# Generated by Django 2.2.5 on 2019-11-12 18:22

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('npsat_manager', '0014_auto_20191112_1022'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modelrun',
            name='date_run',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
    ]