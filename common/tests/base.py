from django.apps import apps as global_apps
from django.db import connection, models
from django.test import TransactionTestCase
from django.test.utils import isolate_apps

from common.models import BaseModel
from core.models import Personas


class AuditModelTestCase(TransactionTestCase):
    """Construye un modelo concreto efímero que hereda BaseModel.

    BaseModel es abstracto (no tiene tabla). Para probarlo creamos un modelo
    concreto en un registro de apps aislado y su tabla con schema_editor, y la
    borramos al terminar. Así no ensuciamos el esquema real.

    Usamos TransactionTestCase (en vez de TestCase) porque el schema_editor de
    SQLite necesita deshabilitar foreign keys, lo que no es posible dentro de
    un bloque atómico (que TestCase usa para aislar cada test).

    Después de activar isolate_apps copiamos los modelos de authentication al
    registro aislado para que las ForeignKey de AuditModel resuelvan.

    Creamos también la tabla `personas` (managed=False en el proyecto, así que
    las migraciones no la crean en el test DB) porque Usuarios tiene una FK
    nullable a ella y SQLite verifica la referencia. La construimos desde el
    modelo real con schema_editor para que no haya drift de esquema.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._app_isolation = isolate_apps("common", "authentication")
        isolated_apps = cls._app_isolation.enable()
        cls.addClassCleanup(cls._app_isolation.disable)

        # Re-registrar los modelos reales de authentication en el registro
        # aislado para que ForeignKey(settings.AUTH_USER_MODEL) resuelva.
        for model in global_apps.get_app_config("authentication").get_models():
            isolated_apps.all_models[model._meta.app_label][
                model._meta.model_name
            ] = model

        class AuditExample(BaseModel):
            name = models.CharField(max_length=50, blank=True, default="")

            class Meta:
                app_label = "common"

        cls.AuditExample = AuditExample

        # El test runner (config.test_runner) ya crea las tablas managed=False,
        # incluida `personas`. Solo la creamos acá si no está (compatibilidad).
        existing = set(connection.introspection.table_names())
        cls._created_personas = Personas._meta.db_table not in existing
        with connection.schema_editor() as schema_editor:
            if cls._created_personas:
                schema_editor.create_model(Personas)
            schema_editor.create_model(AuditExample)

        cls.addClassCleanup(cls._drop_tables)

    @classmethod
    def _drop_tables(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.AuditExample)
            if getattr(cls, "_created_personas", False):
                schema_editor.delete_model(Personas)

    def tearDown(self):
        # Limpiamos las filas efímeras: TransactionTestCase solo vacía modelos
        # del registro real, no nuestro AuditExample aislado. Usamos hard_delete
        # porque el delete() masivo de all_objects ahora es soft.
        self.AuditExample.all_objects.all().hard_delete()
        super().tearDown()
