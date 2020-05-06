# Generated by Django 2.2.6 on 2019-10-17 12:24

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_delete_projectversion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=333, unique=True)),
                ('voices', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=250, unique=True), null=True, size=20)),
                ('emote', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=250, unique=True), null=True, size=None)),
                ('synth', models.BooleanField(verbose_name='Is synthesised')),
            ],
        ),
        migrations.RemoveField(
            model_name='audiorecord',
            name='emote',
        ),
        migrations.RemoveField(
            model_name='audiorecord',
            name='slug',
        ),
        migrations.RemoveField(
            model_name='integrationproject',
            name='created_at',
        ),
        migrations.AddField(
            model_name='integrationproject',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Last updated'),
        ),
        migrations.AddField(
            model_name='audiorecord',
            name='source',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, to='projects.Source'),
            preserve_default=False,
        ),
    ]
