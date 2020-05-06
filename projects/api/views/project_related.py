from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import AllowAny

from projects.models import IntegrationProject
from projects.api.serializers import (
    IntegrationProjectSerializer,
)


__all__ = (
    'GetProjectsView',
    'MakeProjectView',
    'DeleteProjectView',
)


class GetProjectsView(generics.ListAPIView):
    """ Basic list of integration projects (internal use) """

    queryset = IntegrationProject.objects.all().exclude(
        slug=settings.MANUAL_EDIT_SLUG
    )
    serializer_class = IntegrationProjectSerializer


class MakeProjectView(generics.CreateAPIView):
    """ Create project in the system """

    model = IntegrationProject
    serializer_class = IntegrationProjectSerializer
    queryset = IntegrationProject.objects.all()
    permission_classes = (AllowAny, )


class DeleteProjectView(generics.DestroyAPIView):
    """ Delete project in the given system """

    model = IntegrationProject
    queryset = IntegrationProject.objects.all().exclude(
        slug=settings.MANUAL_EDIT_SLUG
    )
    permission_classes = (AllowAny,)
    lookup_field = 'slug'
