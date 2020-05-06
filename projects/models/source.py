from django.db import models
from django.contrib.postgres.fields import ArrayField


__all__ = (
    'Source',
)


class Source(models.Model):
    """ Audio source descriptor """

    name = models.CharField(
        max_length=333,
        unique=True,
        null=False,
        blank=False
    )

    voices = ArrayField(
        models.CharField(max_length=250, unique=True, blank=False, null=False),
        null=True,
        size=20
    )

    emote = ArrayField(
        models.CharField(max_length=250, unique=True),
        null=True
    )

    synth = models.BooleanField(
        blank=False,
        null=False,
        verbose_name='Is synthesised'
    )
