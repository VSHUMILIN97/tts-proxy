from django.views.generic import TemplateView

from projects.mixins.imed_based import ImedBuilderMixin
from projects.mixins.form_based import JsonSoundConverterMixin


class DummyImedGeneratorView(TemplateView, ImedBuilderMixin):
    """ Class test asset. Can be requested by any HTTP methods """


class DummyJsonBasedView(TemplateView, JsonSoundConverterMixin):
    """ Class test asset. Can be requested by any HTTP methods """


class FakeResponse(object):
    """ Creating a fictional response for tests """

    def __init__(self, success=True, content=None, text='12344'):
        if success:
            self.status_code = 200
        else:
            self.status_code = 403
        self.content = b'000' if not content else content
        self.text = text
