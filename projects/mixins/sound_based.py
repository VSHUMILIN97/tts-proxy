import json
import os
import re
import shutil
import subprocess
import tempfile

from typing import Any, Dict, Tuple

import requests
import sox

from django.conf import settings
from django.core.cache import cache

from requests import Response

from projects.utils import exceptions as exc

HRZ_REGEXP = re.compile(r'Sample Rate.*: (.*)')


class _WithSoxMixin(object):
    """ Sox builder container """

    @staticmethod
    def _build_sox_transformer(
            file_type: str = 'raw',
            rate: int = 8000,
            bits: int = 16,
            channels: int = 1,
            encoding: str = 'signed-integer',
    ):
        """ Create and return SoX Transformer obj (same as sox [-args] in cmd)

        Args:
            file_type: Changed file audio format
            rate: Rate of the input audio
            bits: Bits of the input audio
            channels: channels for encoding input audio (stereo or mono or >)
            encoding: encoding type

        Returns:
            Transformer() object. Effects attached via library API

        """
        tfm = sox.Transformer()
        tfm.set_globals(verbosity=0)
        tfm.set_input_format(
            file_type=file_type,
            rate=rate,
            bits=bits,
            channels=channels,
            encoding=encoding,
        )
        return tfm


class SoxTransformerMixin(_WithSoxMixin):
    """ Make Mixin that allows to use sox as sound converter """

    def change_audio_speed(
            self,
            file_path: str,
            new_speed: float
    ) -> Any:
        """ Changing audio speed with SoX without TTS API call

        Args:
            file_path: Current file location
            new_speed:

        Returns:
            tempfile with the .{extension} audio and changed speed

        Notes:
            We cannot change File object on the run. This is a Django DB
            restriction, because of unreliable results after any actions.
            If one would try to, File will be rewritten after second .save()
            call and additional validation (calling clean method)

        """
        ext = os.path.splitext(file_path)[-1]
        buffer_file = tempfile.NamedTemporaryFile(suffix=ext)
        shutil.copy2(file_path, buffer_file.name)
        output_tmp_file = tempfile.NamedTemporaryFile(suffix=ext)
        tfm = self._build_sox_transformer(
            file_type=ext.replace('.', '')
        )
        #
        if new_speed > 3 or new_speed < 0.099999:
            raise exc.ChosenSpeedIsUnavailable('Chosen speed is unavailable')
        #
        tfm.tempo(float(new_speed))
        tfm.build(
            buffer_file.name,
            output_tmp_file.name
        )
        buffer_file.close()
        return output_tmp_file

    def convert_audio_type_format(
            self,
            user_file: Any,
            *,
            extension_to: str = 'raw',
            normalise: bool = False
    ) -> Any:
        """ Change audio extension for the given file, using SoX library

        Args:
            user_file: Filepath to the audio
            extension_to: Extension to convert
            normalise: Does audio require normalisation

        Returns:
            Tempfile with the raw audio data

        """
        try:
            path = user_file.path
        except AttributeError:  # Making it work with tempfiles also (IDK why)
            path = user_file.name
        #
        new_format_file = tempfile.NamedTemporaryFile(
            mode='wb+',
            suffix=f'.{extension_to}',
        )
        #
        if normalise:
            sample_hertz = self._normalise(path)
        else:
            sample_hertz = 8000

        tfm = self._build_sox_transformer(
            file_type=os.path.splitext(path)[-1][1:],
            rate=sample_hertz
        )
        tfm.set_output_format(rate=8000)
        tfm.build(path, new_format_file.name)
        user_file.close()
        return new_format_file

    @staticmethod
    def _normalise(path: str) -> int:
        """ Check audio record current Hertz and use common preset """
        try:
            output = subprocess.check_output(
                ['sox', '--i', path]
            ).decode('utf-8')
            sample_hertz = int(HRZ_REGEXP.search(output).group(1))
        except (TypeError, subprocess.CalledProcessError, AttributeError):
            sample_hertz = 8000
        return sample_hertz


class _TTSMixin(SoxTransformerMixin):
    """ Base Class for creating sound media files via TTS """

    def convert_text_to_sound_via_tts_service(
            self,
            text: str,
            audio_presets: Dict[str, Any],
    ) -> Tuple[Any, Any]:
        """ Convert text to voice via external service

        Args:
            text: Text to convert
            audio_presets: Form audio presets

        Returns:
            Default speed file in the /tmp dir with the .wav suffix
            Speed changed file in the /tmp dir with the .wav suffix

        Notes:
            Should always close a file!
        """
        resp = self._resolve_tts_request(text, **audio_presets)
        if resp.status_code != 200:
            print(resp.__dict__)
            raise exc.TTSBackendIsUnavailable(
                f'Chosen backend is unavailable, please try again later'
            )
        return self._create_audio_from_response(resp, audio_presets)

    def _create_audio_from_response(
            self,
            response: Response,
            audio_presets: Dict[str, Any]
    ) -> Tuple[Any, Any]:
        buffer_file = tempfile.NamedTemporaryFile(suffix='.raw')
        buffer_file.write(response.content)

        default_speed_wav = tempfile.NamedTemporaryFile(suffix='.wav')
        shortening_length = settings.CRT_TTS_OPENING_SHORTENING_RULES.get(
            audio_presets['voice'], None
        )
        tfm = self._build_sox_transformer(file_type='raw')
        #
        if shortening_length:
            tfm = self._apply_anti_grasp_effects(tfm, shortening_length)
        #
        tfm.build(buffer_file.name, default_speed_wav.name)
        buffer_file.close()
        #
        speed = audio_presets.get('speed', None)
        if speed and speed != 1.0 and isinstance(speed, float):
            final_wav = self.change_audio_speed(
                default_speed_wav.name,
                new_speed=audio_presets['speed']
            )
        else:
            final_wav = default_speed_wav
        #
        return default_speed_wav, final_wav

    @staticmethod
    def _apply_anti_grasp_effects(
            transformer: sox.Transformer,
            grasp_length: int
    ):
        """ Patch silence and grasp in record (settings contain proper map) """
        transformer.trim(grasp_length)
        transformer.silence(-1, 0.5, 0.1, buffer_around_silence=True)
        return transformer

    def _resolve_tts_request(
            self,
            text: str,
            **params: Any
    ) -> Response:
        """ Return request after building correct headers

        Args:
            tts: TTSBackend instance
            **kwargs: params for request headers and data

        Returns:
            Request object. Response from the given URL
        """

        raise NotImplementedError()


class YSKTTSMixin(_TTSMixin):
    """ YandexSpeechKit TTS cloud API mixin. Can use any sound converters """

    def _resolve_tts_request(
            self,
            text: str,
            **params
    ):
        """ Body for YSK """
        secret_key = self._acquire_token()
        ysk_data = settings.YSK_TEMPLATE.copy()
        ysk_data['folderId'] = settings.YSK_TTS_FOLDER_ID
        ysk_data['text'] = text
        ysk_data['voice'] = params['voice']
        ysk_data['emotion'] = params['emotion']
        #
        try:
            resp = requests.post(
                settings.YSK_TTS_CONVERT_API_URL,
                data=ysk_data,
                headers={
                    'Authorization': f'Bearer {secret_key}'
                },
                timeout=10
            )
        except requests.Timeout:
            raise exc.TTSBackendIsUnavailable(
                'Yandex speech kit API is unavailable, '
                'please try again later'
            )
        return resp

    @staticmethod
    def _acquire_token() -> str:
        """ Validate token exists or refresh it """
        secret_ttl = cache.ttl('YSK_secret')
        if secret_ttl is None:
            cache.expire('YSK_secret', timeout=0)
        if secret_ttl > 0:
            return cache.get('YSK_secret')
        try:
            resp = requests.post(
                settings.YSK_IAM_BEARER_PULL_URL,
                params={
                    'yandexPassportOauthToken':
                        settings.YSK_BEARER_PULL_SECRET
                },
                timeout=10,
            )
        except requests.Timeout:
            raise exc.TTSBackendIsUnavailable(
                'Yandex speech kit API is unavailable, '
                'please try again later'
            )
        if not resp.status_code == 200:
            raise requests.HTTPError('Undefined error. Please try again.')

        token = json.loads(resp.text)['iamToken']
        cache.set('YSK_secret', token, timeout=42000)
        return token


class CRTTTSMixin(_TTSMixin):
    """ CenterOfSpeechTechnologies API Mixin. Can use any sound converters """

    def _resolve_tts_request(
            self,
            text: str,
            **params: Any
    ) -> Response:
        """ Body for Center of speech technologies """
        crt_params = settings.CRT_TEMPLATE.copy()
        crt_params['voice'] = params['voice']
        crt_params['text'] = text.encode('utf-8', 'strict')
        try:
            resp = requests.get(
                settings.CRT_TTS_CONVERT_API_URL,
                params=crt_params,
                timeout=10
            )
        except requests.Timeout:
            raise exc.TTSBackendIsUnavailable(
                'CRT is unavailable, please try again later'
            )
        return resp
