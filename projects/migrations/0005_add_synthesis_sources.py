from django.db import migrations
from django.conf import settings


def add_sources(apps, _schema_editor):
    """ Python OP to create a CRT backend in the DB

    Args:
        apps: Registered apps in the system
        _schema_editor: Schema of the DB used

    """
    SOURCE = apps.get_model('projects', 'Source')
    SOURCE.objects.create(
        name='Yandex Speech Kit',
        voices=settings.YANDEX_VOICES,
        emote=settings.YANDEX_EMOTE,
        synth=True,
    )
    SOURCE.objects.create(
        name='Center of speech technologies',
        voices=settings.CRT_VOICES,
        emote=None,
        synth=True,
    )
    SOURCE.objects.create(
        name='Voice actor',
        voices=['Male', 'Female'],
        emote=None,
        synth=False,
    )


def erase_sources(apps, _schema_editor):
    """ Python OP to delete a CRT backend in the DB after migration reverse

    Args:
        apps: Registered apps in the system
        _schema_editor: Schema of the DB used

    """
    SOURCE = apps.get_model('projects', 'Source')
    SOURCE.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_auto_20191017_1724'),
    ]

    operations = [
        migrations.RunPython(
            add_sources,
            erase_sources
        ),
    ]
