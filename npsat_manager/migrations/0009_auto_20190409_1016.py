# Generated by Django 2.1.1 on 2019-04-09 17:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('npsat_manager', '0008_auto_20190204_1859'),
    ]

    operations = [
        migrations.CreateModel(
            name='CVHMFarm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mantis_id', models.IntegerField(null=True)),
                ('name', models.CharField(max_length=255)),
                ('active_in_mantis', models.BooleanField(default=False)),
                ('farm_id', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SubBasin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mantis_id', models.IntegerField(null=True)),
                ('name', models.CharField(max_length=255)),
                ('active_in_mantis', models.BooleanField(default=False)),
                ('subbasin_id', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RenameField(
            model_name='b118basin',
            old_name='active_in_npsat',
            new_name='active_in_mantis',
        ),
        migrations.RenameField(
            model_name='b118basin',
            old_name='npsat_id',
            new_name='mantis_id',
        ),
        migrations.RenameField(
            model_name='county',
            old_name='active_in_npsat',
            new_name='active_in_mantis',
        ),
        migrations.RenameField(
            model_name='county',
            old_name='npsat_id',
            new_name='mantis_id',
        ),
        migrations.RenameField(
            model_name='modification',
            old_name='reduction',
            new_name='proportion',
        ),
        migrations.AddField(
            model_name='modelrun',
            name='county',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, related_name='model_runs', to='npsat_manager.County'),
            preserve_default=False,
        ),
    ]