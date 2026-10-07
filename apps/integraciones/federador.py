"""Cliente directo del Federador MSAL (RENAPER, camino B).

Autenticación propia contra el Federador (sin pasar por tableros):
  1. POST /usuarios/aplicacion/login {nombre, clave, codDominio} → {token}
  2. Consultas con headers `token: <jwt>` + `codDominio` (NO Bearer).
  3. Token cacheado ~25 min; ante 401 se re-loguea y reintenta una vez.

Endpoints:
  - GET /personas/renaper?nroDocumento=&idSexo= (1=M, 2=F; 204/404 = no hay)
  - GET /personas/cobertura?nroDocumento=&idSexo= (obra social PUCO/SISA)

Gotcha documentado: ante 204 se reintenta con idSexo opuesto (catálogo
invertido en algunos registros).

Sin dependencias externas: urllib stdlib (timeout 15 s).
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


TIMEOUT = 15
TOKEN_TTL = 25 * 60
DOMINIO_DEFAULT = "DOMINIOSINAUTORIZACIONDEALTA"


class FederadorError(Exception):
    """Error del servicio (caído, 502, respuesta inválida)."""


class FederadorNoEncontrado(Exception):
    """204/404: la persona no está en RENAPER."""


class FederadorNoConfigurado(Exception):
    """Faltan las credenciales del Federador en settings/.env."""


class FederadorAuthError(FederadorError):
    """Login rechazado o token inválido."""


_cache = {"token": None, "exp": 0.0}
_cache_lock = threading.Lock()


def _conf():
    base = (getattr(settings, "FEDERADOR_BASE_URL", "") or "").rstrip("/")
    return {
        "base": base or "https://federador.msal.gob.ar/masterfile-federacion-service/api",
        "dominio": getattr(settings, "FEDERADOR_DOMINIO", "") or DOMINIO_DEFAULT,
        "usuario": getattr(settings, "FEDERADOR_USUARIO", "") or "",
        "clave": getattr(settings, "FEDERADOR_CLAVE", "") or "",
    }


def _configurado():
    cfg = _conf()
    return bool(cfg["usuario"] and cfg["clave"])


def _http(method, url, headers=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            raw = (res.read() or b"").decode("utf-8").strip()
            return res.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raise _HttpStatus(e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FederadorError(f"Federador no disponible: {e}")


class _HttpStatus(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


def _login():
    cfg = _conf()
    if not _configurado():
        raise FederadorNoConfigurado(
            "Faltan FEDERADOR_USUARIO/FEDERADOR_CLAVE en la configuración."
        )
    try:
        _status, data = _http(
            "POST", cfg["base"] + "/usuarios/aplicacion/login",
            payload={"nombre": cfg["usuario"], "clave": cfg["clave"],
                     "codDominio": cfg["dominio"]},
        )
    except _HttpStatus as e:
        if e.status in (401, 403):
            raise FederadorAuthError("El Federador rechazó las credenciales.")
        raise FederadorError(f"Login Federador falló (HTTP {e.status}).")
    token = (data or {}).get("token")
    if not token:
        raise FederadorError("Login Federador sin token en la respuesta.")
    with _cache_lock:
        _cache["token"] = token
        _cache["exp"] = time.time() + TOKEN_TTL
    return token


def _token():
    with _cache_lock:
        if _cache["token"] and time.time() < _cache["exp"]:
            return _cache["token"]
    return _login()


def _headers():
    cfg = _conf()
    return {"token": _token(), "codDominio": cfg["dominio"]}


def _get(path, reintentar=True):
    cfg = _conf()
    if not _configurado():
        raise FederadorNoConfigurado(
            "Faltan FEDERADOR_USUARIO/FEDERADOR_CLAVE en la configuración."
        )
    try:
        _status, data = _http("GET", cfg["base"] + path, headers=_headers())
        return data
    except _HttpStatus as e:
        if e.status == 401 and reintentar:
            with _cache_lock:
                _cache["token"] = None
            _status, data = _http("GET", cfg["base"] + path, headers=_headers())
            return data
        if e.status == 401:
            raise FederadorAuthError("Token del Federador inválido.")
        if e.status in (204, 404):
            raise FederadorNoEncontrado("Persona no encontrada en RENAPER.")
        raise FederadorError(f"Federador respondió HTTP {e.status}.")


def _limpiar_cache():
    """Solo para tests: invalida el token cacheado."""
    with _cache_lock:
        _cache["token"] = None
        _cache["exp"] = 0.0


def _id_sexo(sexo):
    t = str(sexo or "").strip().lower()
    if t in ("1", "m", "masculino", "male"):
        return "1"
    if t in ("2", "f", "femenino", "female"):
        return "2"
    return ""


def _ids_sexo(sexo):
    """El pedido primero; ante 204 se reintenta con el opuesto (catálogo
    invertido en algunos registros)."""
    primero = _id_sexo(sexo)
    if not primero:
        return ["1", "2"]
    return [primero, "2" if primero == "1" else "1"]


def renaper_persona(nro_doc, sexo):
    """Datos filiatorios del Federador o None si no existe.

    Ante sexo desconocido prueba 1 y luego 2 (catálogo invertido).
    """
    nro = str(nro_doc or "").strip()
    if not nro:
        raise FederadorError("DNI vacío para consulta RENAPER.")
    for sid in _ids_sexo(sexo):
        qs = urllib.parse.urlencode({"nroDocumento": nro, "idSexo": sid})
        try:
            data = _get(f"/personas/renaper?{qs}")
        except FederadorNoEncontrado:
            continue
        # El Federador a veces responde 200 con objeto vacío en vez de 204.
        if data:
            return data
    return None


def renaper_cobertura(nro_doc, sexo):
    """Obra social (PUCO/SISA) o None si no hay."""
    nro = str(nro_doc or "").strip()
    if not nro:
        raise FederadorError("DNI vacío para consulta de cobertura.")
    for sid in _ids_sexo(sexo):
        qs = urllib.parse.urlencode({"nroDocumento": nro, "idSexo": sid})
        try:
            data = _get(f"/personas/cobertura?{qs}")
        except FederadorNoEncontrado:
            continue
        if data:
            return data
    return None
