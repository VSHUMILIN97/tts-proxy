import uuid

from django.core.files.base import ContentFile
from django.db import migrations, transaction
from django.conf import settings
from django.utils import timezone


def add_man_integration(apps, schema_editor):
    """ Python OP to create a CRT backend in the DB

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    IP = apps.get_model('projects', 'IntegrationProject')
    core_project = IP(
        name='MANUAL_EDIT',
        slug=settings.MANUAL_EDIT_SLUG,
        created_at=timezone.now()
    )
    core_project.save()


def erase_man_integration(apps, schema_editor):
    """ Python OP to delete a CRT backend in the DB after migration reverse

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    IP = apps.get_model('projects', 'IntegrationProject')
    IP.objects.filter(name='MANUAL_EDIT').delete()


def add_default_record_for_audios(apps, schema_editor):
    """ Python OP to create a CRT backend in the DB

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    AR = apps.get_model('projects', 'AudioRecord')
    for audio in AR.objects.all():
        if audio.default_audio:
            continue
        new_path = audio.audio.path
        content = ContentFile(open(new_path, 'rb+').read())
        audio.default_audio.save(f'{uuid.uuid4()}.wav', content)
        audio.save()


def erase_default_records(apps, schema_editor):
    """ Python OP to delete a CRT backend in the DB after migration reverse

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    AR = apps.get_model('projects', 'AudioRecord')
    for audio in AR.objects.all():
        audio.default_audio.delete()
        audio.save()


def add_development_version(apps, schema_editor):
    """ Python OP to create a current project version

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    PV = apps.get_model('projects', 'ProjectVersion')
    pv_obj = PV(
        cur_ver='DEVELOP'
    )
    pv_obj.save()


def erase_development_version(apps, schema_editor):
    """ Python OP to delete current project version on rollback

    Args:
        apps: Registered apps in the system
        schema_editor: Schema of the DB used

    """
    PV = apps.get_model('projects', 'ProjectVersion')
    PV.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            add_man_integration,
            erase_man_integration
        ),
        migrations.RunPython(
            add_default_record_for_audios,
            erase_default_records
        ),
        migrations.RunPython(
            add_development_version,
            erase_development_version
        )
    ]
