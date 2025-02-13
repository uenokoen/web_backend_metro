# Generated by Django 5.1.1 on 2025-01-14 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metroapp', '0008_alter_routetrip_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='routetrip',
            options={'ordering': ['order'], 'verbose_name': 'Связь маршрута с поездкой', 'verbose_name_plural': 'Связи маршрутов с поездками'},
        ),
        migrations.RemoveField(
            model_name='trip',
            name='price_total',
        ),
        migrations.AddField(
            model_name='routetrip',
            name='duration',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Время проезда (минуты)'),
        ),
        migrations.AddField(
            model_name='routetrip',
            name='order',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Порядок маршрута'),
        ),
        migrations.AddField(
            model_name='trip',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Описание заявки'),
        ),
        migrations.AddField(
            model_name='trip',
            name='name',
            field=models.CharField(default=1, max_length=256, verbose_name='Название заявки'),
            preserve_default=False,
        ),
    ]
