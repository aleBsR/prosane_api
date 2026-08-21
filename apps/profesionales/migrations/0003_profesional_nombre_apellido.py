from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profesionales', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profesional',
            name='apellido',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='profesional',
            name='nombre',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]