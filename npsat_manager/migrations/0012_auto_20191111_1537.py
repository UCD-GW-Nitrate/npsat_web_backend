# Generated by Django 2.2.5 on 2019-11-11 23:37

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('npsat_manager', '0011_auto_20191111_1440'),
    ]

    operations = [
        migrations.AddField(
            model_name='modelrun',
            name='ready',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='modelrun',
            name='date_run',
            field=models.DateTimeField(default=datetime.datetime(2019, 11, 11, 23, 37, 0, 435755, tzinfo=utc), null=True),
        ),
    ]