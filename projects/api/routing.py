from django.urls import path, register_converter

from .route_converters import OptionalValue, OptionalValueInteger

from .views import (
    GetRecordsForProjectView,
    GetProjectsView,
    MakeProjectView,
    DeleteProjectView,
    MakeYSKRecordView,
    MakeCRTRecordView,
    DestroyAudioView,
    GetSynthSourcesView,
    FileImportView,
    UpdateRecordView,
    ImportOwnFilesView,
)
urlpatterns = []

register_converter(OptionalValue, 'optional')
register_converter(OptionalValueInteger, 'optint')


app_name = 'api'

# Projects URI's
urlpatterns += [
    path('projects/', GetProjectsView.as_view(), name='projects-list'),
    path(
        'projects/make/',
        MakeProjectView.as_view(),
        name='projects-make'
    ),
    path(
        'projects/destroy/<optional:slug>',
        DeleteProjectView.as_view(),
        name='projects-destroy'
    )
]

# Audio records URI's
urlpatterns += [
    path(
        'audiorecords/<slug:project>',
        GetRecordsForProjectView.as_view(),
        name='audio-records-list'
    ),
    path(
        'audiorecords/<slug:project>/yandex',
        MakeYSKRecordView.as_view(),
        name='audio-make-yandex'
    ),
    path(
        'audiorecords/<slug:project>/crt',
        MakeCRTRecordView.as_view(),
        name='audio-make-crt'
    ),
    path(
        'audiorecords/<slug:project>/update-audio/<optint:primary_key>',
        UpdateRecordView.as_view(),
        name='audio-update'
    ),
    path(
        'audiorecords/<slug:project>/destroy/<optint:id>',
        DestroyAudioView.as_view(),
        name='audio-destroy'
    ),
    path(
        'audiorecords/<slug:project>/import-file',
        FileImportView.as_view(),
        name='audio-file-import'
    ),
    path(
        'audiorecords/<slug:project>/import-own',
        ImportOwnFilesView.as_view(),
        name='audio-own-import'
    )
]

# Source URI's
urlpatterns += [
    path(
        'sources/list-tts',
        GetSynthSourcesView.as_view(),
        name='synth-sources'
    )
]
