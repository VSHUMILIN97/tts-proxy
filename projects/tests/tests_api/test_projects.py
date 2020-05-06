import json

import pytest
from django.core.exceptions import ObjectDoesNotExist

from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient

from projects.api.serializers import IntegrationProjectSerializer
from projects.models.project_related import IntegrationProject

pytestmark = pytest.mark.django_db


@pytest.mark.projects_api
@pytest.mark.api
class TestProjectsAPI(object):
    """ Case for each of the project related API endpoints """

    def setup_class(self):
        """ Initialise any case-related helpers """
        self.client = APIClient()

    @staticmethod
    def _make_projects():
        """ Evaluate project instances for test case """
        IntegrationProject.objects.create(name='Trump', slug='trump')
        IntegrationProject.objects.create(name='Obama', slug='obama')
        IntegrationProject.objects.create(name='Putin', slug='tsar')

    def test_get_projects(self):
        """ Checks: Get all projects via projects list API """
        self._make_projects()
        request = self.client.get(
            path=reverse('api-projects-list')
        )
        instance = IntegrationProject.objects.all().exclude(
            slug=settings.MANUAL_EDIT_SLUG
        )

        actual = json.loads(request.content)
        expected = [
            IntegrationProjectSerializer(obj).data
            for obj in instance
        ]
        assert actual == expected

    def test_create_project_full(self):
        """ Checks: Create project via POST request """
        data = {'name': 'Jesus', 'slug': 'Gabriel'}
        self.client.post(
            path=reverse('api-projects-make'),
            data=data,
            format='json'
        )
        assert IntegrationProject.objects.get(name='Jesus')

    def test_create_project_name_only(self):
        """ Checks: Make project via POST request partial data (name only) """
        data = {'name': 'BruceU'}
        request = self.client.post(
            path=reverse('api-projects-make'),
            data=data,
            format='json'
        )
        actual = IntegrationProject.objects.get(name='BruceU').slug
        assert actual == 'bruceu'
        assert request.status_code == 201

    def test_delete_project(self):
        """ Checks: Delete project from db """
        name = 'MUJIK'
        IntegrationProject.objects.create(name=name)

        instance = IntegrationProject.objects.get(name=name)
        request = self.client.delete(
            path=reverse('api-projects-destroy', args=[instance.slug])
        )
        assert request.status_code == 204
        with pytest.raises(ObjectDoesNotExist):
            IntegrationProject.objects.get(name=name)
