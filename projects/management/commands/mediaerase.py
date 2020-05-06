import os
import getpass
import shutil
from typing import Any, List

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Erase prepared media-files'

    old_dir = 'rec-files'
    new_dir = 'data-files'
    media_root = 'media'

    def add_arguments(self, parser):  # type: (Any) -> None
        """ Create arguments for command """

    def _execute(self):  # type: () -> List[str]
        """ Operation to perform in handle() hook """
        dels = []
        if not os.path.isdir(self.media_root):
            self.stdout.write(
                'Cannot find "media" in current directory. Check if your path '
                f'is correct - {os.getcwd()}'
            )
        for _, dir_, _ in os.walk(self.media_root):
            if self.old_dir in dir_:
                old_p = os.path.join(self.media_root, self.old_dir)
                files = os.listdir(old_p)
                shutil.rmtree(old_p)
                dels.extend(files)
            if self.new_dir in dir_:
                new_p = os.path.join(self.media_root, self.new_dir)
                files = os.listdir(new_p)
                shutil.rmtree(new_p)
                dels.extend(files)
        buffer = []
        [buffer.append(name) for name in dels if name not in buffer]
        return buffer

    def handle(self, *args, **options):  # type: (Any, Any) -> None
        """ Command hook (used only for creating fancy output) """
        try:
            deleted = self._execute()
        except OSError:
            raise CommandError(
                'Consider using this command via root user.\n'
                f'User {getpass.getuser()} have no rights to perform '
                'operations upon this directory.'
            )
        self.stdout.write(
            f'{len(deleted)} file(s) were deleted. Including:\n'
            if deleted
            else 'No entries spotted. Quiet as always B)'
        )
        if deleted:
            self.stdout.write(','.join(deleted))
