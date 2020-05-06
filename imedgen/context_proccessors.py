""" Service-leveled context processors storage """
from typing import Dict

from django.http.request import HttpRequest
from django.conf import settings


def version(_request: HttpRequest) -> Dict[str, str]:
    """ Create context proccessor that will pass Version for every template """
    return {'PROJECT_VERSION': settings.PROJECT_VERSION}
