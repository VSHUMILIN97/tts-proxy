import string

from datetime import datetime
from typing import Any, Dict

from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SlugField
from rest_framework.reverse import reverse
from unidecode import unidecode

from ..models import AudioRecord, IntegrationProject, Source


def humanize_datetime(data: Dict[str, Any], *, field: str) -> Dict[str, Any]:
    """ Eject common logic for dt parsing """
    machine_time = data[field]
    data[field] = datetime.fromisoformat(
        machine_time
    ).strftime('%y-%m-%d %a %H:%M:%S')
    return data


class RecordSerializer(serializers.ModelSerializer):
    """ Static All query records serializer for AudioRecord model """

    def to_representation(self, instance: Any):
        """ Redefine data representation """
        data = super().to_representation(instance)
        data['source'] = instance.source.name
        data['voice'] = ''.join([
            char for char in instance.voice if char not in string.digits
        ])
        data['id'] = instance.id
        return humanize_datetime(data, field='modified_at')

    class Meta:
        model = AudioRecord
        exclude = ('default_audio', 'related_project', 'id')


class IntegrationProjectSerializer(serializers.ModelSerializer):
    """ Define basic model serializer for integration project """

    slug = SlugField(max_length=300, allow_blank=True, allow_unicode=True)

    audiorecords = serializers.SerializerMethodField('get_link_to_audios')

    def get_link_to_audios(self, object_: IntegrationProject):
        """ Make field for receiving actual link for project audio records """
        return reverse(
            'core:audio-files',
            kwargs={
                'project': object_.slug
            }
        )

    def to_internal_value(self, data: Dict[str, Any]):
        """ Redefine default behaviour for empty slug """
        if data.get('slug', '') != '':
            text = slugify(unidecode(data['slug']))
        else:
            text = slugify(unidecode(data['name']))
        data['slug'] = text
        return data

    def to_representation(self, instance: Any):
        """ Redefine datetime representation """
        data = super().to_representation(instance)
        return humanize_datetime(data, field='last_updated')

    def create(self, validated_data: Dict[str, Any]):
        """ Redefine create action if data does not comfort existence rules """
        name = validated_data['name']
        slug = validated_data['slug']
        if IntegrationProject.objects.filter(slug__exact=slug).exists():
            raise ValidationError(
                {'slug': 'Value is not unique. Make a new slug'},
                code='400'
            )
        if IntegrationProject.objects.filter(name__exact=name).exists():
            raise ValidationError(
                {'name': 'Value is not unique. Make a new name'},
                code='400'
            )
        return super().create(validated_data)

    class Meta:
        model = IntegrationProject
        fields = (
            'name', 'slug', 'audiorecords', 'last_updated',
        )


class SourceSerializer(serializers.ModelSerializer):
    """ Basic model serializer for Source model (exclude synth field) """

    class Meta:
        model = Source
        fields = (
            'name', 'voices', 'emote', 'id'
        )
