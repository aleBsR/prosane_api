# Consentimiento — Slice B — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar el consentimiento de la familia (un paso, inmutable) con `firma_tipo` (adulto/NNA≥13) y `firma_hash`, encendiendo `darConsentimiento`/`verConsentimiento`.

**Architecture:** Modelo `Consentimiento` (`managed=True`) en la app `patients`, linkeado a un `Paciente` (standalone hasta que exista el CIS). Crear = consentir: el POST snapshotea la identidad que manda el front y calcula `firma_hash` + `fecha_firma`. Lógica en `patients/services.py`, vistas delgadas con `require_action`.

**Tech Stack:** Django 6 + DRF + simplejwt. Tests con el runner custom (crea tablas managed=False). Comandos: `./venv/bin/python manage.py ... --settings=config.settings.base`.

**Spec:** `docs/superpowers/specs/2026-06-11-consentimiento-slice-b-design.md`

---

## File Structure

- **Modificar** `patients/models.py` — agregar el modelo `Consentimiento` (managed=True).
- **Crear** `patients/migrations/0001_initial.py` (vía makemigrations — solo `Consentimiento`).
- **Crear** `patients/services.py` — `crear_consentimiento`.
- **Modificar** `patients/serializers.py` — `ConsentimientoSerializer` (adulto_dni write_only).
- **Modificar** `patients/views.py` — `ConsentimientoListCreateView`, `ConsentimientoDetailView`.
- **Modificar** `patients/urls.py` — rutas `consentimientos/` con `<uuid:pk>`.
- **Crear** `patients/tests/__init__.py`, `patients/tests/test_consentimiento.py`, `patients/tests/test_urls.py`.
- **Modificar** fixtures + `actions_map.py` + tests de conteo — acción `verConsentimiento`.

> ⚠️ `patients` puede tener un `tests.py` default. Si existe, convertilo a paquete (`git rm patients/tests.py` + crear `patients/tests/`). Verificá al empezar la Task 2.

---

## Task 1: Modelo `Consentimiento` + migración

**Files:**
- Modify: `patients/models.py`
- Create: `patients/migrations/0001_initial.py`

- [ ] **Step 1: Agregar el modelo al final de `patients/models.py`**

```python
from common.models import BaseModel  # (ya importado arriba para Antecedentes*)


class Consentimiento(BaseModel):
    """Consentimiento de la familia (Ley 26.529). Un paso: crear = consentir; inmutable."""
    ADULTO_RESPONSABLE = 'adulto_responsable'
    NNA_MAYOR_13 = 'nna_mayor_13'
    FIRMA_TIPO_CHOICES = (
        (ADULTO_RESPONSABLE, 'Adulto responsable'),
        (NNA_MAYOR_13, 'NNA mayor de 13'),
    )

    paciente = models.ForeignKey('patients.Pacientes', models.PROTECT, related_name='consentimientos')
    firma_tipo = models.CharField(max_length=20, choices=FIRMA_TIPO_CHOICES)

    # identidad de quien consiente (la manda el front, se snapshotea)
    adulto_nombre = models.CharField(max_length=200)
    adulto_apellido = models.CharField(max_length=200)
    adulto_tipo_documento = models.CharField(max_length=20)
    adulto_dni = models.CharField(max_length=15)

    # firma / trazabilidad
    firma_hash = models.CharField(max_length=128)
    fecha_firma = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'consentimientos'
```

- [ ] **Step 2: Generar la migración**

Run: `./venv/bin/python manage.py makemigrations patients`
Expected: `Create model Consentimiento` (crea `patients/migrations/` con `__init__.py` si no existía). NO debe aparecer ninguno de los modelos `managed=False`.

- [ ] **Step 3: Aplicar la migración en la DB local**

Run: `./venv/bin/python manage.py migrate patients`
Expected: `Applying patients.0001_initial... OK`.

- [ ] **Step 4: Commit**

```bash
git add patients/models.py patients/migrations/
git commit -m "feat(patients): modelo Consentimiento (managed=True) — un paso, inmutable

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Servicio `crear_consentimiento` — TDD

**Files:**
- Create: `patients/services.py`
- Create: `patients/tests/__init__.py`, `patients/tests/test_consentimiento.py`

- [ ] **Step 0: Si existe `patients/tests.py`, convertí a paquete**

Run (si aplica): `git rm patients/tests.py` y creá `patients/tests/__init__.py` vacío.
(Si no existe `patients/tests.py`, creá igual `patients/tests/__init__.py`.)

- [ ] **Step 1: Escribir `patients/tests/test_consentimiento.py`**

```python
from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Consentimiento, Pacientes
from patients import services

NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


@override_settings(SEEDS_ENABLED=True)
class CrearConsentimientoTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self._nna = Personas.objects.create(nombre="Niño", apellido="Prueba", dni="66000001",
                                            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01")
        self._dom = Domicilio.objects.create(calle="Falsa", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=self._nna, domicilio=self._dom, edad=11)

    def tearDown(self):
        Consentimiento.all_objects.filter(paciente=self.paciente).hard_delete()
        Pacientes.objects.filter(id=self.paciente.id).delete()
        Personas.objects.filter(id=self._nna.id).delete()
        Domicilio.objects.filter(id=self._dom.id).delete()
        super().tearDown()

    def _crear(self):
        return services.crear_consentimiento(
            paciente=self.paciente, firma_tipo=Consentimiento.ADULTO_RESPONSABLE,
            adulto_nombre="Marta", adulto_apellido="Tutora",
            adulto_tipo_documento="DNI", adulto_dni="22333444", now=NOW,
        )

    def test_crea_firmado_con_hash_y_fecha(self):
        c = self._crear()
        self.assertEqual(c.firma_tipo, Consentimiento.ADULTO_RESPONSABLE)
        self.assertEqual(c.adulto_nombre, "Marta")
        self.assertTrue(c.firma_hash)
        self.assertEqual(c.fecha_firma, NOW)

    def test_hash_cambia_si_cambia_el_payload(self):
        c1 = self._crear()
        c2 = services.crear_consentimiento(
            paciente=self.paciente, firma_tipo=Consentimiento.NNA_MAYOR_13,
            adulto_nombre="Otro", adulto_apellido="Distinto",
            adulto_tipo_documento="DNI", adulto_dni="99888777", now=NOW,
        )
        self.assertNotEqual(c1.firma_hash, c2.firma_hash)
```

- [ ] **Step 2: Correr → falla (no existe `patients.services`)**

Run: `./venv/bin/python manage.py test patients.tests.test_consentimiento --settings=config.settings.base`
Expected: ERROR — `cannot import name 'services'` / `No module named 'patients.services'`.

- [ ] **Step 3: Implementar `patients/services.py`**

```python
"""Lógica de negocio de patients (Slice B: consentimiento)."""
import hashlib
import json


def _firma_hash(*, firma_tipo, nombre, apellido, tipo_doc, dni, timestamp):
    payload = {
        "firma_tipo": firma_tipo,
        "nombre": nombre,
        "apellido": apellido,
        "tipo_documento": tipo_doc,
        "dni": dni,
        "fecha_firma": timestamp.isoformat(),
    }
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def crear_consentimiento(*, paciente, firma_tipo, adulto_nombre, adulto_apellido,
                         adulto_tipo_documento, adulto_dni, now):
    """Crea un consentimiento YA firmado (un paso). Inmutable luego."""
    from patients.models import Consentimiento
    return Consentimiento.objects.create(
        paciente=paciente,
        firma_tipo=firma_tipo,
        adulto_nombre=adulto_nombre,
        adulto_apellido=adulto_apellido,
        adulto_tipo_documento=adulto_tipo_documento,
        adulto_dni=adulto_dni,
        fecha_firma=now,
        firma_hash=_firma_hash(
            firma_tipo=firma_tipo, nombre=adulto_nombre, apellido=adulto_apellido,
            tipo_doc=adulto_tipo_documento, dni=adulto_dni, timestamp=now,
        ),
    )
```

- [ ] **Step 4: Correr → verde**

Run: `./venv/bin/python manage.py test patients.tests.test_consentimiento --settings=config.settings.base`
Expected: OK (2 tests).

- [ ] **Step 5: Commit**

```bash
git add patients/services.py patients/tests/
git rm patients/tests.py 2>/dev/null; true
git commit -m "feat(patients): servicio crear_consentimiento (un paso + firma_hash)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Serializer, vistas, urls (uuid) y POST — TDD

**Files:**
- Modify: `patients/serializers.py`, `patients/views.py`, `patients/urls.py`
- Create: `patients/tests/test_urls.py`
- Modify: `patients/tests/test_consentimiento.py` (agrega tests de endpoint POST)

- [ ] **Step 1: Agregar el serializer a `patients/serializers.py`**

```python
from .models import Consentimiento  # sumar al import de .models


class ConsentimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consentimiento
        fields = ['id', 'paciente', 'firma_tipo', 'adulto_nombre', 'adulto_apellido',
                  'adulto_tipo_documento', 'adulto_dni', 'firma_hash', 'fecha_firma']
        extra_kwargs = {'adulto_dni': {'write_only': True}}   # se acepta, no se devuelve
        read_only_fields = ['firma_hash', 'fecha_firma']
```

- [ ] **Step 2: Agregar las vistas a `patients/views.py`**

```python
from django.utils import timezone
from authentication.permissions import require_action
from patients.models import Consentimiento
from patients.serializers import ConsentimientoSerializer
from patients import services


class ConsentimientoListCreateView(APIView):
    def get_permissions(self):
        action = 'darConsentimiento' if self.request.method == 'POST' else 'verConsentimiento'
        return [require_action(action)()]

    def get(self, request):
        return Response(ConsentimientoSerializer(Consentimiento.objects.all(), many=True).data)

    def post(self, request):
        s = ConsentimientoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        c = services.crear_consentimiento(
            paciente=v['paciente'], firma_tipo=v['firma_tipo'],
            adulto_nombre=v['adulto_nombre'], adulto_apellido=v['adulto_apellido'],
            adulto_tipo_documento=v['adulto_tipo_documento'], adulto_dni=v['adulto_dni'],
            now=timezone.now(),
        )
        return Response(ConsentimientoSerializer(c).data, status=status.HTTP_201_CREATED)


class ConsentimientoDetailView(APIView):
    permission_classes = [require_action('verConsentimiento')]

    def get(self, request, pk):
        return Response(ConsentimientoSerializer(get_object_or_404(Consentimiento, pk=pk)).data)
```
> Verificá que `status`, `Response`, `APIView`, `get_object_or_404` ya estén importados en el archivo (lo están por las vistas de pacientes). Si falta `status`, agregá `from rest_framework import status`.

- [ ] **Step 3: Agregar las rutas a `patients/urls.py`** (con `<uuid:pk>` — Consentimiento.id es UUID)

```python
from patients.views import ConsentimientoListCreateView, ConsentimientoDetailView  # sumar al import

# dentro de urlpatterns, agregar:
    path('consentimientos/', ConsentimientoListCreateView.as_view(), name='consentimiento-list-create'),
    path('consentimientos/<uuid:pk>/', ConsentimientoDetailView.as_view(), name='consentimiento-detail'),
```
> ⚠️ Poné estas rutas ANTES de cualquier patrón `<int:pk>/` del listado de pacientes si lo hubiera, para que `consentimientos/` matchee como literal. (Como `consentimientos` no es int, igual no colisiona, pero el orden explícito es más claro.)

- [ ] **Step 4: Escribir `patients/tests/test_urls.py`** (regresión del converter, como en el apto)

```python
import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from patients.views import ConsentimientoDetailView


class ConsentimientoUrlsTests(SimpleTestCase):
    def test_detail_resuelve_con_uuid(self):
        u = str(uuid.uuid4())
        self.assertEqual(
            resolve(f"/api/v1/consentimientos/{u}/").func.view_class, ConsentimientoDetailView
        )
```

- [ ] **Step 5: Agregar tests de endpoint POST a `patients/tests/test_consentimiento.py`** (nueva clase, reusa el patrón setUp/tearDown)

```python
from rest_framework.test import APIRequestFactory, force_authenticate
from patients.views import ConsentimientoListCreateView


@override_settings(SEEDS_ENABLED=True)
class ConsentimientoEndpointTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()
        self.tutor = Usuarios.objects.get(email="tutor@prosane.test")
        self.medico = Usuarios.objects.get(email="medico@prosane.test")
        self._nna = Personas.objects.create(nombre="Niño", apellido="Prueba", dni="66000002",
                                            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01")
        self._dom = Domicilio.objects.create(calle="Falsa", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=self._nna, domicilio=self._dom, edad=11)

    def tearDown(self):
        Consentimiento.all_objects.filter(paciente=self.paciente).hard_delete()
        Pacientes.objects.filter(id=self.paciente.id).delete()
        Personas.objects.filter(id=self._nna.id).delete()
        Domicilio.objects.filter(id=self._dom.id).delete()
        super().tearDown()

    def _post(self, user):
        body = {"paciente": self.paciente.id, "firma_tipo": "adulto_responsable",
                "adulto_nombre": "Marta", "adulto_apellido": "Tutora",
                "adulto_tipo_documento": "DNI", "adulto_dni": "22333444"}
        req = self.factory.post("/api/v1/consentimientos/", body, format="json")
        force_authenticate(req, user=user)
        return ConsentimientoListCreateView.as_view()(req)

    def test_tutor_crea_201_sin_exponer_dni(self):
        resp = self._post(self.tutor)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["firma_tipo"], "adulto_responsable")
        self.assertNotIn("adulto_dni", resp.data)

    def test_medico_sin_darConsentimiento_403(self):
        self.assertEqual(self._post(self.medico).status_code, 403)
```

- [ ] **Step 6: Correr → verde**

Run: `./venv/bin/python manage.py test patients.tests --settings=config.settings.base`
Expected: OK (test_consentimiento: 2 servicio + 2 endpoint; test_urls: 1).

- [ ] **Step 7: Commit**

```bash
git add patients/serializers.py patients/views.py patients/urls.py patients/tests/
git commit -m "feat(patients): endpoints de consentimiento (POST darConsentimiento, GET verConsentimiento)

Rutas con <uuid:pk> (Consentimiento.id es UUID), adulto_dni write_only, test de routing.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Acción `verConsentimiento` + GET tests + espejo en ROLE_ACTIONS

Agregar `verConsentimiento` a los fixtures rompe el test de equivalencia Fase1≡Fase2 y los conteos hardcodeados, igual que pasó con `verApto`. Por eso esta task **también** espeja en `actions_map.py` y actualiza los conteos.

**Files:**
- Modify: `authentication/fixtures/actions.json`, `authentication/fixtures/role_actions.json`
- Modify: `authentication/actions_map.py`
- Modify: tests de conteo (ver Step 4)
- Modify: `patients/tests/test_consentimiento.py` (GET tests)

- [ ] **Step 1: Agregar la acción a `authentication/fixtures/actions.json`** (último elemento del array, cuidando comas)

```json
  { "model": "authentication.action", "pk": "a0000000-0000-0000-0000-000000000010",
    "fields": { "name": "verConsentimiento", "label": "Ver consentimiento", "icon": "fact_check", "color": "#455A64", "type": "list", "category": "consentimiento", "is_sensitive": true, "sort_order": 25, "is_active": true, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } }
```

- [ ] **Step 2: Vincular a medico (2), odontologo (3) y tutor (4) en `role_actions.json`** (3 filas al final)

```json
  { "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000015", "fields": { "role": 2, "action": "a0000000-0000-0000-0000-000000000010", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } },
  { "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000016", "fields": { "role": 3, "action": "a0000000-0000-0000-0000-000000000010", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } },
  { "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000017", "fields": { "role": 4, "action": "a0000000-0000-0000-0000-000000000010", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } }
```

- [ ] **Step 3: Espejar en `authentication/actions_map.py`**

Definir la acción compartida (cerca de `_VER_APTO`):
```python
_VER_CONSENTIMIENTO = _a(
    "verConsentimiento", "Ver consentimiento",
    icon="fact_check", color="#455A64", type="list", category="consentimiento",
    is_sensitive=True, sort_order=25,
)
```
Y sumarla a `ROLE_ACTIONS`: en `"medico"`, `"odontologo"` y `"tutor"` agregá `_VER_CONSENTIMIENTO` a la lista.

- [ ] **Step 4: Actualizar los conteos hardcodeados en los tests**

Recargá y corré la suite para ver qué rompe:
`./venv/bin/python manage.py reset_permissions_data && ./venv/bin/python manage.py test authentication --settings=config.settings.base`

Valores nuevos esperados (catálogo **10**, role_actions **17**):
- `authentication/tests/test_seed_source.py` → `test_catalogo_tiene_9`: `9` → `10` (renombrá a `_10` si querés).
- `authentication/tests/test_seed_commands.py`:
  - catálogo `9` → `10`, role_actions `14` → `17` (en `test_carga_catalogo_completo` y `test_idempotente`).
  - `test_medico_da_sus_5_acciones`: el set suma `"verConsentimiento"` (médico ahora 6).
  - `test_tutor_da_sus_2_acciones`: el set suma `"verConsentimiento"` → `{"verConstancias", "darConsentimiento", "verConsentimiento"}` (tutor ahora 3).
- `authentication/tests/test_permissions.py`:
  - `test_medico_5_acciones_ordenadas`: lista ordenada por (sort_order, name) =
    `["listarPacientes", "verFichaClinica", "verConsentimiento", "crearApto", "firmarApto", "verApto"]`.
  - `test_tutor_2_acciones`: set suma `"verConsentimiento"`.
  - `test_superadmin_catalogo_completo`: `9` → `10`.
- `authentication/tests/test_me_endpoint.py`:
  - lista de acciones del médico = la ordenada de arriba (con `verConsentimiento` en posición 3).
  - `test_superadmin_ve_catalogo_completo`: `9` → `10`.
- `authentication/tests/test_me_payload.py`:
  - `test_superuser_recibe_catalogo_completo` y `test_superuser_ordenado_y_8_claves`: `9` → `10`.

Ajustá los nombres de los tests/labels que mencionen "5"/"9"/"2" si querés, pero al menos los valores.

- [ ] **Step 5: Verificar que medico/tutor tienen verConsentimiento**

Run:
```bash
./venv/bin/python manage.py shell -c "
from authentication.models import Usuarios
from authentication.action_resolution import effective_actions
for e in ['medico@prosane.test','tutor@prosane.test']:
    u = Usuarios.objects.get(email=e)
    print(e, 'verConsentimiento' in {a['name'] for a in effective_actions(u)})"
```
Expected: ambos `True`.

- [ ] **Step 6: Agregar GET tests a `patients/tests/test_consentimiento.py`** (dentro de `ConsentimientoEndpointTests`)

```python
    def test_medico_lista_con_verConsentimiento_200(self):
        from patients.views import ConsentimientoListCreateView
        req = self.factory.get("/api/v1/consentimientos/")
        force_authenticate(req, user=self.medico)
        self.assertEqual(ConsentimientoListCreateView.as_view()(req).status_code, 200)

    def test_ayudante_sin_verConsentimiento_403(self):
        from patients.views import ConsentimientoListCreateView
        ayudante = Usuarios.objects.get(email="ayudante@prosane.test")
        req = self.factory.get("/api/v1/consentimientos/")
        force_authenticate(req, user=ayudante)
        self.assertEqual(ConsentimientoListCreateView.as_view()(req).status_code, 403)
```

- [ ] **Step 7: Suite COMPLETA**

Run: `./venv/bin/python manage.py test authentication common core patients health --settings=config.settings.base`
Expected: OK (todo verde).

- [ ] **Step 8: Commit**

```bash
git add authentication/fixtures/ authentication/actions_map.py authentication/tests/ patients/tests/
git commit -m "feat(permisos): acción verConsentimiento (vía playbook + espejo ROLE_ACTIONS)

Cierra Slice B. Suma verConsentimiento a medico/odontologo/tutor; actualiza conteos
del catálogo (10 acciones, 17 role_actions).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notas de cierre

- **Diferido:** enganche al CIS (`cis_id`), revocación de consentimiento, y la regla
  cross-cutting "no se puede crear apto/control sin consentimiento previo" (cuando exista el CIS).
- `firma_hash` es integridad (SHA-256), no firma criptográfica con clave.
- Sin reconciliación nueva: `pacientes` ya quedó reconciliada en Slice A.
