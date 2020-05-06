from django.urls import path, include
from django.views.generic import TemplateView

from .views import (
    AudioRecordsCommonView,
    AudioRecordPageView,
    AudioRecordDeleteView,
    FileUploadAndParseView,
)
from imedgen.views import (
    GetAnalyticsDataSheetView,
    PackAndSendZipView,
    GetExampleExportFileView
)

app_name = 'core'

urlpatterns = [

    path(
        'projects/',
        TemplateView.as_view(template_name='projects.html'),
        name='projects',
    ),

    path(
        'projects/<slug:project>/', include([

            path(
                'file/upload',
                FileUploadAndParseView.as_view(),
                name='upload-file'
            ),

            path(
                'file/upload/broken',
                TemplateView.as_view(template_name='broken-file.html'),
                name='file-is-broken'
            ),

            path(
                'audiorecords/',
                AudioRecordsCommonView.as_view(),
                name='audio-files',
            ),

            path(
                'audiorecords/<int:audio>',
                AudioRecordPageView.as_view(),
                name='audio-file'
            ),

            path(
                'audiorecords/<int:audio>/delete',
                AudioRecordDeleteView.as_view(),
                name='audio-file-delete',
            ),

            path(
                'get-datasheet/',
                GetAnalyticsDataSheetView.as_view(),
                name='audio-analytics-ds'
            ),
            path(
                'get-imed/',
                PackAndSendZipView.as_view(),
                name='audio-media-lib'
            ),
        ]),

    ),

    path(
        'utils/', include([
            path(
                'helpers/example-csv-export',
                GetExampleExportFileView.as_view(),
                name='utils-export-example'
            )
        ])
    ),

]
