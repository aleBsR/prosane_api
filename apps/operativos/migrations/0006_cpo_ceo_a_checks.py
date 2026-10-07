"""CPO/ceo de cantidades a checks (booleanos), como la planilla física.

La planilla solo marca si se hizo alguno: no se registran cantidades.
Conversión en el propio USING: NULL/0 → False, >0 → True.
Reversible en esquema (el rollback deja booleanos; los datos no se
restauran a cantidades).
"""
from django.db import connection, migrations, models

CAMPOS = ["cpo_c", "cpo_p", "cpo_o", "ceo_c", "ceo_e", "ceo_o"]
TABLA = "operativos_evaluaciones_odontologicas"

# Los ALTER con USING solo existen en PostgreSQL. En SQLite (suite de tests)
# el esquema se crea desde el estado (booleanos directos) sin conversión.
ES_POSTGRES = connection.vendor == "postgresql"

# Un ALTER por sentencia (listas, no un solo execute multi-sentencia).
SQL_FORWARDS = (
    [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} TYPE boolean "
        f"USING ({c} IS NOT NULL AND {c} <> 0)"
        for c in CAMPOS
    ]
    + [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} SET DEFAULT false"
        for c in CAMPOS
    ]
    + [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} SET NOT NULL"
        for c in CAMPOS
    ]
)

SQL_BACKWARDS = (
    [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} DROP NOT NULL"
        for c in CAMPOS
    ]
    + [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} DROP DEFAULT"
        for c in CAMPOS
    ]
    + [
        f"ALTER TABLE {TABLA} ALTER COLUMN {c} TYPE integer USING ({c}::int)"
        for c in CAMPOS
    ]
)


class Migration(migrations.Migration):
    dependencies = [
        ("operativos", "0005_alter_operativoprofesional_rol_en_operativo"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=(
                [migrations.RunSQL(SQL_FORWARDS, SQL_BACKWARDS)]
                if ES_POSTGRES
                else []
            ),
            state_operations=[
                migrations.AlterField(
                    model_name="evaluacionodontologica",
                    name=campo,
                    field=models.BooleanField(default=False),
                )
                for campo in CAMPOS
            ],
        ),
    ]
