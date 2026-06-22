# Primera parte — Backend (dev-base) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `prosane_api` @ `dev-base` exponga el contrato de auth/`/me` que el app ya consume y un endpoint agregado que cree un hijo (NNA) con antecedentes y consentimiento en una sola transacción.

**Architecture:** Trabajamos sobre la rama `dev-base` (apps/ limpio, `managed=True`). B0 alinea el contrato congelado del app. B1' agrega campos de consentimiento al `Paciente`. B2 crea 2 acciones del tutor (solo menú). B3' extiende el endpoint `hijos` existente para crear antecedentes + consentimiento atómicamente.

**Tech Stack:** Django + DRF + djangorestframework-simplejwt. Tests con `APITestCase` (Django test runner), patrón existente en `apps/tutores/tests.py`.

**Spec:** `prosane_app/docs/superpowers/specs/2026-06-20-primera-parte-registro-familiar-design.md`

**Prerrequisitos de entorno:** estar en `dev-base`, tener `.env` configurado y la DB de test disponible. Comando base de tests: `python manage.py test <ruta> -v 2`.

---

### Task 0: Rama de trabajo

**Files:** ninguno (git)

- [ ] **Step 1: Crear la rama de feature desde dev-base**

```bash
cd prosane_api
git checkout dev-base
git checkout -b feat/primera-parte-registro-familiar
```

---

### Task 1: B0a — Alias de paths `token/` y `token/refresh/`

El app pega a `/api/v1/auth/token/` y `/api/v1/auth/token/refresh/` (hoy `dev-base` solo tiene `auth/login/` y `auth/refresh/`). Agregamos alias apuntando a las views que ya existen.

**Files:**
- Modify: `apps/usuarios/urls.py`
- Test: `apps/usuarios/tests.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `apps/usuarios/tests.py`:

```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.usuarios.models import Usuario


class AuthTokenAliasTest(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(email="t@example.com", password="test1234")

    def test_token_alias_devuelve_access_y_refresh(self):
        res = self.client.post(
            reverse("auth-token"),
            {"email": "t@example.com", "password": "test1234"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_token_refresh_alias_devuelve_access(self):
        login = self.client.post(
            reverse("auth-token"),
            {"email": "t@example.com", "password": "test1234"},
            format="json",
        )
        res = self.client.post(
            reverse("auth-token-refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test apps.usuarios.tests.AuthTokenAliasTest -v 2`
Expected: FAIL con `NoReverseMatch: Reverse for 'auth-token' not found`.

- [ ] **Step 3: Agregar los alias en urls.py**

`apps/usuarios/urls.py` — agregar dos paths a `urlpatterns`:

```python
from django.urls import path

from apps.usuarios import views


urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/token/', views.LoginView.as_view(), name='auth-token'),
    path('auth/refresh/', views.RefreshView.as_view(), name='auth-refresh'),
    path('auth/token/refresh/', views.RefreshView.as_view(), name='auth-token-refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
]
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python manage.py test apps.usuarios.tests.AuthTokenAliasTest -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/usuarios/urls.py apps/usuarios/tests.py
git commit -m "feat(auth): alias token/ y token/refresh/ para el contrato del app"
```

---

### Task 2: B0b — `/me` con el shape congelado del app

El app espera `{ user:{id,email,nombre,apellido,is_staff}, roles:[{name,label}], actions:[{8 claves}], meta:{version, permissions_synced_at} }`. Hoy `MeView` devuelve un dict plano con `roles:[{id,rol}]` y sin `user` ni `meta`. `effective_actions` ya emite las 8 claves correctas (no se toca).

**Files:**
- Modify: `apps/usuarios/views.py` (`MeView`)
- Test: `apps/usuarios/tests.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `apps/usuarios/tests.py`:

```python
from apps.personas.models import Persona
from apps.usuarios.models import Rol


class MeContractTest(APITestCase):
    def setUp(self):
        persona = Persona.objects.create(
            nombre="Ana", apellido="García", dni="22222222",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="1990-01-01",
        )
        self.user = Usuario.objects.create_user(
            email="ana@example.com", password="test1234", persona=persona,
        )
        rol, _ = Rol.objects.get_or_create(rol="tutor")
        self.user.roles.add(rol)
        self.client.force_authenticate(self.user)

    def test_me_devuelve_shape_congelado(self):
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["user"]["nombre"], "Ana")
        self.assertEqual(res.data["user"]["apellido"], "García")
        self.assertEqual(res.data["user"]["email"], "ana@example.com")
        self.assertIn("is_staff", res.data["user"])

        self.assertEqual(res.data["roles"][0]["name"], "tutor")
        self.assertIn("label", res.data["roles"][0])

        self.assertIsInstance(res.data["actions"], list)

        self.assertIn("version", res.data["meta"])
        self.assertIn("permissions_synced_at", res.data["meta"])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test apps.usuarios.tests.MeContractTest -v 2`
Expected: FAIL con `KeyError: 'user'`.

- [ ] **Step 3: Reescribir `MeView`**

`apps/usuarios/views.py` — reemplazar la clase `MeView` por:

```python
from django.utils import timezone


class MeView(APIView):
    """GET /auth/me/ — contrato congelado: user + roles + actions + meta."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        persona = getattr(user, "persona", None)
        roles = [
            {"name": r.rol, "label": r.rol.capitalize()}
            for r in user.roles.all()
        ]
        data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "nombre": getattr(persona, "nombre", "") or "",
                "apellido": getattr(persona, "apellido", "") or "",
                "is_staff": user.is_staff,
            },
            "roles": roles,
            "actions": effective_actions(user),
            "meta": {
                "version": "1",
                "permissions_synced_at": timezone.now().isoformat(),
            },
        }
        return Response(data)
```

(Quitar el `import` de `UserSerializer` si queda sin uso en el archivo.)

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python manage.py test apps.usuarios.tests.MeContractTest -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/usuarios/views.py apps/usuarios/tests.py
git commit -m "feat(auth): /me con shape congelado (user anidado, roles[name,label], meta)"
```

---

### Task 3: B1' — Campos de consentimiento en `Paciente`

**Files:**
- Modify: `apps/pacientes/models/paciente.py`
- Create: `apps/pacientes/migrations/00XX_paciente_consentimiento.py` (generada)
- Test: `apps/pacientes/tests.py`

- [ ] **Step 1: Escribir el test que falla**

Crear/agregar en `apps/pacientes/tests.py`:

```python
from django.test import TestCase
from django.utils import timezone

from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor
from apps.usuarios.models import Usuario


class PacienteConsentimientoTest(TestCase):
    def test_paciente_persiste_consentimiento(self):
        usuario = Usuario.objects.create_user(email="tu@example.com", password="test1234")
        tutor_persona = Persona.objects.create(
            nombre="Marta", apellido="Tutora", dni="30000000",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="1980-01-01",
        )
        tutor = Tutor.objects.create(persona=tutor_persona, usuario=usuario, parentesco="madre")
        nna = Persona.objects.create(
            nombre="Niño", apellido="Tutora", dni="55555555",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="2016-05-01",
        )
        dom = Domicilio.objects.create(calle="Falsa", nro_calle="123")

        p = Paciente.objects.create(
            persona=nna, domicilio=dom, tutor=tutor, edad=9,
            consentimiento_aceptado=True,
            fecha_consentimiento=timezone.now(),
            adulto_nombre="Marta", adulto_apellido="Tutora",
            adulto_tipo_documento="DNI", adulto_dni="30000000",
        )
        p.refresh_from_db()
        self.assertTrue(p.consentimiento_aceptado)
        self.assertIsNotNone(p.fecha_consentimiento)
        self.assertEqual(p.adulto_dni, "30000000")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test apps.pacientes.tests.PacienteConsentimientoTest -v 2`
Expected: FAIL con `TypeError: 'consentimiento_aceptado' is an invalid keyword argument`.

- [ ] **Step 3: Agregar los campos al modelo**

`apps/pacientes/models/paciente.py` — agregar dentro de `class Paciente`, antes de `class Meta`:

```python
    consentimiento_aceptado = models.BooleanField(default=False)
    fecha_consentimiento = models.DateTimeField(null=True, blank=True)
    adulto_nombre = models.CharField(max_length=200, blank=True, null=True)
    adulto_apellido = models.CharField(max_length=200, blank=True, null=True)
    adulto_tipo_documento = models.CharField(max_length=20, blank=True, null=True)
    adulto_dni = models.CharField(max_length=15, blank=True, null=True)
```

- [ ] **Step 4: Generar y aplicar la migración**

Run:
```bash
python manage.py makemigrations pacientes
python manage.py migrate
```
Expected: crea `apps/pacientes/migrations/00XX_paciente_consentimiento.py` y aplica OK.

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `python manage.py test apps.pacientes.tests.PacienteConsentimientoTest -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/pacientes/models/paciente.py apps/pacientes/migrations/ apps/pacientes/tests.py
git commit -m "feat(pacientes): campos de consentimiento minimo en Paciente + migracion"
```

---

### Task 4: B2 — Acciones `registrarHijo` + `verHijos` (menú del tutor)

Solo menú: se cargan vía fixture + seed y se asignan al rol `tutor`. No gatean endpoints.

**Files:**
- Modify: `apps/usuarios/fixtures/actions.json`
- Modify: `apps/usuarios/management/commands/seed_permissions.py` (dict `ROLE_ACTIONS`)
- Test: `apps/usuarios/tests.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `apps/usuarios/tests.py`:

```python
from django.core.management import call_command


class TutorAccionesFamiliaTest(APITestCase):
    def setUp(self):
        call_command("seed_permissions")
        self.user = Usuario.objects.create_user(email="tutor2@example.com", password="test1234")
        self.user.roles.add(Rol.objects.get(rol="tutor"))
        self.client.force_authenticate(self.user)

    def test_tutor_ve_acciones_de_familia(self):
        res = self.client.get(reverse("auth-me"))
        names = {a["name"] for a in res.data["actions"]}
        self.assertIn("registrarHijo", names)
        self.assertIn("verHijos", names)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test apps.usuarios.tests.TutorAccionesFamiliaTest -v 2`
Expected: FAIL (`registrarHijo` no está en el set).

- [ ] **Step 3: Agregar las 2 acciones al fixture**

`apps/usuarios/fixtures/actions.json` — agregar estos dos objetos al array (antes del `]` final, con coma en el objeto anterior):

```json
  {
    "model": "usuarios.action",
    "fields": {
      "name": "registrarHijo",
      "label": "Registrar hijo",
      "icon": "person_add",
      "color": "#6A4C93",
      "type": "crud",
      "category": "familia",
      "is_sensitive": true,
      "sort_order": 50,
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  },
  {
    "model": "usuarios.action",
    "fields": {
      "name": "verHijos",
      "label": "Mis hijos",
      "icon": "family_restroom",
      "color": "#6A4C93",
      "type": "crud",
      "category": "familia",
      "is_sensitive": false,
      "sort_order": 51,
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  }
```

- [ ] **Step 4: Asignar las acciones al rol tutor en el seed**

`apps/usuarios/management/commands/seed_permissions.py` — en el dict `ROLE_ACTIONS`, reemplazar la línea del tutor por:

```python
    "tutor": ["verEscuelas", "registrarHijo", "verHijos"],
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `python manage.py test apps.usuarios.tests.TutorAccionesFamiliaTest -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/usuarios/fixtures/actions.json apps/usuarios/management/commands/seed_permissions.py apps/usuarios/tests.py
git commit -m "feat(permisos): acciones registrarHijo y verHijos para el rol tutor"
```

---

### Task 5: B3' — Endpoint agregado (extender `hijos`)

Extender el serializer y el service para crear, en la transacción existente: Persona + Domicilio + Paciente (con consentimiento) + `AntecedentePersonal` + `AntecedenteFamiliar`, y actualizar `Tutor.parentesco`.

**Files:**
- Modify: `apps/tutores/serializers.py`
- Modify: `apps/tutores/services/hijos.py`
- Test: `apps/tutores/tests.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `apps/tutores/tests.py`:

```python
from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal


class CrearHijoAgregadoTest(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email="papa@example.com", password="test1234")
        persona = Persona.objects.create(
            nombre="Pedro", apellido="Papá", dni="40000000",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1982-02-02",
        )
        self.tutor = Tutor.objects.create(persona=persona, usuario=self.usuario, parentesco="")
        self.client.force_authenticate(self.usuario)

    def _body(self, dni="60000000"):
        return {
            "persona": {
                "nombre": "Hija", "apellido": "Papá", "dni": dni,
                "tipo_dni": "DNI", "sexo": "F", "fecha_nacimiento": "2015-06-01",
            },
            "domicilio": {"calle": "Siempreviva", "nro_calle": "742", "provincia": "Salta"},
            "edad": 10, "tiene_cud": "NO",
            "tipo_cobertura": "obra_social", "nombre_cobertura": "OSDE",
            "parentesco": "padre",
            "antecedentes_personales": {"asma_espasmos": "SI", "diabetes": "NO"},
            "antecedentes_familiares": {
                "problemas_salud": "SI",
                "detalle_problema_salud": "Hipertensión materna",
                "familiar_con_muerte_subita": "NO",
            },
            "consentimiento": {
                "adulto_nombre": "Pedro", "adulto_apellido": "Papá",
                "adulto_tipo_documento": "DNI", "adulto_dni": "40000000",
            },
        }

    def test_crea_hijo_con_antecedentes_y_consentimiento(self):
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        paciente_id = res.data["id"]

        self.assertEqual(AntecedentePersonal.objects.filter(paciente_id=paciente_id).count(), 1)
        self.assertEqual(AntecedenteFamiliar.objects.filter(paciente_id=paciente_id).count(), 1)
        self.assertTrue(Paciente.objects.get(id=paciente_id).consentimiento_aceptado)
        self.assertEqual(Paciente.objects.get(id=paciente_id).adulto_dni, "40000000")
        # adulto_dni NO se expone
        self.assertNotIn("adulto_dni", res.data)
        # parentesco se grabó en el Tutor
        self.tutor.refresh_from_db()
        self.assertEqual(self.tutor.parentesco, "padre")

    def test_otro_tutor_no_puede_cargar_403(self):
        otro = Usuario.objects.create_user(email="otro@example.com", password="test1234")
        self.client.force_authenticate(otro)
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(dni="61000000"), format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dni_duplicado_no_crea_nada(self):
        Persona.objects.create(
            nombre="X", apellido="X", dni="62000000",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="2010-01-01",
        )
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(dni="62000000"), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AntecedentePersonal.objects.count(), 0)
        self.assertEqual(Paciente.objects.count(), 0)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python manage.py test apps.tutores.tests.CrearHijoAgregadoTest -v 2`
Expected: FAIL (no se crean antecedentes / `adulto_dni` aparece en la respuesta).

- [ ] **Step 3: Extender los serializers**

`apps/tutores/serializers.py` — agregar imports arriba:

```python
from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal
```

Agregar estos serializers de entrada (antes de `HijoCreateSerializer`):

```python
_AUDIT_FIELDS = [
    "id", "paciente", "created_at", "created_year", "created_year_month",
    "updated_at", "updated_year", "updated_year_month",
    "created_by", "updated_by", "deleted_at",
]


class AntecedentePersonalInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentePersonal
        exclude = _AUDIT_FIELDS


class AntecedenteFamiliarInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedenteFamiliar
        exclude = _AUDIT_FIELDS


class ConsentimientoInputSerializer(serializers.Serializer):
    adulto_nombre = serializers.CharField()
    adulto_apellido = serializers.CharField()
    adulto_tipo_documento = serializers.CharField()
    adulto_dni = serializers.CharField()
```

En `HijoCreateSerializer`, agregar estos campos (después de `nombre_cobertura`):

```python
    parentesco = serializers.CharField(required=False, allow_blank=True)
    antecedentes_personales = AntecedentePersonalInputSerializer(required=False)
    antecedentes_familiares = AntecedenteFamiliarInputSerializer(required=False)
    consentimiento = ConsentimientoInputSerializer(required=False)
```

En `HijoOutputSerializer.Meta.fields`, agregar (sin `adulto_dni`):

```python
            "consentimiento_aceptado", "fecha_consentimiento",
            "adulto_nombre", "adulto_apellido", "adulto_tipo_documento",
```

- [ ] **Step 4: Extender el service `crear_hijo`**

`apps/tutores/services/hijos.py` — reemplazar imports y la función `crear_hijo`:

```python
from django.db import transaction
from django.utils import timezone

from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor


def crear_hijo(tutor_id, data):
    """Crea un hijo (Paciente) con antecedentes y consentimiento, atómicamente."""
    try:
        tutor = Tutor.objects.get(id=tutor_id)
    except Tutor.DoesNotExist:
        raise HijosError("Tutor no encontrado.", field="tutor")

    persona_data = data.get("persona", {})
    _validar_dni_unico(persona_data.get("dni"))

    consent = data.get("consentimiento") or {}
    ant_personales = data.get("antecedentes_personales") or {}
    ant_familiares = data.get("antecedentes_familiares") or {}
    parentesco = data.get("parentesco")

    with transaction.atomic():
        domicilio = Domicilio.objects.create(**data.get("domicilio", {}))
        persona = Persona.objects.create(**persona_data)
        paciente = Paciente.objects.create(
            persona=persona,
            domicilio=domicilio,
            tutor=tutor,
            edad=data.get("edad"),
            tiene_cud=data.get("tiene_cud"),
            tipo_cobertura=data.get("tipo_cobertura"),
            nombre_cobertura=data.get("nombre_cobertura"),
            consentimiento_aceptado=bool(consent),
            fecha_consentimiento=timezone.now() if consent else None,
            adulto_nombre=consent.get("adulto_nombre"),
            adulto_apellido=consent.get("adulto_apellido"),
            adulto_tipo_documento=consent.get("adulto_tipo_documento"),
            adulto_dni=consent.get("adulto_dni"),
        )
        AntecedentePersonal.objects.create(paciente=paciente, **ant_personales)
        AntecedenteFamiliar.objects.create(paciente=paciente, **ant_familiares)

        if parentesco:
            tutor.parentesco = parentesco
            tutor.save(update_fields=["parentesco", "updated_at"])

    return paciente
```

(Mantener intactas `HijosError`, `_validar_dni_unico` y `listar_hijos`.)

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `python manage.py test apps.tutores.tests.CrearHijoAgregadoTest -v 2`
Expected: PASS (3 tests).

- [ ] **Step 6: Correr toda la suite tocada**

Run: `python manage.py test apps.usuarios apps.pacientes apps.tutores -v 2`
Expected: PASS (incluye los tests de registro que ya existían).

- [ ] **Step 7: Commit**

```bash
git add apps/tutores/serializers.py apps/tutores/services/hijos.py apps/tutores/tests.py
git commit -m "feat(tutores): hijos agregado (antecedentes + consentimiento, atomico)"
```

---

### Task 6: B5 — Contrato de handoff `.md`

**Files:**
- Create: `prosane_app/docs/contrato-hijos-backend.md`

- [ ] **Step 1: Escribir el contrato**

Crear `prosane_app/docs/contrato-hijos-backend.md` con:

```markdown
# Contrato backend — Registro de hijo (planilla familiar)

> Handoff de `prosane_api` @ `dev-base` para el front. Endpoint agregado: crea el hijo
> (NNA) con antecedentes y consentimiento en una sola transacción.

## Auth
`Authorization: Bearer <access>`. Solo el tutor dueño (request.user == tutor.usuario), si no 403.

## POST /api/v1/tutores/<uuid:tutor_id>/hijos/
Body:
\`\`\`jsonc
{
  "persona":   { "nombre","apellido","dni","tipo_dni","sexo","fecha_nacimiento" },
  "domicilio": { "calle","nro_calle","piso","dpto","manzana","casa","nro_casa","pieza",
                 "provincia","departamento","localidad" },
  "edad": 10, "tiene_cud": "NO",
  "tipo_cobertura": "obra_social", "nombre_cobertura": "OSDE",
  "parentesco": "padre",
  "antecedentes_personales": { "asma_espasmos":"SI", "diabetes":"NO", ... },
  "antecedentes_familiares": { "problemas_salud","detalle_problema_salud","familiar_con_muerte_subita" },
  "consentimiento": { "adulto_nombre","adulto_apellido","adulto_tipo_documento","adulto_dni" }
}
→ 201  { id, persona, domicilio, tutor, edad, tiene_cud, tipo_cobertura, nombre_cobertura,
         consentimiento_aceptado, fecha_consentimiento, adulto_nombre, adulto_apellido,
         adulto_tipo_documento }   // adulto_dni NO se expone
→ 400  dni duplicado / body inválido   |   403 no es el dueño   |   401 sin auth
\`\`\`

## GET /api/v1/tutores/<uuid:tutor_id>/hijos/
Lista los hijos del tutor (mismo shape de salida, sin adulto_dni).

## Notas
- `consentimiento_aceptado` y `fecha_consentimiento` los setea el server al crear.
- `parentesco` se guarda en el Tutor (un parentesco por tutor en v1).
- Antecedentes Sí/No/No sabe viajan como strings.
```

- [ ] **Step 2: Commit**

```bash
git add prosane_app/docs/contrato-hijos-backend.md
git commit -m "docs: contrato de handoff del endpoint hijos (planilla familiar)"
```

---

## Self-review (cobertura del spec)

- **B0** → Task 1 (alias token) + Task 2 (/me shape). ✅
- **B1'** → Task 3 (campos de consentimiento + migración). ✅
- **B2** → Task 4 (acciones tutor solo menú). ✅
- **B3'** → Task 5 (endpoint agregado atómico + antecedentes + consentimiento). ✅
- **B4** → tests integrados en cada task (happy atómico, 403 dueño, dni duplicado/rollback). ✅
- **B5** → Task 6 (contrato `.md`). ✅

## Fuera de este plan (van al Plan 2 — Frontend)
F1–F6: apuntar a dev-base, signup tutor, cablear menú, wizard planilla, submit por cola de sync, nudge en Pendientes.
