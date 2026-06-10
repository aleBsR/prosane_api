"""Test runner que crea en el test DB las tablas `managed=False`.

El proyecto tiene tablas legacy (`roles`, `usuarios`, `personas`, `user_role`, …)
declaradas con `managed=False` (vienen de inspectdb). En producción su esquema lo
posee otro proceso; pero en los TESTS necesitamos esas tablas para que los modelos
`managed=True` que las referencian por FK (p. ej. role_actions → roles) funcionen,
y para que el flush de TransactionTestCase no falle.

`migrate` NO crea esas tablas (sus migraciones registran managed=False en el estado
histórico). Por eso, tras crear el test DB, las construimos a mano con schema_editor
a partir de los modelos vivos.
"""
from django.apps import apps
from django.db import connections
from django.test.runner import DiscoverRunner


class ManagedModelTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        connection = connections["default"]
        existing = set(connection.introspection.table_names())
        unmanaged = [m for m in apps.get_models() if not m._meta.managed]
        with connection.schema_editor() as schema_editor:
            for model in unmanaged:
                if model._meta.db_table not in existing:
                    schema_editor.create_model(model)
                    existing.add(model._meta.db_table)
        return result
