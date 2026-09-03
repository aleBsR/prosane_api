# Generated for PROSANE - contraseña temporal + cambio obligatorio
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_action_show_in_menu'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='must_change_password',
            field=models.BooleanField(default=False, db_column='must_change_password'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='temporal_password_expires_at',
            field=models.DateTimeField(blank=True, db_column='temporal_expires_at', null=True),
        ),
    ]
