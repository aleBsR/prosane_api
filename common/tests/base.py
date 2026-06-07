from django.apps import apps as global_apps
from django.db import connection, models
from django.test import TransactionTestCase
from django.test.utils import isolate_apps

from common.models import BaseModel


class AuditModelTestCase(TransactionTestCase):
    """Construye un modelo concreto efímero que hereda BaseModel.

    BaseModel es abstracto (no tiene tabla). Para probarlo creamos un modelo
    concreto en un registro de apps aislado y su tabla con schema_editor, y la
    borramos al terminar. Así no ensuciamos el esquema real.

    Usamos TransactionTestCase (en vez de TestCase) porque el schema_editor de
    SQLite necesita deshabilitar foreign keys, lo que no es posible dentro de
    un bloque atómico (que TestCase usa para aislar cada test).

    Después de activar isolate_apps copiamos los modelos de authentication del
    registro global al aislado para que las ForeignKey de AuditModel puedan
    resolverse.

    En setUp creamos la tabla personas (managed=False en el proyecto, pero
    necesaria en el test DB porque Usuarios tiene FK nullable a ella y SQLite
    verifica constraints aunque el valor sea NULL). La borramos en tearDown.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._app_isolation = isolate_apps("common", "authentication")
        isolated_apps = cls._app_isolation.enable()

        # Re-register real authentication models into the isolated registry so
        # that ForeignKey(settings.AUTH_USER_MODEL) resolves correctly.
        for model in global_apps.get_app_config("authentication").get_models():
            isolated_apps.all_models[model._meta.app_label][
                model._meta.model_name
            ] = model

        class AuditExample(BaseModel):
            name = models.CharField(max_length=50, blank=True, default="")

            class Meta:
                app_label = "common"

        cls.AuditExample = AuditExample

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AuditExample)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.AuditExample)
        cls._app_isolation.disable()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Create the personas table that Usuarios has a nullable FK to.
        # core.Personas is managed=False so it's never created by migrations
        # in the test DB, but SQLite still validates FK references on insert.
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS personas "
                "(id INTEGER PRIMARY KEY, nombre VARCHAR(256), "
                "apellido VARCHAR(256), dni VARCHAR(256), tipo_dni VARCHAR(256))"
            )

    def tearDown(self):
        # Clear the ephemeral AuditExample rows (TransactionTestCase flushes
        # only models known to the real app registry; our isolated model is
        # not in it, so we clean it up manually).
        self.AuditExample.all_objects.all().delete()
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS personas")
        super().tearDown()
