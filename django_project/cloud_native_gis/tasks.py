# coding=utf-8
"""Cloud Native GIS."""

import os
from datetime import timedelta

from celery.utils.log import get_task_logger
from django.utils import timezone

from core.celery import app

logger = get_task_logger(__name__)


@app.task
def import_data(layer_id):
    """Import data from layer id."""
    from cloud_native_gis.models import LayerUpload
    try:
        layer = LayerUpload.objects.get(id=layer_id)
        layer.import_data()
    except LayerUpload.DoesNotExist:
        logger.error(f'Layer {layer_id} does not exist')


@app.task
def process_layer_download(layer_download_id):
    """Process layer download from layer_download id."""
    from cloud_native_gis.models import LayerDownload
    try:
        layer_download = LayerDownload.objects.get(id=layer_download_id)
        layer_download.run()
    except LayerDownload.DoesNotExist:
        logger.error(f'LayerDownload {layer_download_id} does not exist')


@app.task
def cleanup_old_layer_downloads():
    """Clean up layer download files older than 1 hour."""
    from cloud_native_gis.models import LayerDownload

    cutoff_time = timezone.now() - timedelta(hours=1)
    old_downloads = LayerDownload.objects.filter(created_at__lt=cutoff_time)

    for download in old_downloads:
        if download.path and os.path.exists(download.path):
            try:
                os.remove(download.path)
            except OSError:
                pass
