"""Crea auditoria_usuarios y renombra la acción gestionarAyudantes →
gestionarAdministrativos (el rol ya se había renombrado en 0008).

El rename es in-place sobre la misma fila (conserva id y relaciones
ActionRole). Reversible.
"""
from django.db import migrations, models
import uuid


def forwards(apps, schema_editor):
    Action = apps.get_model("usuarios", "Action")
    Action.objects.filter(name="gestionarAyudantes").update(
        name="gestionarAdministrativos"
    )


def backwards(apps, schema_editor):
    Action = apps.get_model("usuarios", "Action")
    Action.objects.filter(name="gestionarAdministrativos").update(
        name="gestionarAyudantes"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0008_rename_ayudante_administrativo"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditoriaUsuario",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("created_year", models.IntegerField(blank=True, db_index=True, null=True)),
                (
                    "created_year_month",
                    models.CharField(blank=True, db_index=True, max_length=7, null=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_year", models.IntegerField(blank=True, null=True)),
                (
                    "updated_year_month",
                    models.CharField(blank=True, max_length=7, null=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="created_by",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="+",
                        to="usuarios.usuario",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="updated_by",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="+",
                        to="usuarios.usuario",
                    ),
                ),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("accion", models.CharField(max_length=32)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_actor",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="auditorias_realizadas",
                        to="usuarios.usuario",
                    ),
                ),
                (
                    "objetivo",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_objetivo",
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="auditorias_recibidas",
                        to="usuarios.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "auditoria_usuarios",
            },
        ),
        migrations.RunPython(forwards, backwards),
    ]
