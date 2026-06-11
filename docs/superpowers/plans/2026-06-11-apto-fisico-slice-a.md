# Apto Físico — Slice A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el "apto físico mínimo firmable" (borrador editable → firmado inmutable) como primera feature de dominio, encendiendo `crearApto`/`verApto`/`firmarApto`.

**Architecture:** Nueva app `health` con el modelo `Apto` (`managed=True`). El apto referencia un `Paciente` (NNA) y un `Usuarios` (profesional); al firmar congela snapshots (NNA + profesional) + `firma_hash` SHA-256 y queda inmutable. Lógica en `health/services.py`, vistas delgadas con `require_action`. Slice A reconcilia las tablas legacy que toca (`pacientes`, `domicilio`, `responsables`).

**Tech Stack:** Django 6 + DRF + simplejwt. Tests con el framework de Django (sqlite base) y el test runner que crea las tablas `managed=False`. Comandos con `./venv/bin/python manage.py ... --settings=config.settings.base`.

**Spec:** `docs/superpowers/specs/2026-06-11-apto-fisico-slice-a-design.md`

---

## File Structure

- **Modificar** `core/models.py` — reconciliar `Domicilio` (sin BaseModel, id AutoField).
- **Modificar** `patients/models.py` — reconciliar `Responsables` y `Pacientes`.
- **Crear** app `health/`: `__init__.py`, `apps.py`, `models.py` (Apto), `services.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`, `tests/`.
- **Modificar** `config/settings/base.py` — agregar `'health'` a INSTALLED_APPS.
- **Modificar** `config/urls.py` — montar `health.urls` en `/api/v1/aptos/`.
- **Modificar** `authentication/fixtures/actions.json` + `role_actions.json` — acción `verApto`.

Esquemas reales verificados (todos integer id, sin auditoría):
- `pacientes(id, id_domicilio, id_responsable, id_persona, edad, tiene_cud, tipo_cobertura, nombre_cobertura)`
- `domicilio(id, calle, nro_calle, piso, dpto, manzana, casa, nro_casa, pieza, provincia, departamento, localidad)`
- `responsables(id, parentesco, usuario, id_persona)`

---

## Task 1: Reconciliar Domicilio, Responsables y Pacientes (#12)

Las 3 tablas son `managed=False` con id integer y SIN columnas de auditoría, pero los modelos heredan `BaseModel` (UUID + audit) → rotas por ORM en la DB real. Se alinean igual que Personas/UserRole. Encadenadas por FK, van juntas.

**Files:**
- Modify: `core/models.py` (Domicilio)
- Modify: `patients/models.py` (Responsables, Pacientes)

- [ ] **Step 1: Reconciliar `Domicilio` en `core/models.py`**

Reemplazar la clase `Domicilio` por:

```python
class Domicilio(models.Model):
    # Reconciliación #12: tabla integer sin auditoría (no BaseModel).
    id = models.AutoField(primary_key=True)
    calle = models.CharField(max_length=100, blank=True, null=True)
    nro_calle = models.CharField(max_length=10, blank=True, null=True)
    piso = models.CharField(max_length=10, blank=True, null=True)
    dpto = models.CharField(max_length=10, blank=True, null=True)
    manzana = models.CharField(max_length=10, blank=True, null=True)
    casa = models.CharField(max_length=10, blank=True, null=True)
    nro_casa = models.CharField(max_length=10, blank=True, null=True)
    pieza = models.CharField(max_length=20, blank=True, null=True)
    provincia = models.CharField(max_length=20, blank=True, null=True)
    departamento = models.CharField(max_length=20, blank=True, null=True)
    localidad = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'domicilio'
```

- [ ] **Step 2: Reconciliar `Responsables` y `Pacientes` en `patients/models.py`**

Reemplazar ambas clases (dejar `Antecedentesfamiliares`/`Antecedentespersonales` como están por ahora — Slice A no las toca):

```python
class Responsables(models.Model):
    # Reconciliación #12: integer id, sin auditoría.
    id = models.AutoField(primary_key=True)
    parentesco = models.CharField(max_length=50)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona', null=True, blank=True)
    usuario = models.ForeignKey('authentication.Usuarios', models.DO_NOTHING, db_column='usuario', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'responsables'


class Pacientes(models.Model):
    # Reconciliación #12: integer id, sin auditoría.
    id = models.AutoField(primary_key=True)
    domicilio = models.ForeignKey('core.Domicilio', models.DO_NOTHING, db_column='id_domicilio')
    responsable = models.ForeignKey(Responsables, models.DO_NOTHING, db_column='id_responsable', null=True)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona')
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pacientes'
```

- [ ] **Step 3: Verificar que NO genera migración (managed=False, alineación de estado)**

Run: `./venv/bin/python manage.py makemigrations core patients --dry-run`
Expected: `No changes detected in apps 'core', 'patients'`

- [ ] **Step 4: Verificar en la DB real que Pacientes/Domicilio/Responsables ya se leen por ORM**

Run:
```bash
./venv/bin/python manage.py shell -c "
from patients.models import Pacientes, Responsables
from core.models import Domicilio
print('pacientes:', Pacientes.objects.count())
print('domicilio:', Domicilio.objects.count())
print('responsables:', Responsables.objects.count())
print('OK: ORM lee las 3 tablas sin error de columnas')"
```
Expected: imprime los counts sin `ProgrammingError` (antes fallaba por `created_year` inexistente).

- [ ] **Step 5: Correr la suite (regresión: el test runner ahora crea estas tablas sin audit)**

Run: `./venv/bin/python manage.py test authentication common core patients --settings=config.settings.base`
Expected: OK (todo verde).

> ⚠️ Si fallan tests de patients porque `PacientesSerializer`/`ResponsablesSerializer` referencian campos de auditoría inexistentes (created_at, etc.), ajustar esos serializers a campos explícitos del modelo reconciliado (mismo criterio que el fix #15). El test de `require_action` (que serializa la lista de pacientes) cubre esto.

- [ ] **Step 6: Commit**

```bash
git add core/models.py patients/models.py
git commit -m "fix(domain): reconcilia Domicilio/Responsables/Pacientes con la tabla real (#12)

Las 3 tablas son integer id sin auditoría; los modelos dejan de heredar BaseModel.
Destraba el ORM en la DB real (GET pacientes estaba roto como register).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Crear la app `health` y registrarla

**Files:**
- Create: `health/` (vía startapp)
- Modify: `config/settings/base.py`

- [ ] **Step 1: Crear la app**

Run: `./venv/bin/python manage.py startapp health`

- [ ] **Step 2: Agregar `'health'` a INSTALLED_APPS en `config/settings/base.py`**

En la lista `INSTALLED_APPS`, después de `'patients',` agregar:
```python
    'patients',
    'professionals',
    'health',
```
(insertar `'health',` junto a las otras apps de dominio).

- [ ] **Step 3: Verificar que el proyecto sigue cargando**

Run: `./venv/bin/python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 4: Commit**

```bash
git add health/ config/settings/base.py
git commit -m "feat(health): crea la app health (primera app de dominio del apto)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Modelo `Apto` + migración

**Files:**
- Create: `health/models.py` (contenido)
- Create: `health/migrations/0001_initial.py` (vía makemigrations)

- [ ] **Step 1: Escribir el modelo en `health/models.py`**

```python
from django.db import models

from common.models import BaseModel


class Apto(BaseModel):
    """Apto físico (Constancia standalone). Borrador editable → firmado inmutable."""
    BORRADOR = 'borrador'
    FIRMADO = 'firmado'
    ESTADO_CHOICES = ((BORRADOR, 'borrador'), (FIRMADO, 'firmado'))

    paciente = models.ForeignKey('patients.Pacientes', models.PROTECT, related_name='aptos')
    profesional = models.ForeignKey('authentication.Usuarios', models.PROTECT, related_name='aptos_firmados')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=BORRADOR)

    # editable en borrador
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    altura_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')

    # snapshots (se congelan al firmar)
    nna_dni = models.CharField(max_length=20, null=True, blank=True)
    nna_nombre_completo = models.CharField(max_length=200, null=True, blank=True)
    nna_edad = models.IntegerField(null=True, blank=True)
    profesional_nombre = models.CharField(max_length=200, null=True, blank=True)
    matricula_firmante = models.CharField(max_length=50, null=True, blank=True)

    # firma
    fecha_emision = models.DateField(null=True, blank=True)
    validez_hasta = models.DateField(null=True, blank=True)
    firma_hash = models.CharField(max_length=128, null=True, blank=True)
    timestamp_firma = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'aptos'

    @property
    def esta_firmado(self):
        return self.estado == self.FIRMADO
```

- [ ] **Step 2: Generar la migración**

Run: `./venv/bin/python manage.py makemigrations health`
Expected: `Create model Apto`.

- [ ] **Step 3: Aplicar la migración en la DB local**

Run: `./venv/bin/python manage.py migrate health`
Expected: `Applying health.0001_initial... OK`.

- [ ] **Step 4: Commit**

```bash
git add health/models.py health/migrations/0001_initial.py
git commit -m "feat(health): modelo Apto (managed=True) — borrador/firmado + snapshots + firma

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Servicios (`crear_apto`, `editar_apto`, `firmar_apto`) — TDD

Lógica de negocio pura sobre el modelo. El snapshot sale de `paciente.persona` (reconciliada) y del profesional. `matricula_firmante` queda en `None` por ahora (la matrícula vive en `professionals`, que se reconcilia en otra etapa).

**Files:**
- Create: `health/services.py`
- Create: `health/tests/__init__.py`, `health/tests/test_services.py`

- [ ] **Step 1: Escribir el test (`health/tests/test_services.py`)**

```python
from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Pacientes
from health.models import Apto
from health import services

NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


@override_settings(SEEDS_ENABLED=True)
class AptoServicesTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.medico = Usuarios.objects.get(email="medico@prosane.test")
        # NNA + paciente de prueba
        nna = Personas.objects.create(
            nombre="Niño", apellido="Prueba", dni="55000001",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01",
        )
        dom = Domicilio.objects.create(calle="Falsa", nro_calle="123", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=nna, domicilio=dom, edad=11)

    def test_crear_apto_arranca_en_borrador(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        self.assertEqual(apto.estado, Apto.BORRADOR)
        self.assertIsNone(apto.firma_hash)

    def test_editar_borrador_actualiza_campos(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.editar_apto(apto, peso_kg="40.5", altura_cm="145.0", observaciones="ok")
        apto.refresh_from_db()
        self.assertEqual(str(apto.peso_kg), "40.50")
        self.assertEqual(apto.observaciones, "ok")

    def test_firmar_congela_snapshots_y_hash(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.editar_apto(apto, peso_kg="40.5", altura_cm="145.0", observaciones="ok")
        services.firmar_apto(apto, now=NOW)
        apto.refresh_from_db()
        self.assertEqual(apto.estado, Apto.FIRMADO)
        self.assertEqual(apto.nna_dni, "55000001")
        self.assertEqual(apto.nna_nombre_completo, "Niño Prueba")
        self.assertEqual(apto.nna_edad, 11)
        self.assertEqual(apto.profesional_nombre, "Mariana Médica")
        self.assertIsNotNone(apto.firma_hash)
        self.assertEqual(apto.fecha_emision.isoformat(), "2026-06-11")
        self.assertEqual(apto.validez_hasta.isoformat(), "2027-06-11")

    def test_editar_apto_firmado_falla(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.firmar_apto(apto, now=NOW)
        with self.assertRaises(services.AptoInmutableError):
            services.editar_apto(apto, observaciones="no se puede")

    def test_firmar_dos_veces_falla(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.firmar_apto(apto, now=NOW)
        with self.assertRaises(services.AptoInmutableError):
            services.firmar_apto(apto, now=NOW)
```

- [ ] **Step 2: Correr el test → debe fallar (no existe `health.services`)**

Run: `./venv/bin/python manage.py test health.tests.test_services --settings=config.settings.base`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'health.services'`.

- [ ] **Step 3: Implementar `health/services.py`**

```python
"""Lógica de negocio del Apto físico (Slice A)."""
import hashlib
import json
from datetime import timedelta

from django.db import transaction


class AptoInmutableError(Exception):
    """Se intentó editar/firmar un apto ya firmado."""


def crear_apto(*, paciente, profesional):
    from health.models import Apto
    return Apto.objects.create(paciente=paciente, profesional=profesional)


def editar_apto(apto, *, peso_kg=None, altura_cm=None, observaciones=None):
    if apto.esta_firmado:
        raise AptoInmutableError("El apto está firmado: es inmutable.")
    if peso_kg is not None:
        apto.peso_kg = peso_kg
    if altura_cm is not None:
        apto.altura_cm = altura_cm
    if observaciones is not None:
        apto.observaciones = observaciones
    apto.save()
    return apto


def _nombre_completo(persona):
    partes = [getattr(persona, "nombre", None), getattr(persona, "apellido", None)]
    return " ".join(p for p in partes if p)


def _firma_hash(apto, timestamp):
    payload = {
        "nna_dni": apto.nna_dni,
        "nna_nombre_completo": apto.nna_nombre_completo,
        "nna_edad": apto.nna_edad,
        "peso_kg": str(apto.peso_kg),
        "altura_cm": str(apto.altura_cm),
        "profesional_nombre": apto.profesional_nombre,
        "matricula_firmante": apto.matricula_firmante,
        "timestamp_firma": timestamp.isoformat(),
    }
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


@transaction.atomic
def firmar_apto(apto, *, now):
    if apto.esta_firmado:
        raise AptoInmutableError("El apto ya está firmado.")
    persona = apto.paciente.persona
    apto.nna_dni = persona.dni
    apto.nna_nombre_completo = _nombre_completo(persona)
    apto.nna_edad = apto.paciente.edad
    prof_persona = getattr(apto.profesional, "persona", None)
    apto.profesional_nombre = _nombre_completo(prof_persona) if prof_persona else apto.profesional.email
    apto.matricula_firmante = None  # TODO: viene de professionals cuando se reconcilie
    apto.fecha_emision = now.date()
    apto.validez_hasta = now.date() + timedelta(days=365)
    apto.timestamp_firma = now
    apto.firma_hash = _firma_hash(apto, now)
    apto.estado = apto.FIRMADO
    apto.save()
    return apto
```

- [ ] **Step 4: Correr el test → verde**

Run: `./venv/bin/python manage.py test health.tests.test_services --settings=config.settings.base`
Expected: OK (5 tests).

- [ ] **Step 5: Commit**

```bash
git add health/services.py health/tests/__init__.py health/tests/test_services.py
git commit -m "feat(health): servicios del apto (crear/editar/firmar) con snapshots + firma_hash

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Serializer, vistas, urls y enforcement — TDD

**Files:**
- Create: `health/serializers.py`, `health/views.py`, `health/urls.py`
- Modify: `config/urls.py`
- Create: `health/tests/test_endpoints.py`

- [ ] **Step 1: Escribir el test de endpoints (`health/tests/test_endpoints.py`)**

```python
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Pacientes
from health.views import AptoListCreateView, AptoDetailView, AptoFirmarView


@override_settings(SEEDS_ENABLED=True)
class AptoEndpointsTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()
        self.medico = Usuarios.objects.get(email="medico@prosane.test")
        self.tutor = Usuarios.objects.get(email="tutor@prosane.test")
        nna = Personas.objects.create(nombre="Niño", apellido="Prueba", dni="55000002",
                                      tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01")
        dom = Domicilio.objects.create(calle="Falsa", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=nna, domicilio=dom, edad=11)

    def _crear(self, user):
        req = self.factory.post("/api/v1/aptos/", {"paciente": self.paciente.id}, format="json")
        force_authenticate(req, user=user)
        return AptoListCreateView.as_view()(req)

    def test_crear_apto_medico_201(self):
        resp = self._crear(self.medico)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["estado"], "borrador")
        self.assertNotIn("nna_dni", resp.data or {})  # snapshot vacío en borrador no expone dni

    def test_crear_apto_tutor_403(self):
        self.assertEqual(self._crear(self.tutor).status_code, 403)

    def test_firmar_y_luego_no_se_puede_editar(self):
        apto_id = self._crear(self.medico).data["id"]
        # firmar
        req = self.factory.post(f"/api/v1/aptos/{apto_id}/firmar/")
        force_authenticate(req, user=self.medico)
        self.assertEqual(AptoFirmarView.as_view()(req, pk=apto_id).status_code, 200)
        # editar firmado → 409
        req2 = self.factory.patch(f"/api/v1/aptos/{apto_id}/", {"observaciones": "x"}, format="json")
        force_authenticate(req2, user=self.medico)
        self.assertEqual(AptoDetailView.as_view()(req2, pk=apto_id).status_code, 409)
```

- [ ] **Step 2: Correr → falla (no existen las vistas)**

Run: `./venv/bin/python manage.py test health.tests.test_endpoints --settings=config.settings.base`
Expected: ERROR — `cannot import name 'AptoListCreateView' from 'health.views'`.

- [ ] **Step 3: Escribir `health/serializers.py`**

```python
from rest_framework import serializers

from health.models import Apto


class AptoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apto
        fields = [
            'id', 'paciente', 'profesional', 'estado',
            'peso_kg', 'altura_cm', 'observaciones',
            'nna_nombre_completo', 'nna_edad',          # nna_dni NO se expone (dato sensible)
            'profesional_nombre', 'matricula_firmante',
            'fecha_emision', 'validez_hasta', 'firma_hash', 'timestamp_firma',
        ]
        read_only_fields = [
            'estado', 'profesional', 'nna_nombre_completo', 'nna_edad',
            'profesional_nombre', 'matricula_firmante',
            'fecha_emision', 'validez_hasta', 'firma_hash', 'timestamp_firma',
        ]
```

- [ ] **Step 4: Escribir `health/views.py`**

```python
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import require_action
from health.models import Apto
from health.serializers import AptoSerializer
from health import services


class AptoListCreateView(APIView):
    def get_permissions(self):
        action = 'crearApto' if self.request.method == 'POST' else 'verApto'
        return [require_action(action)()]

    def get(self, request):
        aptos = Apto.objects.all()
        return Response(AptoSerializer(aptos, many=True).data)

    def post(self, request):
        paciente_id = request.data.get('paciente')
        if not paciente_id:
            return Response({'paciente': ['Requerido.']}, status=status.HTTP_400_BAD_REQUEST)
        from patients.models import Pacientes
        paciente = get_object_or_404(Pacientes, pk=paciente_id)
        apto = services.crear_apto(paciente=paciente, profesional=request.user)
        return Response(AptoSerializer(apto).data, status=status.HTTP_201_CREATED)


class AptoDetailView(APIView):
    def get_permissions(self):
        action = 'crearApto' if self.request.method in ('PATCH', 'PUT') else 'verApto'
        return [require_action(action)()]

    def get(self, request, pk):
        return Response(AptoSerializer(get_object_or_404(Apto, pk=pk)).data)

    def patch(self, request, pk):
        apto = get_object_or_404(Apto, pk=pk)
        try:
            services.editar_apto(
                apto,
                peso_kg=request.data.get('peso_kg'),
                altura_cm=request.data.get('altura_cm'),
                observaciones=request.data.get('observaciones'),
            )
        except services.AptoInmutableError as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(AptoSerializer(apto).data)


class AptoFirmarView(APIView):
    permission_classes = [require_action('firmarApto')]

    def post(self, request, pk):
        apto = get_object_or_404(Apto, pk=pk)
        try:
            services.firmar_apto(apto, now=timezone.now())
        except services.AptoInmutableError as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(AptoSerializer(apto).data, status=status.HTTP_200_OK)
```

- [ ] **Step 5: Escribir `health/urls.py`**

```python
from django.urls import path

from health.views import AptoListCreateView, AptoDetailView, AptoFirmarView

urlpatterns = [
    path('', AptoListCreateView.as_view(), name='apto-list-create'),
    path('<int:pk>/', AptoDetailView.as_view(), name='apto-detail'),
    path('<int:pk>/firmar/', AptoFirmarView.as_view(), name='apto-firmar'),
]
```

- [ ] **Step 6: Montar en `config/urls.py`**

Agregar el include (antes del `path('api/v1/', include('patients.urls'))` para que matchee primero):

```python
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/aptos/', include('health.urls')),
    path('api/v1/', include('patients.urls')),
```

- [ ] **Step 7: Correr el test → verde**

Run: `./venv/bin/python manage.py test health.tests.test_endpoints --settings=config.settings.base`
Expected: OK (3 tests).

- [ ] **Step 8: Commit**

```bash
git add health/serializers.py health/views.py health/urls.py config/urls.py health/tests/test_endpoints.py
git commit -m "feat(health): endpoints del apto (crear/ver/editar/firmar) con require_action

crearApto/verApto en list/detail, firmarApto en /firmar/, 409 si se edita un firmado,
nna_dni nunca se expone.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Acción `verApto` (siguiendo `docs/reglas/crear-accion.md`)

**Files:**
- Modify: `authentication/fixtures/actions.json`
- Modify: `authentication/fixtures/role_actions.json`

- [ ] **Step 1: Agregar la acción a `authentication/fixtures/actions.json`**

Agregar como último elemento del array:
```json
  { "model": "authentication.action", "pk": "a0000000-0000-0000-0000-000000000009",
    "fields": { "name": "verApto", "label": "Ver apto físico", "icon": "fact_check", "color": "#2E7D32", "type": "list", "category": "salud", "is_sensitive": true, "sort_order": 45, "is_active": true, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } }
```

- [ ] **Step 2: Vincular a medico (2) y odontologo (3) en `authentication/fixtures/role_actions.json`**

Agregar dos filas:
```json
  { "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000013", "fields": { "role": 2, "action": "a0000000-0000-0000-0000-000000000009", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } },
  { "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000014", "fields": { "role": 3, "action": "a0000000-0000-0000-0000-000000000009", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } }
```

- [ ] **Step 3: Recargar y verificar que medico tiene verApto**

Run:
```bash
./venv/bin/python manage.py reset_permissions_data && ./venv/bin/python manage.py shell -c "
from authentication.models import Usuarios
from authentication.action_resolution import effective_actions
u = Usuarios.objects.get(email='medico@prosane.test')
print('verApto' in {a['name'] for a in effective_actions(u)})"
```
Expected: `True`.

- [ ] **Step 4: Test — el endpoint GET aptos requiere verApto (tutor 403)**

Agregar a `health/tests/test_endpoints.py`:
```python
    def test_listar_aptos_tutor_sin_verApto_403(self):
        req = self.factory.get("/api/v1/aptos/")
        force_authenticate(req, user=self.tutor)
        self.assertEqual(AptoListCreateView.as_view()(req).status_code, 403)

    def test_listar_aptos_medico_con_verApto_200(self):
        req = self.factory.get("/api/v1/aptos/")
        force_authenticate(req, user=self.medico)
        self.assertEqual(AptoListCreateView.as_view()(req).status_code, 200)
```

Run: `./venv/bin/python manage.py test health.tests.test_endpoints --settings=config.settings.base`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add authentication/fixtures/actions.json authentication/fixtures/role_actions.json health/tests/test_endpoints.py
git commit -m "feat(permisos): acción verApto (lectura de aptos) vía el playbook

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Admin + suite completa + smoke real

**Files:**
- Modify: `health/admin.py`

- [ ] **Step 1: Registrar Apto en el admin (`health/admin.py`)**

```python
from django.contrib import admin

from health.models import Apto


@admin.register(Apto)
class AptoAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'profesional', 'estado', 'fecha_emision')
    list_filter = ('estado',)
    readonly_fields = ('firma_hash', 'timestamp_firma')
```

- [ ] **Step 2: Suite completa**

Run: `./venv/bin/python manage.py test authentication common core patients health --settings=config.settings.base`
Expected: OK (todo verde).

- [ ] **Step 3: Smoke real (medico crea → firma → no edita)**

Levantar el server (`./venv/bin/python manage.py runserver`), loguear como `medico@prosane.test` / la pass de seeds, y verificar manualmente o por curl: `POST /api/v1/aptos/` (201), `POST /api/v1/aptos/<id>/firmar/` (200), `PATCH /api/v1/aptos/<id>/` (409). (Requiere un paciente cargado.)

- [ ] **Step 4: Commit**

```bash
git add health/admin.py
git commit -m "feat(health): admin del Apto + cierre de Slice A

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notas de cierre

- **Diferido a Slice B/C:** Consentimiento; CIS + bloque clínico (antropometría/presión/etc.); `cis_id`; `pdf_url`; `vacunas_estado`; `matricula_firmante` real (requiere reconciliar `professionals`).
- `firma_hash` es integridad (SHA-256), no firma criptográfica con clave — documentado en el spec.
- La reconciliación de Task 1 además **destraba los endpoints de pacientes** en la DB real.
