"""Núcleo puro de permisos — Fase 1 (mapa rol→acciones en código).

⚠️ DETALLE DE IMPLEMENTACIÓN DE FASE 1, DESCARTABLE.
En Fase 2 este mapa se reemplaza por las tablas `actions` / `role_actions` /
`user_action_overrides` y la resolución computada, SIN cambiar el contrato `/me`
(ver docs/superpowers/specs/2026-06-09-permisos-data-driven-design.md).

Acá vive el contrato CONGELADO de cada acción: las 8 claves exactas y la
invariante de `name` en camelCase. Eso NO cambia entre fases.
"""
import hashlib

# Las 8 claves congeladas del contrato (§3 del spec). El orden importa para docs,
# pero el contrato sólo exige que estén las 8.
ACTION_FIELDS = (
    "name", "label", "icon", "color", "type",
    "category", "is_sensitive", "sort_order",
)


def _a(name, label, *, icon, color, type, category, is_sensitive, sort_order):
    """Arma una acción con las 8 claves del contrato (evita typos de claves)."""
    return {
        "name": name,
        "label": label,
        "icon": icon,
        "color": color,
        "type": type,
        "category": category,
        "is_sensitive": is_sensitive,
        "sort_order": sort_order,
    }


# --- Acciones compartidas (se reutilizan en varios roles → el dedup las unifica) ---
_LISTAR_PACIENTES = _a(
    "listarPacientes", "Listar pacientes",
    icon="people", color="#1565C0", type="list", category="salud",
    is_sensitive=False, sort_order=10,
)
_CREAR_APTO = _a(
    "crearApto", "Crear apto físico",
    icon="assignment_add", color="#2E7D32", type="form", category="salud",
    is_sensitive=True, sort_order=30,
)
_FIRMAR_APTO = _a(
    "firmarApto", "Firmar apto físico",
    icon="draw", color="#2E7D32", type="form", category="salud",
    is_sensitive=True, sort_order=40,
)

# --- Mapa rol → acciones (Fase 1; los nombres de rol salen de la tabla `roles`) ---
ROLE_ACTIONS = {
    "medico": [
        _LISTAR_PACIENTES,
        _a("verFichaClinica", "Ver ficha clínica",
           icon="clinical_notes", color="#6A1B9A", type="form", category="salud",
           is_sensitive=True, sort_order=20),
        _CREAR_APTO,
        _FIRMAR_APTO,
    ],
    "odontologo": [
        _LISTAR_PACIENTES,
        _a("verFichaOdontologica", "Ver ficha odontológica",
           icon="dentistry", color="#00838F", type="form", category="salud",
           is_sensitive=True, sort_order=25),
        _CREAR_APTO,
        _FIRMAR_APTO,
    ],
    "ayudante": [
        _LISTAR_PACIENTES,
        _a("registrarAntropometria", "Registrar antropometría",
           icon="straighten", color="#EF6C00", type="form", category="salud",
           is_sensitive=True, sort_order=15),
    ],
    "tutor": [
        _a("verConstancias", "Ver constancias",
           icon="description", color="#455A64", type="list", category="consentimiento",
           is_sensitive=False, sort_order=10),
        _a("darConsentimiento", "Dar consentimiento",
           icon="how_to_reg", color="#455A64", type="form", category="consentimiento",
           is_sensitive=True, sort_order=20),
    ],
}


# --- Labels de rol (Fase 1, en código; §11.4 del spec — additive en Fase 2) ---
ROLE_LABELS = {
    "medico": "Médico/a",
    "odontologo": "Odontólogo/a",
    "ayudante": "Ayudante",
    "tutor": "Tutor/a",
    "usuario": "Usuario",
}


def role_label(rol):
    """Label visible de un rol; si no está mapeado, devuelve el propio nombre."""
    return ROLE_LABELS.get(rol, rol)


def actions_for_roles(role_names):
    """Devuelve las acciones efectivas de un conjunto de roles.

    Deduplica por `name` (acciones compartidas aparecen una vez) y ordena por
    (sort_order, name) para un menú estable.
    """
    by_name = {}
    for rol in role_names:
        for accion in ROLE_ACTIONS.get(rol, ()):
            by_name[accion["name"]] = accion
    return sorted(by_name.values(), key=lambda a: (a["sort_order"], a["name"]))


def all_actions():
    """Lista de acciones únicas (por name) definidas en el mapa. Fuente del seed."""
    by_name = {}
    for acciones in ROLE_ACTIONS.values():
        for a in acciones:
            by_name[a["name"]] = a
    return list(by_name.values())


def role_action_pairs():
    """Pares (rol, name_de_accion) que el seed vuelca en role_actions."""
    pares = []
    seen = set()
    for rol, acciones in ROLE_ACTIONS.items():
        for a in acciones:
            par = (rol, a["name"])
            if par not in seen:
                seen.add(par)
                pares.append(par)
    return pares


def permissions_version(actions):
    """Hash corto y determinístico del conjunto de `name` (independiente del orden).

    Cambia si y sólo si cambia el conjunto de acciones del usuario. Sirve para que
    la app invalide su cache de permisos (offline-first).
    """
    names = sorted(a["name"] for a in actions)
    digest = hashlib.sha256("|".join(names).encode("utf-8")).hexdigest()
    return digest[:8]
