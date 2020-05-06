""" Service utility views storage module """
import csv
import datetime

from io import BytesIO
from typing import Any, Iterable, Tuple

import xlwt

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.views import View

from projects.mixins.imed_based import ZipFileMediaBuildMixin
from projects.models import IntegrationProject


class PackAndSendZipView(View, ZipFileMediaBuildMixin):
    """ View for creating ZIP archive with Media build on the run """

    def get(
            self,
            _request: HttpRequest,
            *_args: Any,
            **_kwargs: Any
    ) -> HttpResponse:
        """ Creating a trigger for an internal POST request """
        project = self.kwargs.get('project')
        if project is None:
            # Silent redirect in case of erasing project from a link
            return redirect('core:projects')

        return self.create_and_send_a_zip(
            IntegrationProject.objects.get(slug=project),
            self.request.GET.get('build-path')
        )


class GetAnalyticsDataSheetView(View):
    """ Get project-related audio data CSV d-sheets """

    @staticmethod
    def _make_excel(
            data: Iterable[Tuple[str, str]]
    ) -> BytesIO:
        """ Create excel file from given entry """
        mem_file = BytesIO()
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        w_book = xlwt.Workbook(encoding='utf-8')
        w_sheet: xlwt.Worksheet = w_book.add_sheet(f'Audio records')
        w_sheet.col(0).width = int(25*260)
        w_sheet.col(1).width = int(100*260)
        w_sheet.row(0).height = 260*2
        w_sheet.row(0).height_mismatch = True
        w_sheet.write(0, 0, 'ID')
        w_sheet.write(0, 1, 'TEXT')
        for index, value in enumerate(data):
            w_sheet.row(index + 1).height = 260*4
            w_sheet.row(index + 1).height_mismatch = True
            row_id, row_text = value
            w_sheet.write(index + 1, 0, row_id, style=style)
            w_sheet.write(index + 1, 1, row_text, style=style)
        w_book.save(mem_file)
        return mem_file

    def get(
            self,
            _request: HttpRequest,
            *_args: Any,
            **_kwargs: Any
    ) -> HttpResponse:
        """ Trigger for data sheet fetch """
        response = HttpResponse(content_type='application/vnd.ms-excel')
        project = IntegrationProject.objects.get(slug=self.kwargs['project'])
        cursor_iter = project.audiorecord_set.all().values_list('name', 'text')

        xls_file = self._make_excel(cursor_iter)
        response.write(xls_file.getvalue())
        response['Content-Disposition'] = (
            'attachment; '
            f'filename="{project.slug}_{datetime.datetime.now()}.xls"'
        )
        return response


class GetExampleExportFileView(View):
    """ Get export file example """

    def get(
            self,
            _request: HttpRequest,
            *_args: Any,
            **_kwargs: Any
    ) -> HttpResponse:
        """ Fetch example in CSV format """
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow(['ID', 'TEXT'])
        writer.writerow(['EXAMPLE1', 'Пример заполнения'])
        writer.writerow(['Example_2_1', 'Второй пример'])
        response['Content-Disposition'] = (
            'attachment; filename="imedgen-export-example.csv"'
        )
        return response
