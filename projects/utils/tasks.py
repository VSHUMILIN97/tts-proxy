from __future__ import annotations

import csv
import os

from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from tempfile import NamedTemporaryFile
from typing import (
    List,
    Tuple,
    Any,
    Union,
    Callable,
    Mapping,
    ClassVar,
    Optional,
    Generator
)

import pydub
import xlrd

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import QuerySet
from lxml import objectify

from projects.models import Source
from projects.utils import exceptions as exc

from ..models import AudioRecord, IntegrationProject
from projects.mixins.sound_based import (
    CRTTTSMixin as CrtTTS,
    YSKTTSMixin as YskTTS,
    SoxTransformerMixin
)


class BaseParser(object):
    """ Base class for generating AudioRecord DB records """
    EXTENSIONS: ClassVar[Tuple[str, ...]] = ('.csv', '.xls', '.xlsx', '.imed')

    def __init__(
            self,
            form_file: TemporaryUploadedFile
    ):
        """ Parser for creating dataset for audio generation

        Args:
            form_file: File uploaded from user request

        Raises:
            ValueError: In case of unexpected file extension

        """
        self.django_file_wrapper = form_file
        self.ext = os.path.splitext(self.django_file_wrapper.name)[-1].lower()
        if self.ext not in self.EXTENSIONS:
            raise exc.ReadUserDataFileError(
                'File extension does not comfort to this list - '
                f'{self.EXTENSIONS}'
            )

    @property
    def _is_csv(self):  # type: () -> bool
        """ Extension validation function

        Returns:
            True if file is csv False in any other cases

        Notes:
            CSV is preferred over XLS, because of native support in python

        """
        if self.ext != '.csv':
            return False
        return True

    @property
    def _is_imed(self):  # type: () -> bool
        """ Extension validation function

        Returns:
            True if file is imed False in any other cases

        Notes:
            imed is preferred over XLS, because its our own data type

        """
        if self.ext != '.imed':
            return False
        return True

    def _get_data(self):  # type: () -> List[Mapping[str, str]]
        """ Extract data from file """
        if self._is_csv:
            values = self._parse_csv()
        elif self._is_imed:
            values = self._parse_imed()
        else:
            values = self._parse_xls()
        return values

    def parse(self):  # type: () -> List[Mapping[str, str]]
        """ Well-known alias for parsing operation """
        try:
            return self._get_data()
        except KeyError:
            raise exc.ReadUserDataFileError(
                'Given file missing one of the HEADER columns [ID/TEXT]'
            )

    def _parse_csv(self) -> List[Mapping[str, str]]:
        """ Inner method for parsing CSV files

        Creates:
            Rows for the projects_audiorecord table in the DB

        Returns:
            csv.DictReader which is list with dicts that contain row values
            in the format of {ColumnHeaderName[0]:N, ColumnHeaderName[1]:N, ..}

        """
        d_file = open(self.django_file_wrapper.temporary_file_path(), 'r')
        try:
            data_container = list()
            reader = csv.DictReader(d_file, fieldnames=['id', 'text'])
            f_row = next(reader)
            if f_row['id'].lower() != 'id' and f_row['text'].lower() != 'text':
                data_container.append(
                    {'ID': f_row['id'], 'TEXT': f_row['text']}
                )
            data_container.extend([
                {'ID': row['id'], 'TEXT': row['text']}
                for row in reader
            ])
            return data_container
        except csv.Error:
            raise exc.ReadUserDataFileError(
                'Given file is not valid .csv file'
            )
        finally:
            d_file.close()  # Respect OS file descriptors

    def _parse_imed(self) -> List[Mapping[str, str]]:
        """ Parser of the .imed formatted files

        Creates:
            Rows for the projects_audiorecord table in the DB

        Raises:
            ValueError: In case of unexpected rows or errors

        Returns:
            dict_storage(list) - contains {ID:N, TEXT:N} structured dicts with
                                 imed values
        """
        imed_file = open(
            self.django_file_wrapper.temporary_file_path(),
            'rb'
        )
        try:
            data = imed_file.read()
            root = objectify.fromstring(data)
            sounds = root.Sounds.Sound
            return [
                {
                    'ID': sound.attrib['name'],
                    'TEXT': sound.attrib['description']
                }
                for sound in sounds
            ]
        except (ValueError, KeyError):
            raise exc.ReadUserDataFileError(
                'Given file is not valid .imed file'
            )
        finally:
            imed_file.close()

    def _parse_xls(self) -> List[Mapping[str, str]]:
        """ Parser of the Excel (xls, xlsx) files

        Returns:
            dict_storage(list) - contains {ID:N, TEXT:N} structured dicts with
                                 excel values

        """
        try:
            dict_storage = []
            wb = xlrd.open_workbook(
                self.django_file_wrapper.temporary_file_path()
            )
            sheet = wb.sheet_by_index(0)
            for row_idx in range(1, sheet.nrows):
                row_values = sheet.row_values(row_idx)
                if row_values[0] and row_values[1]:
                    dict_storage.append({
                        'ID': row_values[0],
                        'TEXT': row_values[1]
                    })
            if not dict_storage:
                raise xlrd.XLRDError

            return dict_storage
        except xlrd.XLRDError:
            raise exc.ReadUserDataFileError(
                'Given file is not valid .xls(x) file'
            )
        except IndexError:
            # Block on the higher level will catch this for you
            # Also, for us it is the same (Shit happens)
            raise KeyError()


class DataToAudioConverter(object):
    """ Simple parser for wrapped data

    Notes:
        Format should be like - [{id: text}, {id:text}, ...]
    """

    def __init__(
            self,
            data: List[Mapping[str, str]],
            presets: Mapping[str, Any],
            convert_cb: Callable[[str, Mapping[str, Any]], Tuple[Any, Any]]
    ) -> None:
        self.data = data
        self._presets = presets
        self.convert_text_to_tts = convert_cb

    @staticmethod
    def _escape_name_float(name: Union[str, int, float]) -> str:
        """ Escape name for row in table from undesirable symbols

        Args:
            name: Unescaped name after excel parsing

        Returns:
            Escaped name (if represented as float)

        Notes:
            Side effect of using excel format

        """
        try:
            name = str(float(name).as_integer_ratio()[0])
        except ValueError:
            pass
        return name

    def make_audio_files(self) -> List[str]:
        """ Parse given dataset

        Notes:
            Any exceptions about file content should be thrown before this part

        """
        exceptions = []
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {
                executor.submit(self._make_audio_content, row['TEXT']):
                    AudioRecord(
                        name=self._escape_name_float(row['ID']),
                        text=row['TEXT'],
                        related_project=self._presets['project'],
                        emote=self._presets['emotion'],
                        voice=self._presets['voice'],
                        source=self._presets['source'],
                        playing_speed=self._presets['speed']
                    )
                for row in self.data
                if not AudioRecord.objects.filter(
                    related_project=self._presets['project'],
                    name=self._escape_name_float(row['ID'])
                ).exists()
            }
            for future in as_completed(futures):
                audio = futures[future]
                try:
                    default, content = future.result()
                except Exception as exc:
                    exceptions.append(
                        f'Convert failed for audio with id {audio.name}'
                    )
                    continue
                audio.audio.save(f'{audio.name}.wav', content)
                audio.default_audio.save(f'{audio.name}-default.wav', default)
                audio.save()
        return exceptions

    def _make_audio_content(self, text: str) -> Tuple[Any, Any]:
        """ Create DjangoFile wrapper around binary file for audio record """
        default_file, wav_file = self.convert_text_to_tts(
            text,
            self._presets
        )
        content = ContentFile(open(wav_file.name, 'rb+').read())
        default_content = ContentFile(open(default_file.name, 'rb+').read())
        wav_file.close()
        default_file.close()
        return default_content, content


class FileParserWithAudioCreation(BaseParser):
    """ Combined parser for common audio generation """

    def __init__(
            self,
            form_file: TemporaryUploadedFile,
            cleaned_data: Mapping[str, Any],
    ) -> None:
        super().__init__(form_file)
        self._raw_form_data = cleaned_data

    def parse(self) -> List[str]:
        """ Override of the parent method (alias) """
        return self._parse_and_create_files()

    def _parse_and_create_files(self) -> List[str]:
        """ Parse data file with the parent method
            and create files next after it
        """
        parsed_rows = super().parse()
        presets = self._extract_presets()
        if presets['source'].id == 1:
            return DataToAudioConverter(
                parsed_rows,
                presets,
                YskTTS().convert_text_to_sound_via_tts_service
            ).make_audio_files()
        return DataToAudioConverter(
            parsed_rows,
            presets,
            CrtTTS().convert_text_to_sound_via_tts_service
        ).make_audio_files()

    def _extract_presets(self) -> Mapping[str, Any]:
        """ Create presets for audio converter from raw form data """
        return {
            'voice': self._raw_form_data['voice'],
            'emotion': self._raw_form_data['emotion'],

            'speed': self._raw_form_data['speed']
            if isinstance(self._raw_form_data['speed'], float)
            else float(self._raw_form_data['speed']),

            'project': IntegrationProject.objects.get(
                slug=self._raw_form_data['project']
            ),
            'source': Source.objects.get(id=self._raw_form_data['source'])
        }


def import_own_files(
        files: Mapping[str, TemporaryUploadedFile],
        *,
        qs: QuerySet,
        voice: str
) -> Generator[Mapping[Optional[str], Optional[str]], None, None]:
    """ Import own file """
    audio_list = [qs_object['name'] for qs_object in qs.values('name')]
    converter = SoxTransformerMixin()
    safe_extensions = ['.mp3', '.wav', '.raw']
    for file_name, file_ in files.items():
        file_name, extension = os.path.splitext(file_name)
        if extension not in safe_extensions:
            yield {'error': f'{file_name}{extension}', 'success': None}
        if file_name not in audio_list:
            yield {'error': file_name, 'success': None}
        else:
            if extension == '.mp3':  # SoX do not nothing about mp3 o_O
                file_ = convert_from_mp3(file_)

            audio_record: AudioRecord = qs.get(name__exact=file_name)
            wav_file = converter.convert_audio_type_format(
                user_file=file_.file,
                extension_to='wav',
                normalise=True
            )
            audio_record.source = Source.objects.get(name='Voice actor')
            audio_record.voice = voice
            audio_record.emote = 'Живые эмоции'
            audio_record.playing_speed = Decimal(1.0)
            with wav_file as converted_:
                content = converted_.read()
                audio_record.audio.save(
                    f'{file_name}_{datetime.now()}.wav',
                    ContentFile(content)
                )
                audio_record.default_audio.save(
                    f'{file_name}_{datetime.now()}-default.wav',
                    ContentFile(content)
                )
            yield {'error': None, 'success': file_name}


class WrappedTempFile(object):
    """ Wrap-up for mimicking TemporaryUploadedFile """
    def __init__(self, given_file: Any) -> None:
        self.file = given_file


def convert_from_mp3(mp3_file: TemporaryUploadedFile) -> WrappedTempFile:
    """ Make wav from mp3 file

    Args:
        mp3_file: Uploaded mp3 file on the server side

    Returns:
        Wrapped temp file (imitate temporary uploaded file)

    """
    new_file = NamedTemporaryFile(suffix='.wav')
    sound = pydub.AudioSegment.from_mp3(mp3_file.file.name)
    sound.export(new_file.name, format='wav')
    return WrappedTempFile(new_file)
