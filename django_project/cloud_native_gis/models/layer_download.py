# coding=utf-8
# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cloud Native GIS."""

import os
import shutil
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from cloud_native_gis.models.general import AbstractResource
from cloud_native_gis.models.layer import Layer
from cloud_native_gis.utils.type import FileType

User = get_user_model()


class DownloadStatus(object):
    """Quick access for coupling variable with Log status string."""

    START = 'Start'
    RUNNING = 'Running'
    FAILED = 'Failed'
    SUCCESS = 'Success'


class LayerDownload(AbstractResource):
    """Download layer."""

    unique_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    status = models.CharField(
        max_length=100,
        choices=(
            (DownloadStatus.START, DownloadStatus.START),
            (DownloadStatus.RUNNING, DownloadStatus.RUNNING),
            (DownloadStatus.FAILED, DownloadStatus.FAILED),
            (DownloadStatus.SUCCESS, DownloadStatus.SUCCESS),
        ),
        default=DownloadStatus.START
    )
    note = models.TextField(
        null=True, blank=True, help_text='Note of the download task'
    )
    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE
    )
    file_type = models.CharField(
        choices=(
            (FileType.ORIGINAL, FileType.ORIGINAL),
            (FileType.GEOJSON, FileType.GEOJSON),
            (FileType.KML, FileType.KML),
            (FileType.SHAPEFILE, FileType.SHAPEFILE),
            (FileType.GEOPACKAGE, FileType.GEOPACKAGE),
        ),
        max_length=256
    )
    working_dir = models.TextField()
    filename = models.TextField(null=True, blank=True)

    # Task id for celery
    task_id = models.TextField(
        null=True, blank=True, help_text='Celery task id'
    )

    # Generated path
    path = models.TextField(
        null=True, blank=True, help_text='Generated path to file on server'
    )

    @staticmethod
    def export_layer(
            created_by: User,
            layer: Layer, file_type: FileType, working_dir: str, filename=None
    ):
        """Export layer to file."""
        return LayerDownload.objects.create(
            created_by=created_by,
            layer=layer, file_type=file_type, working_dir=working_dir,
            filename=filename
        )

    def schedule_task(self):
        """Schedule async task to process download."""
        from cloud_native_gis.tasks import process_layer_download
        task = process_layer_download.delay(self.id)
        self.task_id = task.id
        self.save()
        return task

    def run(self):
        """Run the download task."""
        self.status = DownloadStatus.START
        self.save()

        # Run if request is original file
        if self.file_type == FileType.ORIGINAL:
            # If it has upload, use original one
            upload = self.layer.layerupload_set.order_by('-created_at').first()
            if upload:
                for file in upload.files:
                    # If it has zip, just return the zip file
                    if file.endswith('.zip'):
                        file_path = os.path.join(upload.folder, file)
                        self.path = file_path
                        if not os.path.exists(file_path):
                            self.status = DownloadStatus.FAILED
                            self.note = "Original file does not found."
                        else:
                            self.status = DownloadStatus.SUCCESS
                        self.save()
                        return
                # if no zip file, try to zipping the folder
                folder_to_zip = upload.folder
                if os.path.exists(folder_to_zip):
                    zip_base = os.path.join(
                        self.working_dir, os.path.basename(folder_to_zip)
                    )
                    zip_path = shutil.make_archive(
                        zip_base, 'zip', folder_to_zip
                    )
                    self.path = zip_path
                    self.status = DownloadStatus.SUCCESS
                    self.save()
                    return
            else:
                self.status = DownloadStatus.FAILED
                self.note = "Original file does not found."
                self.save()
                return

        # For other file type
        else:
            file_path, success = self.layer.export_layer(
                self.file_type, self.working_dir, filename=str(self.unique_id)
            )
            if file_path:
                self.path = file_path
                self.status = DownloadStatus.SUCCESS
            else:
                self.status = DownloadStatus.FAILED
                self.note = success
            self.save()


@receiver(pre_delete, sender=LayerDownload)
def delete_layer_download_file(sender, instance, **kwargs):
    """Delete the file at path when LayerDownload is deleted."""
    if instance.path and os.path.exists(instance.path):
        try:
            os.remove(instance.path)
        except OSError:
            pass
