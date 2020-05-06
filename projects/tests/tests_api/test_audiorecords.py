import json

import pytest

from django.urls import reverse
from rest_framework.test import APIClient

from projects.api.serializers import RecordSerializer
from projects.models import IntegrationProject, AudioRecord

pytestmark = pytest.mark.django_db


@pytest.mark.audiorecords_api
@pytest.mark.api
class TestAudiorecords(object):
    """ Case for audiorecords API endpoints """

    def setup_class(self):
        """ Create client """
        self.client = APIClient()

    def setup_project(self):
        """ Make project and add some audios to it """
        self.project = IntegrationProject.objects.create(name='Audiotest')
        AudioRecord.objects.create(
            name='Test1',
            text='Assert me',
            playing_speed=1.0,
            emote='neutral',
            related_project=self.project,
            tts_backend_id=1,
            voice_id=1
        )

    def test_get_audio_list(self):
        """ Checks: Fetch list with audios """
        self.setup_project()
        response = self.client.get(
            path=reverse('api-audio-records-list', args=[self.project.slug])
        )
        actual = json.loads(response.content)
        expected = [
            RecordSerializer(self.project.audiorecord_set.first()).data
        ]
        assert actual == expected
