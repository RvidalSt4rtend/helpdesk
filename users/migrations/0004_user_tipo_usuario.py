# Generated by Django 5.2 on 2025-05-25 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_user_c_campania_remove_user_cuenta_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='tipo_usuario',
            field=models.IntegerField(blank=True, choices=[(1, 'Administrador'), (2, 'Soporte'), (3, 'Cliente')], null=True),
        ),
    ]
