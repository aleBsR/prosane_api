"""Cliente directo del Bus Nacional MSAL (REFEPS, camino B).

Autenticación propia OAuth2 + jwt-bearer (RFC 7523, sin pasar por tableros):
  1. JWT HS256 (clientAssertion) firmado con el secret: iss=sub=dominio
     institucional, aud=<base>/bus-auth/v2/auth, iat, exp=+600s y los
     literales name/ident/role. SIN jti y SIN claims extra (el Bus los
     rechaza con 412).
  2. POST /bus-auth/v2/auth (form) con grantType=client_credentials,
     scope, clientAssertionType=urn:ietf:params:oauth:client-assertion-type:jwt-bearer
     y clientAssertion → {accessToken} (~60 min; se cachea 50).
  3. GET /fhir/Practitioner?identifier=<system>|<valor> con
     Authorization: Bearer + Accept: application/fhir+json.

Sistemas FHIR: dni https://www.renaper.org.ar/dni (+gender),
refeps https://sisa.msal.gov.ar/REFEPS, cuil https://www.anses.org.ar/cuil.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt
from django.conf import settings


TIMEOUT = 15
TOKEN_TTL = 50 * 60

SYSTEMS = {
    "dni": "https://www.renaper.org.ar/dni",
    "refeps": "https://sisa.msal.gov.ar/REFEPS",
    "cuil": "https://www.anses.org.ar/cuil",
}


class BusError(Exception):
    """Error del servicio (caído, respuesta inválida)."""


class BusNoEncontrado(Exception):
    """Bundle vacío: sin profesionales."""


class BusNoConfigurado(Exception):
    """Faltan las credenciales del Bus en settings/.env."""


class BusAuthError(BusError):
    """Credenciales/scope rechazados."""


_cache = {"token": None, "exp": 0.0}
_cache_lock = threading.Lock()


def _conf():
    base = (getattr(settings, "BUS_BASE_URL", "") or "").rstrip("/")
    return {
        "base": base or "https://bus.msal.gob.ar",
        "issuer": getattr(settings, "BUS_ISSUER", "") or "https://safesa.gob.ar",
        # Literales que espera el Bus (ver código histórico: van tal cual).
        "secret": getattr(settings, "BUS_SECRET", "") or "",
        "scope": getattr(settings, "BUS_SCOPE", "") or "Practitioner/*.read",
        "name": getattr(settings, "BUS_NAME", "") or "name",
        "ident": getattr(settings, "BUS_IDENT", "") or "ident",
        "role": getattr(settings, "BUS_ROLE", "") or "role",
    }


def _configurado():
    cfg = _conf()
    return bool(cfg["issuer"] and cfg["secret"])


def _http_post_json(url, payload, headers=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, json.loads((res.read() or b"{}").decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise _HttpStatus(e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise BusError(f"Bus MSAL no disponible: {e}")


def _http_get_json(url, headers=None):
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, json.loads((res.read() or b"{}").decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise _HttpStatus(e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise BusError(f"Bus MSAL no disponible: {e}")


class _HttpStatus(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


def _assertion():
    """JWT HS256 mínimo para client_credentials (sin jti ni claims extra)."""
    cfg = _conf()
    ahora = int(time.time())
    claims = {
        "iss": cfg["issuer"],
        "sub": cfg["issuer"],
        "aud": f"{cfg['base']}/bus-auth/v2/auth",
        "iat": ahora,
        "exp": ahora + 600,
        "name": cfg["name"],
        "ident": cfg["ident"],
        "role": cfg["role"],
    }
    return jwt.encode(claims, cfg["secret"], algorithm="HS256")


def _login():
    cfg = _conf()
    if not _configurado():
        raise BusNoConfigurado(
            "Faltan BUS_ISSUER/BUS_SECRET en la configuración."
        )
    try:
        _status, data = _http_post_json(
            f"{cfg['base']}/bus-auth/v2/auth",
            {
                "grantType": "client_credentials",
                "scope": cfg["scope"],
                "clientAssertionType": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "clientAssertion": _assertion(),
            },
        )
    except _HttpStatus as e:
        raise BusAuthError(f"Auth del Bus falló (HTTP {e.status}).")
    token = (data or {}).get("access_token") or (data or {}).get("accessToken")
    if not token:
        raise BusError("Auth del Bus sin accessToken en la respuesta.")
    with _cache_lock:
        _cache["token"] = token
        _cache["exp"] = time.time() + TOKEN_TTL
    return token


def _token():
    with _cache_lock:
        if _cache["token"] and time.time() < _cache["exp"]:
            return _cache["token"]
    return _login()


def _limpiar_cache():
    """Solo para tests: invalida el token cacheado."""
    with _cache_lock:
        _cache["token"] = None
        _cache["exp"] = 0.0


def _bundle(tipo, valor, genero=""):
    cfg = _conf()
    if not _configurado():
        raise BusNoConfigurado(
            "Faltan BUS_ISSUER/BUS_SECRET en la configuración."
        )
    valor = str(valor or "").strip()
    if not valor:
        raise BusError("Valor vacío para consulta REFEPS.")
    if tipo not in SYSTEMS:
        raise BusError(f"Tipo REFEPS inválido: {tipo}.")
    ident = f"{SYSTEMS[tipo]}|{valor}"
    qs = urllib.parse.urlencode({"identifier": ident})
    if tipo == "dni" and genero in ("male", "female"):
        qs += "&" + urllib.parse.urlencode({"gender": genero})
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/fhir+json",
    }
    try:
        _status, data = _http_get_json(f"{cfg['base']}/fhir/Practitioner?{qs}", headers)
    except _HttpStatus as e:
        if e.status == 401:
            with _cache_lock:
                _cache["token"] = None
            headers["Authorization"] = f"Bearer {_login()}"
            try:
                _status, data = _http_get_json(
                    f"{cfg['base']}/fhir/Practitioner?{qs}", headers)
            except _HttpStatus as e2:
                raise BusError(f"Bus respondió HTTP {e2.status}.")
        elif e.status == 404:
            raise BusNoEncontrado("Sin profesionales con ese identificador.")
        else:
            raise BusError(f"Bus respondió HTTP {e.status}.")
    return data or {}


def _parse_practitioner(p):
    ids = {}
    for ident in p.get("identifier") or []:
        if isinstance(ident, dict) and ident.get("value"):
            ids[ident.get("system")] = ident.get("value")
    names = p.get("name") or []
    n0 = names[0] if names else {}
    family = str(n0.get("family") or "").strip()
    given = n0.get("given") or []
    nombre = str(given[0]).strip() if given else ""
    quals = []
    for q in p.get("qualification") or []:
        if not isinstance(q, dict):
            continue
        code = q.get("code") or {}
        codings = code.get("coding") or []
        display = code.get("text") or (codings[0].get("display") if codings else "")
        numero = ""
        for ident in q.get("identifier") or []:
            if isinstance(ident, dict) and ident.get("value"):
                numero = str(ident.get("value"))
                break
        period = q.get("period") or {}
        quals.append({
            "tipo": str((codings[0].get("code") if codings else "") or ""),
            "display": str(display or ""),
            "numero": numero,
            "desde": str(period.get("start") or ""),
        })
    mat0 = quals[0] if quals else {}
    return {
        "fhir_id": str(p.get("id") or ""),
        "nombre": nombre,
        "apellido": family,
        "dni": str(ids.get(SYSTEMS["dni"]) or ""),
        "refeps": str(ids.get(SYSTEMS["refeps"]) or ""),
        "cuil": str(ids.get(SYSTEMS["cuil"]) or ""),
        "genero": str(p.get("gender") or ""),
        "activo": bool(p.get("active", True)),
        "matriculas": quals,
        "profesion": str(mat0.get("display") or ""),
        "matricula": str(mat0.get("numero") or ""),
    }


def refeps_profesional(tipo="refeps", valor="", genero=""):
    """Busca profesional en REFEPS. Dict simple o None si no hay."""
    try:
        data = _bundle(tipo, valor, genero)
    except BusNoEncontrado:
        return None
    practs = []
    for e in data.get("entry") or []:
        res = (e or {}).get("resource") or {}
        if res.get("resourceType", "Practitioner") == "Practitioner":
            practs.append(_parse_practitioner(res))
    if not practs:
        return None
    return practs[0]


def refeps_por_matricula(numero):
    """Atajo para validar matrícula (lo que usa Profesionales)."""
    return refeps_profesional(tipo="refeps", valor=numero)
