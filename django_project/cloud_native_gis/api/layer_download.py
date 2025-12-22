# coding=utf-8
"""Cloud Native GIS."""

import os

from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cloud_native_gis.models.layer_download import (
    LayerDownload, DownloadStatus
)
from cloud_native_gis.utils.type import FileType


class FileWrapper:
    """File wrapper that deletes file on close."""

    def __init__(self, file_path):
        """Initialize wrapper."""
        self.file_path = file_path
        self.file = open(file_path, 'rb')

    def __iter__(self):
        """Iterate over file chunks."""
        return self

    def __next__(self):
        """Get next chunk."""
        chunk = self.file.read(8192)
        if not chunk:
            raise StopIteration
        return chunk

    def read(self, size=-1):
        """Read from file."""
        return self.file.read(size)

    def close(self):
        """Close file and delete it."""
        try:
            self.file.close()
        finally:
            # Delete the file after closing
            try:
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
            except OSError:
                pass


class DownloadFileAPI(APIView):
    """API to download file from LayerDownload."""

    permission_classes = [IsAuthenticated]

    def get(self, request, unique_id):
        """Download the file if ready."""
        # Get layer download by unique_id
        layer_download = get_object_or_404(
            LayerDownload.objects.filter(unique_id=unique_id)
        )

        # Check if user has permission
        if layer_download.created_by != request.user:
            raise PermissionDenied(
                "You don't have permission to download this file."
            )

        # Check if download failed
        if layer_download.status == DownloadStatus.FAILED:
            return Response(
                {
                    'error': 'Download failed.',
                    'note': layer_download.note
                },
                status=500
            )

        # Check if download is ready
        if layer_download.status != DownloadStatus.SUCCESS:
            return Response(
                {
                    'error': 'Download is not ready yet.',
                    'status': layer_download.status,
                    'note': layer_download.note
                },
                status=400
            )

        # Check if file exists
        if not layer_download.path or not os.path.exists(layer_download.path):
            return Response(
                {'error': 'File not found.'},
                status=404
            )

        # Determine filename
        extension = FileType.to_extension(layer_download.file_type)
        filename = f'{layer_download.layer.name}{extension}'

        is_head_request = request.method == 'HEAD'
        if layer_download.file_type == FileType.ORIGINAL or is_head_request:
            return FileResponse(
                open(layer_download.path, 'rb'),
                as_attachment=True,
                filename=filename
            )

        # Create file wrapper that will delete file after download
        file_wrapper = FileWrapper(layer_download.path)

        return FileResponse(
            file_wrapper,
            as_attachment=True,
            filename=filename
        )
