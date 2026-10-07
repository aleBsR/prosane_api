"""Renombra el rol `ayudante` → `administrativo` (los permisos no cambian).

Mueve RoleUsuario/ActionRole al nuevo UUID determinístico y actualiza
OperativoProfesional.rol_en_operativo + label de gestionarAyudantes.
Reversible.
"""
import uuid

from django.db import migrations


OLD_UUID = uuid.UUID("4e9d0fc2-d6b8-5c60-a421-bd7d1176f40f")
NEW_UUID = uuid.UUID("0a0a929c-9068-513e-96bd-0845cea37834")


def forwards(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    RoleUsuario = apps.get_model("usuarios", "RoleUsuario")
    ActionRole = apps.get_model("usuarios", "ActionRole")
    Action = apps.get_model("usuarios", "Action")
    OperativoProfesional = apps.get_model("operativos", "OperativoProfesional")

    try:
        old = Rol.objects.get(pk=OLD_UUID)
    except Rol.DoesNotExist:
        old = Rol.objects.filter(rol="ayudante").first()
    if old is None:
        return
    new, _ = Rol.objects.get_or_create(
        pk=NEW_UUID,
        defaults={"rol": "administrativo", "ruta": "/home/administrativo"},
    )
    if new.rol != "administrativo":
        new.rol = "administrativo"
        new.ruta = "/home/administrativo"
        new.save(update_fields=["rol", "ruta", "updated_at"])
    RoleUsuario.objects.filter(id_rol=old).update(id_rol=new)
    ActionRole.objects.filter(role=old).update(role=new)
    OperativoProfesional.objects.filter(rol_en_operativo="ayudante").update(
        rol_en_operativo="administrativo"
    )
    Action.objects.filter(name="gestionarAyudantes").update(
        label="Gestionar usuarios administrativos"
    )
    if str(old.pk) != str(new.pk):
        old.delete()


def backwards(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    RoleUsuario = apps.get_model("usuarios", "RoleUsuario")
    ActionRole = apps.get_model("usuarios", "ActionRole")
    Action = apps.get_model("usuarios", "Action")
    OperativoProfesional = apps.get_model("operativos", "OperativoProfesional")

    try:
        new = Rol.objects.get(pk=NEW_UUID)
    except Rol.DoesNotExist:
        new = Rol.objects.filter(rol="administrativo").first()
    if new is None:
        return
    old, _ = Rol.objects.get_or_create(
        pk=OLD_UUID,
        defaults={"rol": "ayudante", "ruta": "/home/ayudante"},
    )
    if old.rol != "ayudante":
        old.rol = "ayudante"
        old.ruta = "/home/ayudante"
        old.save(update_fields=["rol", "ruta", "updated_at"])
    RoleUsuario.objects.filter(id_rol=new).update(id_rol=old)
    ActionRole.objects.filter(role=new).update(role=old)
    OperativoProfesional.objects.filter(rol_en_operativo="administrativo").update(
        rol_en_operativo="ayudante"
    )
    Action.objects.filter(name="gestionarAyudantes").update(
        label="Gestionar usuarios ayudantes"
    )
    if str(new.pk) != str(old.pk):
        new.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0007_usuario_must_change_password"),
        ("operativos", "0005_alter_operativoprofesional_rol_en_operativo"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
