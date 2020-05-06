import json
import os
import tempfile
import time
import copy

from decimal import Decimal

import mock
import parameterized
import pytest
import wave
import requests

from django.test import TestCase

from lxml import objectify

from projects.utils.exceptions import TTSBackendIsUnavailable
from projects.mixins.sound_based import BaseSoundConverterMixin
from projects.tests.test_utils.mixin_assets import (
    DummyImedGeneratorView,
    DummyJsonBasedView,
    FakeResponse
)
from projects.models import AudioRecord, IntegrationProject

from tts_backend.models import TTSVoice, TTSBackend


@pytest.mark.unit
class ImedGeneratorTest(TestCase):
    """ Test case for Media library Mix-in"""

    def setUp(self):
        """ Setting up test environment """
        project = IntegrationProject.objects.create(
            name='Pog U',
            slug='pog_u'
        )
        self.allocated_names = ['Meow', 'Mur', 'Pur']
        for text in self.allocated_names:
            AudioRecord.objects.create(
                name=f'{text}_name',
                text=f'{text}_text\nnext',
                related_project=project,
                voice=TTSVoice.objects.first(),
                tts_backend=TTSBackend.objects.first(),
            )
        self.d_view = DummyImedGeneratorView()
        self.imed_xml = self.d_view.create_imed(AudioRecord.objects.all())

    def tearDown(self):
        """ Modify data after completing every test case """
        self.imed_xml.close()

    @parameterized.parameterized.expand([
        ('./test', './test/'),
        ('morkovka', 'morkovka/'),
        ('/./././()eshkere', '/./././eshkere/'),
        ('./test/', './test/'),
        ('{-_}{&?}{+=}sha', '-_sha/'),
    ])
    def test_build_path_assertions(self, path, expected):
        """ Create imed files with builder path """
        imed = self.d_view.create_imed(AudioRecord.objects.all(), path)
        with open(imed.name, 'rb') as f:
            data = f.read()
            root = objectify.fromstring(data)
            sounds = root.Sounds.Sound
            for sound in sounds:
                self.assertTrue(
                    sound.attrib['file'].startswith(expected)
                )
                self.assertTrue(
                    sound.attrib['file'].endswith('.raw')
                )
        imed.close()

    def test_mixin_return_imed_file(self):
        """ Checks: File is in /tmp/ dir, since it's a TempFile instance """
        self.assertTrue(self.imed_xml.name.startswith(tempfile.gettempdir()))

    def test_mixin_data_is_correct(self):
        """ Checks: Data is correct for .imed file """
        with open(self.imed_xml.name, 'rb') as f:
            data = f.read()
            root = objectify.fromstring(data)
            sounds = root.Sounds.Sound
            for sound in sounds:
                self.assertTrue(
                    sound.attrib['name'].replace('_name', '')
                    in self.allocated_names
                )

    def test_project_is_correctly_represented_in_file(self):
        """ Checks: .imed file correctly store the attribute file='' """
        with open(self.imed_xml.name, 'rb') as f:
            data = f.read()
            root = objectify.fromstring(data)
            sounds = root.Sounds.Sound
            filepath = sounds[0].attrib['file']
            self.assertEqual(
                filepath,
                './client/pog_u/audio/Meow_name.raw'
            )

    def test_imed_text_do_not_contain_escape_or_line_break_symbols(self):
        """ Checks: .imed audio description do not contain escape
                    (or line break) symbols
        """
        with open(self.imed_xml.name, 'rb') as f:
            data = f.read()
            root = objectify.fromstring(data)
            sounds = root.Sounds.Sound
            text = sounds[0].attrib['description']
            self.assertEqual(
                text,
                'Meow_textnext'
            )


@pytest.mark.unit
class FormBasedMixinTest(TestCase):
    """ Test case for FormBased Mix-in """

    class FakeProject(object):
        """ Fake related project """

        def __init__(self, name):
            """ Project Fakers """
            self.name = name

    class FakeAudio(object):
        """ Fake related Audio object """

        def __init__(self):
            self.path = None

        def save(self, name, content):
            """ Mocking the save method contsanlty """
            pass

    class FakeFormFactory(object):
        """ Fake form object for this case """

        def __init__(self, cld, chd):
            """ Setting necessary attributes here

            Args:
                cld: dict with cleaned data
                chd: list with changed field
            """
            _el = {}
            _el.update(cld)
            self.cleaned_data = _el
            self.changed_data = chd

        def save(self, commit=False):
            """ Fake save() method """
            if not commit:
                return AudioRecord(**self.cleaned_data)

    def setUp(self):
        """ Setting up test env """
        self.snippet = AudioRecord.objects.values_list('id', flat=True)
        self.project = IntegrationProject.objects.create(name='test')
        self.tts_1 = TTSBackend.objects.create(
            name='KVN',
            link='http://127.0.0.1/ru',
            auth_token='1234'
        )
        TTSVoice.objects.create(voice='Я', tts_backend=self.tts_1)
        self.tts_2 = TTSBackend.objects.create(
            name='IBM',
            link='http://127.0.0.1/en',
            auth_token='1234'
        )
        TTSVoice.objects.create(voice='Мишка', tts_backend=self.tts_2)
        self.voice = TTSVoice.objects.first()
        self.FIXTURE = {
            'name': '1234',
            'slug': '1234',
            'text': 'Сорт оф',
            'tts_backend': TTSBackend.objects.first(),
            'related_project': self.FakeProject('test'),
            'audio': '',
            'playing_speed': '1',
            'voice': TTSVoice.objects.first(),
            'emote': '',
        }
        data = copy.deepcopy(self.FIXTURE)
        data['related_project'] = self.project
        data['name'] = '1235'
        data['slug'] = '1235'
        data['tts_backend'] = self.tts_1
        data['voice'] = self.tts_1.ttsvoice_set.first()
        self.fake_audio = AudioRecord.objects.create(**data)
        self.d_view = DummyJsonBasedView()
        self.only_name_form = self.FakeFormFactory(
            self.FIXTURE,
            ['name', ]
        )

    def tearDown(self):
        """ Erase everything after test run """
        IntegrationProject.objects.all().delete()
        self.tts_1.delete()
        self.tts_2.delete()
        self.project.delete()
        self.fake_audio.delete()

    def test_method_is_callable_for_update(self):
        """ Checks: Method may be called from view with is_update flag """
        self.d_view.convert_data(self.only_name_form, is_update=True)
        self.assertTrue(True)

    def test_method_is_callable_for_base(self):
        """ Checks: Method may be called without update """
        self.d_view.convert_data(self.only_name_form)
        self.assertTrue(True)

    @parameterized.parameterized.expand([
        ('1236', Decimal('1.0'), ['name']),
        (None, Decimal('1.4'), ['playing_speed']),
        ('1236', Decimal('0.8'), ['name', 'playing_speed']),
    ])
    @mock.patch.object(FakeFormFactory, 'save')
    @mock.patch.object(BaseSoundConverterMixin, 'change_audio_speed')
    def test_method_allow_operations_without_tts(
            self, name, speed, ch_data, mock_speed_changer, mock_save
    ):
        """ Checks: Method allow to change name/speed without calling TTS """
        self.FIXTURE.update({
            'name': name,
            'playing_speed': speed,
            'related_project': self.project,
            'audio': self.FakeAudio()
        })
        form = self.FakeFormFactory(
            self.FIXTURE,
            ch_data
        )
        fake_audio = tempfile.NamedTemporaryFile('w+b', suffix='.wav')
        fake_audio.write(b'000')
        cl_d = copy.deepcopy(self.FIXTURE)
        cl_d['audio'] = ""
        instance = AudioRecord(
            **cl_d
        )
        instance.audio = self.FIXTURE['audio']
        mock_save().side_effect = [instance, None]
        mock_speed_changer.side_effect = [fake_audio]
        self.d_view.convert_data(form)
        self.assertTrue(True)
        fake_audio.close()


@pytest.mark.unit
class SoundBasedMixinTest(TestCase):
    """ Test case for sound based mix-ins """

    def setUp(self):
        """ Setting up environment """
        self.sound_convert = BaseSoundConverterMixin()
        self.tts = TTSBackend.objects.first()
        self.voice = TTSVoice.objects.first()
        self.snippet = AudioRecord.objects.all().values_list('id', flat=True)

    def tearDown(self):
        """ Erasing everything for each test case """
        new_snippet = AudioRecord.objects.all()
        for audio in new_snippet:
            if audio.id not in self.snippet:
                audio.delete()

    @mock.patch.object(BaseSoundConverterMixin, '_resolve_tts_request')
    def test_convert_via_tts_success(self, mock_request):
        """ Checks: Is it possible to convert audio with TTS call (success) """
        mock_request.side_effect = [FakeResponse()]
        dflt, file = self.sound_convert.convert_text_to_sound_via_tts_service(
            '1',
            self.tts,
            self.voice,
            speed=1,
            emote='neutral'
        )
        reader = wave.open(file.name)
        self.assertEqual(reader.getnchannels(), 1)
        self.assertEqual(reader.getframerate(), 8000)
        file.close()
        dflt.close()

    @mock.patch.object(BaseSoundConverterMixin, '_resolve_tts_request')
    def test_convert_via_tts_failure(self, mock_request):
        """ Checks: Is it possible to convert audio with TTS (failure case) """
        mock_request.side_effect = [
            FakeResponse(success=False, text=json.dumps({
                'error_status': 'Test',
                'error_message': 'You have been tested'
            }))
        ]
        with self.assertRaises(TTSBackendIsUnavailable) as exc:
            self.sound_convert.convert_text_to_sound_via_tts_service(
                '1',
                self.tts,
                self.voice,
                speed=1,
                emote='neutral'
            )
        #
        self.assertEqual(
            exc.exception.args,
            (
                f'The {self.tts.name} '
                f'is unavailable, please try again later.\n'
                f'Status - "Test".\n'
                f'Error message - "You have been tested"',
            )
        )

    @parameterized.parameterized.expand([
        (
            time.time(),
            TTSBackend(name='KKK', link='1', expires_at='1'),
            FakeResponse(text=json.dumps({'iamToken': '123456789i'})),
            '123456789i',
        ),
        (
            time.time(),
            TTSBackend(
                name='KKK',
                link='1',
                expires_at=str(time.time()),
                auth_token='test123',
            ),
            FakeResponse(),
            'test123',
        )
    ])
    @mock.patch('requests.post')
    def test_check_token_is_fetching(
            self, fake_time, fake_tts, fake_response, token, mock_req
    ):
        """ Checks: Token fetcher test """
        mock_req.side_effect = (fake_response,)
        self.sound_convert._acquire_token(fake_tts)
        self.assertGreaterEqual(float(fake_tts.expires_at), fake_time)
        self.assertEqual(fake_tts.auth_token, token)

    @parameterized.parameterized.expand([
        (
            FakeResponse(success=False),
            requests.HTTPError,
            'Undefined error. Please try again.',
        ),
        (
            requests.Timeout,
            TTSBackendIsUnavailable,
            'The test is unavailable, please try again later.\n'
            'Error message - "Cannot authenticate via Bearer"',
        ),
    ])
    @mock.patch('requests.post')
    def test_check_token_is_unfetchable(
            self, fake_response, thrown_error, fake_msg, mocked_request
    ):
        """ Checks: Token cannot be fetched (YSK backend issues) """
        with self.assertRaises(thrown_error) as exc:
            mocked_request.side_effect = (fake_response,)
            self.sound_convert._acquire_token(
                TTSBackend(name='test', link='test', expires_at='1')
            )
        self.assertEqual(exc.exception.args, (fake_msg,))

    def test_check_audio_format_is_changable(self):
        """ Checks: It is possible to make .wav from .raw and so on """
        raw = tempfile.NamedTemporaryFile('wb+', suffix='.raw')
        open(raw.name, 'wb+').write(b'000')
        wav_t = self.sound_convert.convert_audio_type_format(raw, 'wav')
        self.assertEqual(os.path.splitext(wav_t.name)[-1], '.wav')
