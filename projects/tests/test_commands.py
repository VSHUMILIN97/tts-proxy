import os
from io import StringIO

import pytest
import parameterized
from django.core.management import call_command
from django.test import TestCase


@pytest.mark.unit
class EraseMediaFilesTest(TestCase):
    """ Test case for new command that erase media files from subsystem """

    def setUp(self):
        """ Fill in unit test with necessary data """
        if not os.path.isdir('media'):  # ensure "media" in test env
            os.makedirs('media')
        self.strio = StringIO()
        self.command = lambda: call_command('mediaerase', stdout=self.strio)

    def test_empty(self):
        """ Checks: No special files stored in media """
        self.command()
        actual = self.strio.getvalue()
        expected = 'No entries spotted. Quiet as always B)\n'
        self.assertEqual(actual, expected)

    @staticmethod
    def _make_data(path, first_name='one'):
        """ Create data in media folder to test command work """
        media_p = os.path.join(os.getcwd(), 'media')
        file_list = os.listdir(media_p)
        if path in file_list:
            raise OSError(
                'Consider saving any important data before running this test'
            )
        media_p = os.path.join(media_p, path)
        dirs = [name for name in [first_name, 'two', 'three']]
        for dirname in dirs:
            media_p = os.path.join(media_p, dirname)
        os.makedirs(media_p)
        with open(os.path.join(media_p, 'anypepegas'), 'w') as write_case:
            write_case.write('pepega')

    @parameterized.parameterized.expand([
        ('rec-files', 'old'),
        ('data-files', 'new')
    ])
    def test_single_data_format(self, data_type, pr_name):
        """ Checks: Old-style data will be erased from system """
        self._make_data(data_type, pr_name)
        self.command()
        actual = self.strio.getvalue()
        expected = (
            '1 file(s) were deleted. Including:\n'
            f'{pr_name}\n'
        )
        self.assertEqual(actual, expected)

    def test_combination_of_data_types(self):
        """ Checks: New and Old style data will be erased from the system """
        self._make_data('rec-files', 'old')
        self._make_data('data-files', 'new')
        self.command()
        actual = self.strio.getvalue()
        expected = (
            '2 file(s) were deleted. Including:\n'
            'old,new\n'
        )
        self.assertEqual(actual, expected)
