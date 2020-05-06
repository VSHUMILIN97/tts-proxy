from rest_framework import generics
from rest_framework.permissions import AllowAny

from projects.models import Source
from projects.api.serializers import SourceSerializer


class GetSynthSourcesView(generics.ListAPIView):
    """ Basic list of integration projects (internal use) """

    queryset = Source.objects.filter(synth__exact=True)
    permission_classes = (AllowAny, )
    serializer_class = SourceSerializer
