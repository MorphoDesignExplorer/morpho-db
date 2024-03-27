# Generated by Django 5.0.2 on 2024-03-09 23:12

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('project_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('creation_date', models.DateTimeField(auto_now=True, help_text='Date of Creation')),
                ('project_name', models.CharField(help_text='Project Name', max_length=256)),
                ('metadata', models.JSONField(help_text='Set of Parameters and their units')),
                ('deleted', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'project',
            },
        ),
        migrations.CreateModel(
            name='GeneratedModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('parameters', models.JSONField(help_text='Set of Parameters and their Values')),
                ('assets', models.JSONField(help_text='Set of Asset Types and their URLs')),
                ('project_key', models.ForeignKey(help_text='Foreign Key to Associated Model', on_delete=django.db.models.deletion.PROTECT, to='main_process.project')),
            ],
        ),
    ]
