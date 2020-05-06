import uuid

import unidecode

from django.db.models.signals import post_save, pre_save
from django.utils.text import slugify
from django.dispatch import receiver

from projects.models import AudioRecord, IntegrationProject


@receiver(post_save, sender=AudioRecord)
def resolve_audio_record_name(sender, instance, **kwargs):
    """ This is an additional method to erase duplicates silently
        Main check is in the form method

    Args:
        sender: Sender model
        instance: Saved instance of the AudioRecord model
        **kwargs: props for future

    Notes:
        Work silently (May be use django.contrib.messages to display errors)

    """
    if instance.related_project.audiorecord_set.filter(
            name=instance.name
    ).count() > 1:
        instance.delete()


@receiver(pre_save, sender=IntegrationProject)
def check_slug_existence(sender, instance, **kwargs):
    """ Creating a slug if none was provided and call full_clean method """
    if not instance.slug == '':
        return
    text = slugify(unidecode.unidecode(instance.name))
    if text == '':
        text = uuid.uuid4().hex
    instance.slug = text
