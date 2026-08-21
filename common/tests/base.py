from django.apps import apps as global_apps
from django.db import connection, models
from django.test import TransactionTestCase
from django.test.utils import isolate_apps

from common.managers import SoftDeleteManager, SoftDeleteQuerySet
from common.models import UUIDPrimaryKeyModel


class AuditModelTestCase(TransactionTestCase):
    """Construye un modelo concreto efímero que hereda BaseModel.

    BaseModel es abstracto (no tiene tabla). Para probarlo creamos un modelo
    concreto en un registro de apps aislado y su tabla con schema_editor, y la
    borramos al terminar. Así no ensuciamos el esquema real.

    Usamos TransactionTestCase (en vez de TestCase) porque el schema_editor de
    SQLite necesita deshabilitar foreign keys, lo que no es posible dentro de
    un bloque atómico (que TestCase usa para aislar cada test).

    Las tablas de `personas` y `usuarios` ya existen en la base de tests porque
    sus modelos son `managed = True` y las migraciones las crean. Solo creamos
    la tabla efímera de `AuditExample`.

    IMPORTANTE: las FK a `settings.AUTH_USER_MODEL` se crean con
    `db_constraint=False` para que Django/PostgreSQL pueda hacer `flush` de la
    base de tests entre tests sin violar constraints de clave foránea con una
    tabla efímera que no conoce.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._app_isolation = isolate_apps("common", "apps.usuarios")
        isolated_apps = cls._app_isolation.enable()
        cls.addClassCleanup(cls._app_isolation.disable)

        # Re-registrar los modelos reales de usuarios en el registro
        # aislado para que ForeignKey(settings.AUTH_USER_MODEL) resuelva.
        for model in global_apps.get_app_config("usuarios").get_models():
            isolated_apps.all_models[model._meta.app_label][
                model._meta.model_name
            ] = model

        UserModel = global_apps.get_model("usuarios", "Usuario")

        class AuditExample(UUIDPrimaryKeyModel):
            name = models.CharField(max_length=50, blank=True, default="")
            created_at = models.DateTimeField(auto_now_add=True, db_index=True)
            created_year = models.IntegerField(null=True, blank=True, db_index=True)
            created_year_month = models.CharField(
                max_length=7, null=True, blank=True, db_index=True
            )
            updated_at = models.DateTimeField(auto_now=True)
            updated_year = models.IntegerField(null=True, blank=True)
            updated_year_month = models.CharField(
                max_length=7, null=True, blank=True
            )
            created_by = models.ForeignKey(
                UserModel,
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                related_name="+",
                db_column="created_by",
                db_constraint=False,
            )
            updated_by = models.ForeignKey(
                UserModel,
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                related_name="+",
                db_column="updated_by",
                db_constraint=False,
            )
            deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

            objects = SoftDeleteManager()
            all_objects = SoftDeleteQuerySet.as_manager()

            class Meta:
                app_label = "common"

            def delete(self, using=None, keep_parents=False):
                from django.utils import timezone
                self.deleted_at = timezone.now()
                self.save(update_fields=["deleted_at", "updated_at"])

            def hard_delete(self, using=None, keep_parents=False):
                super().delete(using=using, keep_parents=keep_parents)

            def restore(self):
                self.deleted_at = None
                self.save(update_fields=["deleted_at", "updated_at"])

        cls.AuditExample = AuditExample

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AuditExample)

        cls.addClassCleanup(cls._drop_tables)

    @classmethod
    def _drop_tables(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.AuditExample)

    def tearDown(self):
        # Limpiamos las filas efímeras: TransactionTestCase solo vacía modelos
        # del registro real, no nuestro AuditExample aislado. Usamos hard_delete
        # porque el delete() masivo de all_objects ahora es soft.
        self.AuditExample.all_objects.all().hard_delete()
        super().tearDown()