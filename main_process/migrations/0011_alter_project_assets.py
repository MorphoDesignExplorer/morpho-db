# Generated by Django 5.0.2 on 2024-03-21 01:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_process', '0010_alter_assetfile_generated_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='assets',
            field=models.JSONField(help_text='Set of asset names'),
        ),
    ]
