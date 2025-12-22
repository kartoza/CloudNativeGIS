# coding=utf-8
"""Cloud Native GIS."""

from rest_framework import serializers

from cloud_native_gis.models.layer_download import LayerDownload


class LayerDownloadSerializer(serializers.ModelSerializer):
    """Serializer for LayerDownload."""

    layer_name = serializers.CharField(
        source='layer.name', read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True
    )
    is_ready = serializers.SerializerMethodField()

    class Meta:  # noqa: D106
        model = LayerDownload
        fields = (
            'id', 'unique_id', 'created_at', 'created_by',
            'created_by_username', 'layer', 'layer_name',
            'file_type', 'status', 'note', 'task_id',
            'is_ready', 'path'
        )
        read_only_fields = (
            'id', 'unique_id', 'created_at', 'created_by',
            'status', 'note', 'task_id', 'path', 'is_ready'
        )

    def get_is_ready(self, obj):
        """Check if download is ready."""
        from cloud_native_gis.models.layer_download import DownloadStatus
        return obj.status == DownloadStatus.SUCCESS and bool(obj.path)