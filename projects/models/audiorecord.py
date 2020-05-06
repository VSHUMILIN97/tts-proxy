from functools import partial

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext as _

from projects.utils import validators as vdt
from projects.utils.storage import project_path_cb

from .project_related import IntegrationProject
from .source import Source


class AudioRecordBase(models.Model):
    """ Model that contains records about audio TTS files """

    name = models.CharField(
        verbose_name=_('ID'),
        max_length=100,
        validators=[vdt.validate_name],
    )

    text = models.TextField(
        blank=False,
        unique=False,
        verbose_name=_('Text')
    )

    # ANY CALL TO UPDATE WOULDN'T BE SAVED!
    modified_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    audio = models.FileField(
        null=True,
        verbose_name=_('Record'),
        upload_to=partial(project_path_cb, root='records')
    )

    default_audio = models.FileField(
        null=True,
        verbose_name=_('Default record'),
        upload_to=partial(project_path_cb, root='records:default-audio')
    )

    playing_speed = models.DecimalField(
        max_digits=2,
        default=1,
        decimal_places=1,
        validators=[vdt.validate_speed_accuracy],
        verbose_name=_('Speed of the audio')
    )

    related_project = models.ForeignKey(
        IntegrationProject,
        on_delete=models.CASCADE,
        default='MANUAL_EDIT',
    )

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )

    voice = models.CharField(max_length=100, default='Not specified')

    emote = models.CharField(max_length=50, default='Not specified')

    class Meta:
        abstract = True

    def __str__(self):
        """ Repr for django admin """
        return self.name

    def get_absolute_url(self):
        """ Absolute path to the object in the MVC (URLification) """
        return reverse(
            'core:audio-file',
            kwargs={
                'project': self.related_project.slug,
                'audio': self.pk
            }
        )


class RecordManager(models.Manager):
    """ Manager for filtering objects by project slug and registered user """

    def get_records(self, project_slug, user_name=None):
        """ Method for fetching filtered queryset

        Args:
            project_slug: project slugified id (works as PK)
            user_name: WIP

        Returns:
            Filtered queryset

        """
        qs = super().get_queryset().filter(
            related_project__slug=project_slug,
        )
        if user_name:
            # qs.filter(user__name=user_name)
            pass
        return qs


class AudioRecord(AudioRecordBase):
    """ Child for the Abstract AudioRecord model. Imply new data manager """

    objects = models.Manager()  # Define base objects manager

    records = RecordManager()

    class Meta:

        verbose_name = _('Audio record')
        verbose_name_plural = _('Audio records')
        ordering = ('name', 'text', 'audio', 'modified_at')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """ Easiest way to update last modified field """
        self.related_project.save()
        super().save(force_insert, force_update, using, update_fields)
