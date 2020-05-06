import pytest

from django.test import TestCase

from tts_backend.models import TTSBackend, TTSVoice
from ..models import AudioRecord
from projects.forms import AudioRecordForm


@pytest.mark.unit
class AudioRecordFormstest(TestCase):
    """ Tests for forms.py file and Django generics """
    def setUp(self):
        """ Setting up environment with objects """
        self.tts = TTSBackend.objects.get(name='CRT')
        self.voice = TTSVoice.objects.first()
        AudioRecord.objects.create(
            name='test', text='one', tts_backend=self.tts, voice=self.voice
        )
        self.rec = AudioRecord.objects.filter(name='test').values()[0]
        self.form = AudioRecordForm(self.rec)

    def test_form_init(self):
        """ Test form is initialised """
        self.assertTrue(bool(self.form))

    def test_form_contains_stuff(self):
        """ Checks: Form is fulfilled with data """
        self.assertTrue(self.form.is_bound)
