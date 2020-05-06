from typing import Dict, Any

from django.http.response import HttpResponse
from django.template.defaultfilters import urlencode
from django.urls.base import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import DeleteView, UpdateView

from projects.models import AudioRecord, IntegrationProject
from projects.utils.exceptions import (
    TTSBackendIsUnavailable,
    ChosenSpeedIsUnavailable,
    DuplicatingAudioRecord
)


__all__ = (
    'AudioRecordDeleteView',
    'AudioRecordPageView',
    'AudioRecordsCommonView'
)


class AudioRecordDeleteView(DeleteView):
    """ Generic for deleting objects.
        Works as API endpoint, but with a registered template
    """

    model = AudioRecord

    query_pk_and_slug = True

    slug_url_kwarg = 'audio'

    template_name = 'object_delete.html'

    def get_success_url(self) -> str:
        """ Appending project name to the returned success URL """
        return reverse(
            'core:audio-files',
            kwargs={'project': self.kwargs['project']}
        )


class AudioRecordsCommonView(TemplateView):
    """ Generic view for reviewing records """

    template_name = 'audio_records.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """ Standard method for setting a context into a GenericView """
        ctx = super().get_context_data(**kwargs)
        ctx['PROJECT_NAME'] = IntegrationProject.objects.get(
            slug=self.kwargs['project']
        ).name
        return ctx


class AudioRecordPageView(UpdateView):
    """ Generic for displaying object fields and change them if needed """

    model = AudioRecord

    template_name = 'record_data.html'

    slug_url_kwarg = 'audio'

    query_pk_and_slug = True

    def form_valid(self, form) -> HttpResponse:
        """ Changing form validation to append sound convert
            Or if text doesn't change just update the object
        """
        try:
            form = self.convert_data(form, is_update=True)
        except TTSBackendIsUnavailable as tts_e:
            form.add_error('tts_backend', tts_e)
            return super().form_invalid(form)
        except ChosenSpeedIsUnavailable as speed_e:
            form.add_error('speed', speed_e)
            return super().form_invalid(form)
        except DuplicatingAudioRecord as duplicate_e:
            form.add_error('name', duplicate_e)
            return super().form_invalid(form)
        return super().form_valid(form)

    def get_form_kwargs(self) -> Dict[str, Any]:
        """ FormView method for fetching kwargs with Django Form class """
        kwargs = super().get_form_kwargs()
        kwargs['project'] = IntegrationProject.objects.get(
            slug=self.kwargs['project']
        )
        return kwargs

    def get_success_url(self) -> str:
        """ Appending project name to the returned success URL """
        return self.__build_url_with_get_params(
            'core:audio-files',
            kwargs={
                'project': self.kwargs['project'],
                'get': {
                    'page': self.request.session.get('audio_table_page', 1)
                }
            },
        )

    @staticmethod
    def __build_url_with_get_params(*args: Any, **kwargs: Any) -> str:
        """ URL builder with GET parameters """
        get_params = kwargs['kwargs'].pop('get', {})
        url = reverse(*args, **kwargs)
        if get_params:
            params_build = ''.join(
                [f'{k}={urlencode(v)}&' for k, v in get_params.items()]
            )
            url += f'?{params_build}'
        return url
