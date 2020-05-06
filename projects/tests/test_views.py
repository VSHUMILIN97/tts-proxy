from shutil import which

import pytest

from django.test import RequestFactory, TestCase
from django.test import LiveServerTestCase

from selenium.webdriver.firefox.options import Options
from selenium import webdriver

from tts_backend.models import TTSBackend, TTSVoice
from projects.models import AudioRecord, IntegrationProject

from projects.views import (
    AudioRecordPageView,
    AudioRecordDeleteView
)


@pytest.mark.unit
class AudioRecordsViewsTest(TestCase):
    """ AudioRecords views test """

    def setUp(self):
        """ Setting up a Request Factory """
        self.tts = TTSBackend.objects.get(name='CRT')
        self.factory = RequestFactory()
        self.voice = TTSVoice.objects.first()
        AudioRecord.objects.create(
            name='Yame',
            text='Beaver',
            tts_backend=self.tts,
            voice=self.voice,
        )
        self.proj = IntegrationProject.objects.get(name='MANUAL_EDIT')
        self.client.session['audio_table_page'] = 1
        self.rec = AudioRecord.objects.get(name='Yame')
        self.kwargs = {'project': 'manual_edit'}

    def test_common_view_on_availability(self):
        """ Checks: It's possible to reach /audiorecords/ with get/post """
        response = self.client.get(
            '/imedgen/projects/drafts/audiorecords/'
        )
        self.assertEqual(response.status_code, 200)

    def test_common_objects_are_rendered(self):
        """ Checks: Objects from db is synced and uploaded to MP """
        AudioRecord.objects.create(
            name='Mamba',
            text='CUS WORDS :P',
            tts_backend=self.tts,
            voice=self.voice
        )
        resp = self.client.get('/imedgen/projects/drafts/audiorecords/')
        self.assertNotContains(resp, 'Boomer22814488213123n31j3j1k2b3h12bhj14')

    def test_object_view_on_availaility(self):
        """ Checks: Every object may be fetched """
        request = self.factory.get(self.rec.get_absolute_url())
        resp = AudioRecordPageView.as_view()(
            request,
            audio=self.rec.slug,
            project='drafts'
        )
        self.assertEqual(resp.status_code, 200)

    def test_delete_view_on_availability(self):
        """ Checks: Every object may be deleted from the object page """
        req = self.factory.get(f'{self.rec.get_absolute_url()}/delete')
        resp = AudioRecordDeleteView.as_view()(req, audio=self.rec.slug)
        self.assertEqual(resp.status_code, 200)
        req2 = self.factory.post(f'{self.rec.get_absolute_url()}/delete')
        resp2 = AudioRecordDeleteView.as_view()(
            req2,
            audio=self.rec.slug,
            project='manual_edit'
        )
        # REDIRECT TO THE NEXT PAGE CAUSE OF ENTRY DEL
        self.assertEqual(resp2.status_code, 302)


@pytest.mark.selenium
class SeleniumAudioRecordViewsTest(LiveServerTestCase):
    """ Functional test for the AudioRecord views """

    def setUp(self):
        """ Setting up a fake browser """
        foxy_options = Options()
        foxy_options.headless = True
        foxy_options.binary = which('firefox')
        self.selenium = webdriver.Firefox(options=foxy_options)
        super().setUp()

    def tearDown(self):
        """ Setting environment down """
        super().tearDown()
        self.selenium.quit()

    @pytest.mark.skip(reason='Cannot fix selenium driver')
    def test_main_page_contains_redirect_link(self):
        """ Broken BrokeBack """
        browser = self.selenium
        browser.get('http://127.0.0.1:8000/imedgen')
        redirect_link = browser.find_element_by_id('projects_link')
        redirect_link.click()
        self.assertContains(
            browser.current_url,
            'http://127.0.0.1:8000/imedgen/projects'
        )
