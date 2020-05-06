from django.conf import settings
from django.contrib.messages.api import error
from django.shortcuts import redirect
from django.urls.base import reverse_lazy, reverse
from django.views.generic.edit import FormView

from projects.utils import exceptions
from projects.utils.tasks import FileParserWithAudioCreation


class FileUploadAndParseView(FormView):
    """ Upload and make_audio_files file """

    template_name = 'file-add.html'

    def get(self, request, *args, **kwargs):
        """ Override GET to disallow manual_edit """
        if self.kwargs.get('project') == settings.MANUAL_EDIT_SLUG:
            return redirect(
                reverse_lazy('core:audio-files', kwargs=self.kwargs)
            )
        #
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """ Using Immediate sound generator after form validation """
        #
        form.cleaned_data['project'] = self.kwargs['project']
        try:
            FileParserWithAudioCreation(
                form.cleaned_data['file'],
                form.cleaned_data,
            ).parse()
        #
        except exceptions.FileUploadParseError as file_tts_err:
            _errs = str(file_tts_err).split('\n')
            return self.log_errors_and_redirect(_errs)
        #
        except exceptions.ReadUserDataFileError as read_usr_err:
            return self.log_errors_and_redirect([str(read_usr_err)])
        #
        return redirect(self.get_success_url())

    def log_errors_and_redirect(self, error_s):
        """ Pass errors via django message queue

        Args:
            error_s: (list) Error list (every object in list is a distinct row)

        Returns:
            HttpRequestRedirect to the same page

        """
        for err in error_s:
            error(self.request, err)
        return redirect(
            self.request.META['HTTP_REFERER']
        )

    def get_success_url(self):
        """ Appending project name to the returned success URL """
        return reverse(
            'core:audio-files',
            kwargs={'project': self.kwargs['project']}
        )
