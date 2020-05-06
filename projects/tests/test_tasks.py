import os
import csv
import tempfile

import mock
import xlwt
import pytest
import lxml.builder as xml_bld
import parameterized


from django.core.files.base import ContentFile
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lxml import etree

from projects.utils.exceptions import ReadUserDataFileError
from projects.utils import tasks

from tts_backend.models import TTSBackend
from projects.models import AudioRecord, IntegrationProject


@pytest.mark.unit
class FileParserCaseTest(TestCase):
    """ File parser test case """

    class TempFileWrapper(object):
        """ Imitation of the Django TemporaryUploadFile wrapper """

        def __init__(self, f_file):
            self.file = f_file

        @property
        def name(self):
            """ Alias for filename wrapper """
            return self.file.name

        def temporary_file_path(self):
            """ Stub for getting FP """
            return self.file.name

    def setUp(self):
        """ Creating a test env. Making sure that BASE_DIR/media lib exists """
        if not os.path.exists(f'{os.path.join(settings.BASE_DIR, "media")}'):
            os.mkdir(f'{os.path.join(settings.BASE_DIR, "media")}')

        self.proj = IntegrationProject.objects.create(name='test', slug='test')
        self.excel_load = tasks.BaseParser(
            self._excel,
        )
        self.csv_load = tasks.BaseParser(
            self._csv,
        )
        self.imed_load = tasks.BaseParser(
            self._imed,
        )
        self.broken_load = tasks.BaseParser(
            self._invalid_file
        )
        self.ext_fail = self.TempFileWrapper(
            tempfile.NamedTemporaryFile(suffix='.docx')
        )

    def tearDown(self):
        """ Close all the temporary files (prevent flood in the system) """
        self._invalid_file.file.close()
        self._excel.file.close()
        self._csv.file.close()
        self._imed.file.close()

    @property
    def _invalid_file(self):
        """ File that is not valid for the test DB """
        tmp = tempfile.NamedTemporaryFile(
            dir='media',
            prefix='test_',
            suffix='.xlsx'
        )
        wb = xlwt.Workbook()
        sht = wb.add_sheet('Sheet 2')
        sht.write(3, 2, 'Koi-8')
        sht.write(6, 6, 'XfdsT')
        sht.write(4, 4, 'id1')
        sht.write(5, 5, 'Фуdsf')
        sht.write(7, 7, 'idfsdf2')
        sht.write(5, 3, 'dsБар')
        sht.write(3, 5, 'id3fsd')
        sht.write(12, 12, 'Баз')
        wb.save(tmp.name)
        return self.TempFileWrapper(tmp)

    @property
    def _excel(self):
        """ Excel file in the test DB represented by a property """
        tmp = tempfile.NamedTemporaryFile(
            dir='media',
            prefix='test_',
            suffix='.xlsx'
        )
        wb = xlwt.Workbook()
        sht = wb.add_sheet('Sheet 1')
        sht.write(0, 0, 'ID')
        sht.write(0, 1, 'TEXT')
        sht.write(1, 0, 'id1')
        sht.write(1, 1, 'Фу')
        sht.write(2, 0, 'id2')
        sht.write(2, 1, 'Бар')
        sht.write(3, 0, 'id3')
        sht.write(3, 1, 'Баз')
        wb.save(tmp.name)
        return self.TempFileWrapper(tmp)

    @property
    def _imed(self):
        """ Imed file in test DB represented by a property """
        tmp = tempfile.NamedTemporaryFile(
            dir='media',
            prefix='test_',
            suffix='.imed'
        )
        fake_audio_cursor = [
            {'name': 'id7', 'description': 'Фу'},
            {'name': 'id8', 'description': 'Бар'},
            {'name': 'id9', 'description': 'Баз'}
        ]
        xml_content = xml_bld.E.Voice(
            xml_bld.E.BaseProduct(
                name='./base.imed'
            ),
            xml_bld.E.Langs(
                xml_bld.E.Lang(
                    name='ru', description=u'Русский'
                )
            ),
            xml_bld.E.Sounds(
                *[
                    xml_bld.E.Sound(
                        name=entry['name'],
                        description=entry['description']
                    ) for entry in fake_audio_cursor
                ]
            ),
            schema='1', version='Multy'
        )
        with open(tmp.name, 'wb') as f:
            f.write(
                etree.tostring(
                    xml_content,
                    pretty_print=True,
                    encoding='UTF-8',
                    standalone='yes',
                    xml_declaration=True,
                )
            )
        return self.TempFileWrapper(tmp)

    @property
    def _csv(self):
        """ CSV file in test DB represented by a property """
        tmp = tempfile.NamedTemporaryFile(
            dir='media',
            prefix='test_',
            suffix='.csv'
        )
        with open(tmp.name, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = (u'ID', u'TEXT',)
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {'ID': 'id4', 'TEXT': 'Фу'}
            )
            writer.writerow(
                {'ID': 'id5', 'TEXT': 'Бар'}
            )
            writer.writerow(
                {'ID': 'id6', 'TEXT': 'Баз'}
            )
            writer.writerow(
                {'ID': '1.0', 'TEXT': 'Базбар'}
            )
        return self.TempFileWrapper(tmp)

    def test_internal_accessory_files_are_generated(self):
        """ Accessory test for the fake files generation """
        self.assertIsNotNone(self._excel)
        self.assertIsNotNone(self._csv)
        self.assertIsNotNone(self._imed)
        self.assertIsNotNone(self._invalid_file)

    @parameterized.parameterized.expand([
        (lambda self: self.excel_load.parse(), 'id1'),
        (lambda self: self.csv_load.parse(), 'id4'),
        (lambda self: self.imed_load.parse(), 'id7'),
    ])
    def test_parsing_result_do_not_become_objects_in_db(
            self,
            file_parser,
            audio_id
    ):
        """ Checks: Parsing operation does not create objects in the DB """
        file_parser(self)
        with self.assertRaises(ObjectDoesNotExist):
            AudioRecord.objects.get(name=audio_id)

    def test_parser_does_not_escape_floats(self):
        """ Checks: Parsing floats does not override ID w/ system rules """
        data = self.csv_load.parse()
        self.assertIn('1.0', data[-1].values())

    @parameterized.parameterized.expand([
        (
            lambda self: self.excel_load.parse(),
            [
                {'ID': 'id1', 'TEXT': 'Фу'},
                {'ID': 'id2', 'TEXT': 'Бар'},
                {'ID': 'id3', 'TEXT': 'Баз'},
            ]
        ),
        (
            lambda self: self.csv_load.parse(),
            [
                {'ID': 'id4', 'TEXT': 'Фу'},
                {'ID': 'id5', 'TEXT': 'Бар'},
                {'ID': 'id6', 'TEXT': 'Баз'},
                {'ID': '1.0', 'TEXT': 'Базбар'},
            ]
        ),
        (
            lambda self: self.imed_load.parse(),
            [
                {'ID': 'id7', 'TEXT': 'Фу'},
                {'ID': 'id8', 'TEXT': 'Бар'},
                {'ID': 'id9', 'TEXT': 'Баз'}
            ]
        ),
    ])
    def test_parsing_result_for_healthy_files(self, data_parser, expected):
        """ Checks: That FileField of the AudioRecord model contains None """
        actual = data_parser(self)
        self.assertEqual(actual, expected)

    def test_parse_for_broken_file_throw_exception(self):
        """ Checks: parse() will throw errors if data is incorrect
            ReadUserDataFileError
        """
        with self.assertRaises(ReadUserDataFileError):
            self.broken_load.parse()

    def test_incorrect_file_extension_validation(self):
        """ Checks: File extension will be validated against ext rules """
        with self.assertRaises(ValueError):
            tasks.BaseParser(self.ext_fail)

    def test_broken_xls_file_will_produce_specific_exception(self):
        """ Checks: Incorrect file will produce ReadUserFileException """
        with self.assertRaises(ReadUserDataFileError):
            self.broken_load.parse()


@pytest.mark.unit
class AudioCreationTest(TestCase):
    """ Creation of the audio records """

    def setUp(self):
        """ Define working fixtures for this test case """
        self.generation_patch = mock.patch.object(
            tasks.DataToAudioConverter,
            '_make_audio_content',
            return_value=(
                ContentFile('\x89PNG\r\n\x1a\n\x00\x00\x00'),
                ContentFile('\x89PNG\r\n\x1a\n\x00\x00\x00')
            )
        )
        self.presets = {
            'tts': TTSBackend.objects.first(),
            'emote': 'neutral',
            'voice': TTSBackend.objects.first().ttsvoice_set.first(),
            'speed': 1.0,
            'project': IntegrationProject.objects.first().slug
        }

    def tearDown(self):
        """ Drop down query set for all """
        for instance in AudioRecord.objects.all():
            instance.audio.delete()
            instance.default_audio.delete()

    def test_smoke(self):
        """ Smoke test for creating audio records """
        data = [
            {'ID': 'WOW', 'TEXT': 'SLOW'}, {'ID': 'a', 'TEXT': 'Жаброни'}
        ]
        with self.generation_patch:
            errors = tasks.DataToAudioConverter(
                data,
                self.presets
            ).make_audio_files()

        self.assertEqual(errors, [])
        self.assertEqual(AudioRecord.objects.get(name='WOW').text, 'SLOW')
        self.assertEqual(AudioRecord.objects.get(name='a').text, 'Жаброни')

    def test_float_id_convert_into_integer(self):
        """ Checks: Float values become integers in the system

        Notes:
            Real problem in the MS applications and its number treatment policy
        """
        data = [
            {'ID': '2.0', 'TEXT': 'SLOW'}, {'ID': '1.0', 'TEXT': 'Жаброни'}
        ]
        with self.generation_patch:
            tasks.DataToAudioConverter(data, self.presets).make_audio_files()
        self.assertEqual(AudioRecord.objects.get(name='2').text, 'SLOW')
        self.assertEqual(AudioRecord.objects.get(name='1').text, 'Жаброни')
