import os
import re
import string
import tempfile

import lxml.builder as xml_bld
import zipfile

from io import BytesIO

from lxml import etree  # NO QA
from django.http import HttpResponse

from imedgen import loggers
from projects.mixins.sound_based import (
    SoxTransformerMixin as SoundChangerMixin,
)
from projects.models import IntegrationProject


class ImedBuilderMixin(object):
    """ Mixin for creating .imed file for AudioRecord DB model """

    def _escape_string_for_path(self, path):
        """ String should be clear as baby drop

        Args:
            path: Unescaped path

        Returns:
            path after escaping incorrect symbols

        """
        allowed_chars = ''.join([
            string.ascii_letters,
            string.digits,
            r'\/._-'
        ])
        path = ''.join([char for char in path if char in allowed_chars])
        return self._check_slash(path)

    @staticmethod
    def _check_slash(path: str):
        """ Checking path for trailing slash

        Args:
            path: With/without trailing slash

        Returns:
            path ALWAYS with trailing slash

        """
        if path.endswith('/'):
            return path

        return f'{path}/'

    def create_imed(self, audio_cursor, build_path=None):
        """ Putting .imed content (xml format) into temp file

        Args:
            audio_cursor: AudioRecord rows in DB related to certain project
            build_path: directory where Sound object are stored (for .imed)

        Returns:
            TempFile: Instance with the .imed content (xml file)

        """
        path_to_build = './client/{project}/audio/{filename}'
        alternative_path = '{path}{filename}'
        t_file = tempfile.NamedTemporaryFile()
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
                        name=entry.name,
                        file=path_to_build.format(
                            filename=f'{entry.name}.raw',
                            project=entry.related_project.slug.replace(
                                '-', '_'
                            )
                        )
                        if not build_path
                        else alternative_path.format(
                            path=self._escape_string_for_path(build_path),
                            filename=f'{entry.name}.raw'
                        ),
                        description="".join([
                            re.sub(' +', ' ', x)
                            for x in entry.text.splitlines()
                        ])
                    ) for entry in audio_cursor
                ]
            ),
            schema='1', version='Multy'
        )
        #
        with open(t_file.name, 'wb') as f:
            f.write(etree.tostring(
                xml_content,
                pretty_print=True,
                encoding='UTF-8',
                standalone='yes',
                xml_declaration=True,
            ))
        #
        return t_file


class ZipFileMediaBuildMixin(SoundChangerMixin, ImedBuilderMixin):
    """ Mixin for ZipFileView. The purpose is to split the logic """
    logger = loggers.return_logger('mediarecord')

    def create_and_send_a_zip(
            self,
            project: IntegrationProject,
            build_path: str = None
    ) -> HttpResponse:
        """ Creating a ZIP in memory using BytesIO and zipfile libraries

        Args:
            project: IntegrationProject DB record with its _set manager
            build_path: directory where Sound object are stored (for .imed)

        Returns:
            HttpResponse: Django Http object. In our case this is the response
                          with the MIME type of zip archive, so browser will
                          start download automatically

        """
        cursor = project.audiorecord_set.all().exclude(audio='')
        if not cursor.exists():
            return HttpResponse(content='NO AUDIO RECORDS!', status=404)

        wav_files = [record.audio.file for record in cursor]
        wav_filenames = [audio.name for audio in cursor]
        raw_files = []

        zip_name = f'cc_{project.slug.replace("-", "_")}_audio_loadout.zip'
        stream = BytesIO()
        zip_subdir = 'audio'
        zip_file = zipfile.ZipFile(stream, 'w')

        for cursor_file in wav_files:
            raw_files.append(
                self.convert_audio_type_format(cursor_file)
            )
        #
        if len(wav_filenames) != len(raw_files):
            #
            return HttpResponse(
                status=404,
                content='Cannot retrieve all audio records'
            )

        for file_idx, file in enumerate(raw_files):
            archive_name = f'{wav_filenames[file_idx]}.raw'
            zip_path = os.path.join(str(zip_subdir), archive_name)
            with file as file_:
                zip_file.write(str(file_.name), str(zip_path))

        temp_imed_file = self.create_imed(cursor, build_path)
        with temp_imed_file as tmp_imed:
            zip_file.write(
                tmp_imed.name,
                os.path.join(
                    zip_subdir,
                    f'{cursor.first().related_project.slug}.imed'
                )
            )

        zip_file.close()

        resp = HttpResponse(
            stream.getvalue(),
            content_type="application/x-zip-compressed"
        )
        resp['Content-Disposition'] = f'attachment; filename={zip_name}'

        return resp
