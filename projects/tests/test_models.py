from datetime import datetime

import parameterized
import pytest

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.test import TestCase

from tts_backend.models import TTSBackend, TTSVoice
from projects.models import AudioRecord, IntegrationProject


@pytest.mark.unit
class AudioRecordModelTest(TestCase):
    """ AudioRecord models test """

    def setUp(self):
        """ Creating objects for the testing env and DO NOT save 'em """
        self.tts = TTSBackend.objects.get(name='CRT')
        self.voice = TTSVoice.objects.first()
        AudioRecord.objects.create(
            name='fake',
            text='fakery fakedy fake',
            tts_backend=self.tts,
            voice=self.voice
        )
        self.rec = AudioRecord.objects.get(name='fake')
        self.proj = IntegrationProject.objects.create(
            name='proj',
            slug='proj'
        )

    def test_records_do_not_have_audio(self):
        """ Checks whether audio is on the basic object creation """
        self.assertFalse(bool(self.rec.audio))

    def test_records_do_have_backend_choice_filed(self):
        """ Checks whether record have backend choice field """
        self.assertEqual(str(self.rec.tts_backend), 'CRT')

    def test_records_do_have_timestamp_on_creation(self):
        """ Checks whether timestamp is created and it is a datetime ins'ce """
        self.assertIsInstance(self.rec.modified_at, datetime)

    def test_text_field_is_ok_with_non_unique(self):
        """ Checks whether text field  """
        AudioRecord.objects.create(
            name='faker',
            text='fakery fakedy fake',
            tts_backend=self.tts,
            voice=self.voice
        )
        self.assertEqual(
            self.rec.text, AudioRecord.objects.get(name='faker').text
        )

    def test_get_absolute_url(self):
        """ Checks whether get_absolute_url return actual URL slug """
        self.assertEqual(
            self.rec.get_absolute_url().split('/')[-1],
            self.rec.name
        )
        self.assertNotEqual(
            self.rec.get_absolute_url().split()[0],
            self.rec.name
        )

    def test_get_manual_edit_url_related_to_file_and_project(self):
        """ Checks whether manual URL to its ancestor """

        record = AudioRecord.objects.create(
            name='test',
            text='test',
            tts_backend=self.tts,
            voice=self.voice
        )

        self.assertEqual(
            '/imedgen/projects/drafts/audiorecords/test',
            record.get_absolute_url()
        )

    def test_string_object_repr(self):
        """ Checks whether object is str() convert possible """
        self.assertEqual(str(self.rec), 'fake')

    def test_project_can_be_related(self):
        """ Checking for a ForeignKey link with IntegrationProject model """
        rec = AudioRecord.objects.create(
            name='test',
            text='test',
            tts_backend=self.tts,
            related_project=self.proj,
            voice=self.voice,
        )
        self.assertEqual(rec.related_project.name, 'proj')
        self.assertEqual(type(rec.related_project.created_at), datetime)

    @parameterized.parameterized.expand(['-', '_'])
    def test_allowed_special_symbols(self, allowed_char):
        """ Checks: Possibility to create record(id) with allowed char """
        rec = AudioRecord.objects.create(
            name=f'{allowed_char}test',
            text='test',
            tts_backend=self.tts,
            related_project=self.proj,
            voice=self.voice,
            audio='1',
            default_audio='1',
            emote='neutral'
        )
        rec.clean_fields()  # explicit validation call
        self.assertEqual(rec.name, f'{allowed_char}test')


@pytest.mark.unit
class IntegrationProjectModelTest(TestCase):
    """ TestCase for the 'IntegrationProject' model """

    def setUp(self):
        """ Setting up test environment """
        self.project = IntegrationProject.objects.create(
            name='Default',
            slug='default'
        )

    def tearDown(self):
        """ Erase environment changes """
        self.project.delete()

    def test_integration_project_should_contain_slug(self):
        """ Checks: Slug is created AND reachable every time """
        self.assertEqual(self.project.slug, 'default')
        tst_cs = IntegrationProject.objects.create(name='Wipe')
        self.assertEqual(tst_cs.slug, 'wipe')

    def test_object_have_string_repr(self):
        """ Checks: __str__ is defined and return actual value of obj name """
        self.assertEqual(str(self.project), 'Default')

    def test_get_absolute_url(self):
        """ Checks: get_absolute_url return actual URL slug from obj name """
        self.assertEqual(
            self.project.get_absolute_url().split('/')[-2],
            'audiorecords'
        )
        self.assertNotEqual(
            self.project.get_absolute_url().split()[0],
            self.project.name
        )

    def test_slug_is_autocreated_in_every_case(self):
        """ Checks: Slug is created in every case and every time """
        a = IntegrationProject.objects.create(name='Вася')
        b = IntegrationProject.objects.create(name='КаМеЛио CasE - %4444')
        c = IntegrationProject.objects.create(name='12345')
        self.assertEqual(a.slug, 'vasia')
        self.assertEqual(b.slug, 'kamelio-case-4444')
        self.assertEqual(c.slug, '12345')

    def test_slug_may_be_not_valid(self):
        """ Checks: Slug field may not be valid if manually edited """
        a = IntegrationProject(name='1', slug='КуКуХа%421411|')
        with self.assertRaises(ValidationError) as cm_err:
            a.full_clean()
        self.assertIsNotNone(cm_err.exception.error_dict.get('slug'))
