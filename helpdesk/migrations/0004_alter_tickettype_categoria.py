# Generated by Django 5.2 on 2025-05-25 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0003_alter_ticket_calificacion_alter_ticket_estado_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tickettype',
            name='categoria',
            field=models.IntegerField(choices=[(1, 'Hardware'), (2, 'Software'), (3, 'Redes')]),
        ),
    ]
