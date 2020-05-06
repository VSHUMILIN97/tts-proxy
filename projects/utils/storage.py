import os
from typing import TYPE_CHECKING

from django.core.files.storage import FileSystemStorage

if TYPE_CHECKING:  # pragma: no cover
    from projects.models import AudioRecord


class OverwriteStorage(FileSystemStorage):
    """ Storage class based on the current Django storage class
        Implement overwriting logic to the base storage
    """

    def get_available_name(self, name, max_length=None):
        """ Base storage method for name resolving """
        if self.exists(name):
            self.delete(name)
        return name


def project_path_cb(
        instance: 'AudioRecord',
        filename: str,
        root: str = 'default'
) -> str:
    """ Real callback for django storage internals """
    return os.path.join(root, instance.related_project.slug, filename)
