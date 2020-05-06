import json
import traceback

from datetime import datetime
from decimal import Decimal
from typing import Any, Tuple, Dict

from django.core.files.base import ContentFile
from django.forms import model_to_dict

from requests import Request

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.api.serializers import RecordSerializer
from projects.mixins.sound_based import (
    CRTTTSMixin,
    YSKTTSMixin,
    SoxTransformerMixin
)
from projects.models import AudioRecord, Source, IntegrationProject
from projects.utils.exceptions import ReadUserDataFileError
from projects.utils.tasks import FileParserWithAudioCreation, import_own_files


class DestroyAudioView(generics.DestroyAPIView):

    model = AudioRecord
    lookup_field = 'id'
    permission_classes = (AllowAny,)

    def get_queryset(self) -> Any:
        """ Use minimised queryset only for current project """
        return AudioRecord.objects.filter(
            related_project__slug__exact=self.kwargs['project']
        )


class GetRecordsForProjectView(generics.ListAPIView):
    """ Generic list api view """
    serializer_class = RecordSerializer

    def get_queryset(self):
        """ Get data ONLY for concrete project """
        return AudioRecord.objects.filter(
            related_project__slug__exact=self.kwargs['project']
        )


def wrap_error(fn):
    """ Post-middleware wrapper for handling any exception in view func """
    def request(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            traceback.print_exc()
            raise ValidationError(
                json.dumps(str(exc)),
                code='500'
            )
    return request


class UpdateRecordView(APIView):
    """ View for partial or full update of the audio record """

    @staticmethod
    def _build_presets(
            entry_dict: Dict[str, Any],
            form_dict: Dict[str, str]
    ) -> Dict[str, Any]:
        """ Rebuild form to presets and so on """
        fields = ('text', 'voice', 'emote', 'playing_speed')
        presets = {
            key: value for key, value in entry_dict.items() if key in fields
        }
        if 'speed' in form_dict:
            form_dict['playing_speed'] = form_dict.pop('speed')
        else:
            presets['playing_speed'] = float(presets['playing_speed'])
        if 'emotion' in form_dict:
            form_dict['emote'] = form_dict.pop('emotion')

        presets.update(form_dict)
        presets['emotion'] = presets.pop('emote')
        presets['speed'] = float(presets.pop('playing_speed'))
        return presets

    @staticmethod
    def _speed_update(
            entry: AudioRecord,
            data: Dict[str, Any],
            builder: SoxTransformerMixin
    ) -> Response:
        """ Only update speed for current audio record """
        new_speed = float(data['speed'])
        new_record = builder.change_audio_speed(
            entry.default_audio.path,
            new_speed
        )
        with new_record as audio:
            entry.audio.delete()
            entry.audio.save(
                f'{entry.name}_{datetime.now()}.wav',
                ContentFile(audio.read())
            )
        entry.playing_speed = Decimal.from_float(new_speed)
        entry.save()
        return Response(
            RecordSerializer(entry).data,
            status=201
        )

    @staticmethod
    def _update_record(
            entry: AudioRecord,
            text: str,
            source: Source,
            presets: Dict[str, Any]
    ) -> None:
        """ Update record after editing """
        entry.playing_speed = presets.pop('speed', entry.playing_speed)
        entry.voice = presets.pop('voice', entry.voice)
        entry.text = text
        emotion = presets.get('emotion')
        entry.emote = emotion if emotion else 'Not specified'
        entry.source = source
        entry.save()

    @staticmethod
    def _save_updated_audio(
            origin: Any,
            converted: Any,
            entry: AudioRecord
    ) -> None:
        """ Update existing audio record """
        with converted as converted_:
            content = converted_.read()
            entry.audio.save(
                f'{entry.name}_{datetime.now()}.wav',
                ContentFile(content)
            )
            if origin == converted:
                entry.default_audio.save(
                    f'{entry.name}_{datetime.now()}-default.wav',
                    ContentFile(content)
                )
            else:
                with origin as origin_:
                    entry.default_audio.save(
                        f'{entry.name}_{datetime.now()}-default.wav',
                        ContentFile(origin_.read())
                    )

    @wrap_error
    def post(
            self,
            request: Request,
            project: str,
            primary_key: int,
            *_args: Any,
            **_kwargs: Any
    ) -> Response:
        """ Core body for editing audio records """
        # TODO: refactor (not united w/ create)
        data: Dict[str, Any] = request.data.copy()
        if len(data) == 1 and 'tts' in data:
            return Response(status=304)
        elif len(data) == 1 and 'tts' not in data:
            raise ValidationError(
                detail=json.dumps('Don\'t try to cheat. Use web-forms :)'),
                code='400'
            )
        entry: AudioRecord = get_object_or_404(
            AudioRecord.objects.filter(related_project__slug__exact=project),
            pk=primary_key
        )
        source = Source.objects.get(pk=data['tts'])
        if source.id == 1:
            builder = YSKTTSMixin()
        else:
            builder = CRTTTSMixin()
        if len(data) == 2:
            if 'speed' in data:
                self._speed_update(entry, data, builder)

        presets = self._build_presets(model_to_dict(entry), data)
        text = presets.pop('text')
        origin, converted = builder.convert_text_to_sound_via_tts_service(
            text,
            presets
        )

        self._save_updated_audio(origin, converted, entry)
        self._update_record(entry, text, source, presets)
        return Response(
            RecordSerializer(entry).data,
            status=200
        )


class _MakeRecordBaseView(generics.CreateAPIView):
    """ Base view for both make-record-via-tts-API views """

    serializer_class = RecordSerializer
    permission_classes = (AllowAny, )

    def convert_text_to_sound_via_tts_service(
            self,
            *args: Any,
            **kwargs: Any
    ) -> Tuple[Any, Any]:
        """ Interface for creating sounds from text """
        raise NotImplementedError()

    def get_source(self) -> Source:
        """ Interface for getting right source (synthesis) """
        raise NotImplementedError()

    @wrap_error
    def create(
            self,
            request: Request,
            *args: Any,
            **kwargs: Any
    ) -> Response:
        """ Major API for creating audio record from scratch """
        data = request.data.copy()
        text = data.pop('text')
        project = IntegrationProject.objects.get(
            slug=self.kwargs['project']
        )
        if AudioRecord.objects.filter(related_project=project,
                                      name=data['name']
                                      ).exists():
            raise ValidationError(
                {'name': 'This name already exists'},
                code='400',
            )

        origin, converted = self.convert_text_to_sound_via_tts_service(
            text,
            data
        )
        record = AudioRecord(
            name=data['name'],
            text=text,
            source=self.get_source(),
            related_project=project,
            playing_speed=data['speed'],
            voice=data['voice']
        )
        emote = data.get('emotion', None)
        if emote:
            record.emote = emote
        with converted as converted_:
            record.audio.save(
                f'{data["name"]}.wav',
                ContentFile(converted_.read())
            )
            if origin == converted:
                record.default_audio.save(
                    f'{data["name"]}-default.wav',
                    ContentFile(converted_.read())
                )
            else:
                with origin as origin_:
                    record.default_audio.save(
                        f'{data["name"]}-default.wav',
                        ContentFile(origin_.read())
                    )

        record.save()
        return Response(
            RecordSerializer(record).data,
            status=201,
            headers={'content-type': 'application/json'}
        )


class MakeYSKRecordView(YSKTTSMixin, _MakeRecordBaseView):
    """ View with usage of YSK params for audio synthesis """

    def get_source(self) -> Source:
        return Source.objects.get(name='Yandex Speech Kit')


class MakeCRTRecordView(CRTTTSMixin, _MakeRecordBaseView):
    """ View with usage of CoST params for audio synthesis """

    def get_source(self) -> Source:
        return Source.objects.get(name='Center of speech technologies')


class FileImportView(APIView):
    """ Specific view that allow using files instead  """
    permission_classes = (AllowAny,)

    @wrap_error
    def post(
            self,
            *_request_args: Any,
            project: str,
            **_kwargs: Any
    ):
        """ Allow using file export via POST """
        presets = {
            key: value
            for key, value in self.request.data.items()
            if key != 'export-file'
        }
        presets['project'] = project
        try:
            exceptions = FileParserWithAudioCreation(
                self.request.data['export-file'],
                presets
            ).parse()
        except ReadUserDataFileError as error_str:
            return Response(
                data=json.dumps({'file': f'{str(error_str)}. Check examples'}),
                status=400,
                headers={'content-type': 'application/json'}
            )
        if exceptions:
            return Response(
                status=205,
                data=json.dumps(exceptions),
                headers={'content-type': 'application/json'}
            )
        return Response(status=204)


class ImportOwnFilesView(APIView):
    """ Allow to download and proceed own files """

    permission_classes = (AllowAny,)

    @wrap_error
    def post(
            self,
            *_req_args: Any,
            project: str,
            **_kwargs: Any,
    ) -> Response:
        """ Import own files via request """
        a_names = IntegrationProject.objects.get(
            slug__exact=project
        ).audiorecord_set.all()
        files = {key: value for key, value in self.request.data.items()}
        voice = files.pop('voice')
        data = {'errors': [], 'success': []}
        for result in import_own_files(files, qs=a_names, voice=voice):
            error, success = result.values()
            if error:
                data['errors'].append(error)
            if success:
                data['success'].append(success)
        return Response(status=200, data=data)
