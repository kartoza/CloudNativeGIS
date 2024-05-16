"""Context Layer Management."""

import os
import shutil
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from context_layer.models.general import AbstractTerm, AbstractResource

FOLDER_ROOT = os.path.join(settings.MEDIA_ROOT, 'layer_files')
FOLDER_URL = os.path.join(settings.MEDIA_URL, 'layer_files')


class Layer(AbstractTerm, AbstractResource):
    """Model contains layer information."""

    unique_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )

    def __str__(self):
        """Return str."""
        return f'{self.name}'

    @property
    def folder(self) -> str:
        """Return folder path of this layer."""
        return os.path.join(FOLDER_ROOT, str(self.unique_id))

    @property
    def url(self) -> str:
        """Return url root of this layer."""
        return os.path.join(FOLDER_URL, str(self.unique_id))

    # ----------------------------------------------------
    # -------------------- FUNCTIONS ---------------------
    # ----------------------------------------------------
    def delete_folder(self):
        """Delete folder of the instance."""
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)

    def emptying_folder(self):
        """Delete content of the folder."""
        self.delete_folder()
        os.makedirs(self.folder)


@receiver(post_delete, sender=Layer)
def layer_on_delete(sender, instance, using, **kwargs):
    """Delete folder when the layer deleted."""
    instance.delete_folder()
