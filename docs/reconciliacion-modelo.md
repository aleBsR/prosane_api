# Reconciliación del modelo de datos

> **Estado: ABIERTO — pendiente de decisión de Roberto.**
> Este documento NO define el modelo final. Solo deja por escrito que hoy conviven
> **tres vocabularios distintos** para la misma realidad, para que el equipo no
> programe en direcciones opuestas. La inspección fina de las tablas ya creadas la
> hace Roberto por separado.

---

## El problema: tres modelos que no coinciden

| # | Fuente | Vocabulario / entidades clave | Roles |
|---|--------|-------------------------------|-------|
| 1 | `docs/modelo-de-datos.md` (TPFinal, basado en planilla PROSANE oficial) | `NNA`, `PerfilFamilia`, `PerfilProfesional`, `PerfilEscuela`, `ControlIntegralSalud` (CIS), `Consentimiento`, `Constancia`, `Derivacion`, `Especialidad`, bloques clínicos (Antropometria, PresionArterial, etc.) | `familia` / `profesional` / `escuela` / `admin` |
| 2 | `prosane_propuesta.md` (raíz del repo) | `Tutor`, `Paciente`, `Escuela`, `Visita`, `Ficha`, `Derivacion`, tabla pivot `visita_profesionales` | `superusuario` / `profesional` / `ayudante` / `tutor` / `paciente` |
| 3 | **Código actual** (`*/models.py`) | `Personas`, `Usuarios`, `Roles`, `UserRole`, `Domicilio`, `Pacientes`, `Responsables`, `Antecedentespersonales`, `Antecedentesfamiliares`, `Profesionales` | seed de `Roles`: medico, odontologo, tutor, ayudante, superusuario, usuario |

### Cómo se mapean (aproximado)

| Concepto | Modelo 1 (planilla) | Modelo 2 (propuesta) | Código actual |
|----------|---------------------|----------------------|---------------|
| Alumno controlado | `NNA` | `Paciente` | `Pacientes` + `Personas` |
| Adulto responsable | `PerfilFamilia` | `Tutor` | `Responsables` + `Personas` |
| Profesional de salud | `PerfilProfesional` | `profesional` | `Profesionales` + `Usuarios` |
| La planilla / control | `ControlIntegralSalud` (CIS) | `Ficha` | **no existe aún** |
| Agendamiento operativo | *(no existe)* | `Visita` + `ayudante` | **no existe aún** |
| Datos personales | inline en cada entidad | inline | `Personas` (tabla compartida) |

---

## Las dos diferencias de fondo (no son solo nombres)

1. **¿Existe una capa operativa de "Visita"?**
   - El **Modelo 2 / código** introducen `ayudante` + `Visita` (un equipo agendado para
     ir a una escuela una fecha dada) y `Ficha` cuelga de la visita.
   - El **Modelo 1** NO tiene eso: el `CIS` cuelga directo del `NNA` y referencia escuela,
     curso e institución de salud como snapshots. No hay agendamiento ni rol `ayudante`.
   - **No son contradictorios**: una `Visita` podría agrupar varios `CIS`. Pero hay que
     decidir si esa capa entra al MVP o no.

2. **Nomenclatura: `NNA` vs `Paciente`, `Familia` vs `Tutor`.**
   - El Modelo 1 usa el lenguaje **legal/clínico oficial** (NNA = Niño/Niña/Adolescente,
     según Ley 26.061). El código usa `Paciente`/`Responsable`.
   - Conviene elegir **un** vocabulario y usarlo en todo: modelos, serializers, endpoints,
     y la app Flutter. Mezclarlos genera bugs y confusión en el equipo.

---

## ¿Se pueden fusionar? — Sí, es viable

Los tres modelos describen el mismo dominio; la fusión es **factible** y de complejidad
media. El trabajo real no es técnico sino de **decisión de alcance y vocabulario**:

- [ ] **Decidir el vocabulario canónico** (recomendación: el del Modelo 1 / planilla,
      porque está atado a la planilla oficial y al marco legal — `NNA`, `CIS`, etc.).
- [ ] **Decidir si entra la capa `Visita` / `ayudante`** al MVP, o si el `CIS` cuelga
      directo del `NNA` como en el Modelo 1.
- [ ] **Decidir el destino de las tablas ya creadas** (`Personas`, `Pacientes`,
      `Responsables`, etc., casi todas `managed=False`). → *Roberto las analiza aparte.*
- [ ] **Unificar el centro del modelo**: hoy falta la entidad central `ControlIntegralSalud`
      (la planilla) en el código. Es la pieza más importante y todavía no existe.

> ⚠️ Recordatorio técnico: casi todas las tablas del código tienen `managed = False`
> (Django no controla su esquema; salieron de un `inspectdb` sobre una base existente).
> Cualquier decisión de fusión tiene que aclarar primero **quién es dueño del esquema**:
> ¿Django con migraciones, o una base externa ya creada?

---

## Recomendación (para discutir, no para ejecutar todavía)

1. Adoptar el **Modelo 1 (planilla PROSANE)** como fuente de verdad del dominio, por su
   anclaje legal y su trazabilidad con la planilla oficial.
2. Tratar el **Modelo 2 (`Visita`/`ayudante`)** como una **extensión operativa opcional**
   a evaluar después del MVP.
3. Migrar el código hacia ese vocabulario de forma incremental, empezando por crear la
   entidad faltante `ControlIntegralSalud`.
4. Pasar `managed = True` en las tablas que Django deba controlar, o documentar
   explícitamente por qué siguen siendo externas.
