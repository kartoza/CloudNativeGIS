# coding=utf-8
"""Context Layer Management."""

from celery.utils.log import get_task_logger

from core.celery import app

logger = get_task_logger(__name__)


@app.task
def import_data(layer_id):
    """Import data from layer id."""
    from context_layer_management.models import LayerUpload
    try:
        layer = LayerUpload.objects.get(id=layer_id)
        layer.import_data()
    except LayerUpload.DoesNotExist:
        logger.error(f'Layer {layer_id} does not exist')
