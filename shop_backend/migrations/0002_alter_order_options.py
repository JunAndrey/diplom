# Generated by Django 4.2.3 on 2023-07-16 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop_backend', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ('-dt',), 'verbose_name': 'Заказ', 'verbose_name_plural': 'Список-заказ'},
        ),
    ]
