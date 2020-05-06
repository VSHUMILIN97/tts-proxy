from django.core.validators import validate_slug
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext as _


class IntegrationProject(models.Model):
    """ Model for integration projects """

    name = models.CharField(
        primary_key=True,
        max_length=100,
        verbose_name=_('Project name')
    )

    slug = models.SlugField(
        unique=True,
        editable=True,
        verbose_name=_('Project shortcut'),
        validators=[validate_slug],
    )

    last_updated = models.DateTimeField(
        auto_now=True,
        editable=False,
        verbose_name=_('Last updated')
    )

    def __str__(self):
        """ String representation of object """
        return self.name

    def get_absolute_url(self):
        """ Return instance of the project """
        return reverse('core:audio-files', kwargs={'project': self.slug})

    class Meta:
        verbose_name = _('Integration project')
        verbose_name_plural = _('Integration projects')
        ordering = ('name',)
