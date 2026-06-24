"""Logging verboso y LEGIBLE de requests/responses para DESARROLLO.

Se activa SOLO desde config/settings/local.py (nunca base/production). Loguea
método, path, status, duración y los bodies JSON de request/response **con los
campos sensibles redactados** (Ley 25.326: nada de DNI/diagnósticos/emails/tokens
en texto plano). No loguea headers (así el Bearer token nunca aparece).

DX: colores ANSI (verbo + status según 2xx/4xx/5xx), JSON indentado y espaciado
entre requests. Los colores solo se emiten en una consola real (TTY) o si se fuerza
con PROSANE_LOG_COLOR=1; al redirigir a un archivo, salida limpia sin ANSI.
"""
import json
import logging
import os
import sys
import time

logger = logging.getLogger("prosane.api")

# Una clave es sensible si su nombre (lower) contiene alguno de estos substrings.
SENSITIVE_SUBSTRINGS = (
    "password", "passwd", "secret", "token", "authorization",
    "access", "refresh", "email", "mail", "dni", "documento",
    "diagnos", "cuil", "cuit",
)

REDACTED = "***"
_MAX_BODY = 4000  # no logueamos bodies enormes

# --- ANSI ---
_RESET, _BOLD, _DIM = "\033[0m", "\033[1m", "\033[2m"
_RED, _GREEN, _YELLOW, _BLUE, _MAGENTA, _CYAN = (
    "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[35m", "\033[36m",
)
_VERB_COLORS = {
    "GET": _CYAN, "POST": _GREEN, "PUT": _YELLOW, "PATCH": _YELLOW,
    "DELETE": _RED, "OPTIONS": _DIM, "HEAD": _DIM,
}


def _color_on():
    return sys.stderr.isatty() or os.environ.get("PROSANE_LOG_COLOR") == "1"


def _c(color, text):
    return f"{color}{text}{_RESET}" if _color_on() else str(text)


def _status_color(code):
    if 200 <= code < 300:
        return _GREEN
    if 300 <= code < 400:
        return _CYAN
    if 400 <= code < 500:
        return _YELLOW
    return _RED


def _is_sensitive(key):
    k = str(key).lower()
    return any(s in k for s in SENSITIVE_SUBSTRINGS)


def redact(value):
    """Copia con los valores de claves sensibles reemplazados por ***. No muta el original."""
    if isinstance(value, dict):
        return {k: (REDACTED if _is_sensitive(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def _json_or_none(raw):
    if not raw:
        return None
    try:
        if len(raw) > _MAX_BODY:
            return {"_truncated": f"{len(raw)} bytes"}
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _pretty_block(obj):
    """JSON indentado, redactado, con cada línea sangrada (en gris)."""
    text = json.dumps(redact(obj), indent=2, ensure_ascii=False)
    indented = "\n".join("    " + line for line in text.splitlines())
    return _c(_DIM, indented)


class RequestResponseLoggingMiddleware:
    """Middleware de dev: loguea request/response redactados y legibles. Nunca rompe el request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        req_body = _json_or_none(getattr(request, "body", b""))
        response = self.get_response(request)
        try:
            dur_ms = (time.monotonic() - start) * 1000
            verb = request.method
            out = [
                "",  # línea en blanco → espaciado entre requests
                f"{_c(_DIM, time.strftime('%H:%M:%S'))}  "
                f"{_c(_VERB_COLORS.get(verb, _MAGENTA), f'→ {verb}')} {request.get_full_path()}",
            ]
            if req_body is not None:
                out.append(_c(_DIM, "  req:"))
                out.append(_pretty_block(req_body))

            status = response.status_code
            out.append(
                f"          {_c(_status_color(status), f'← {status}')} {_c(_DIM, f'({dur_ms:.0f} ms)')}"
            )
            if response.get("Content-Type", "").startswith("application/json"):
                resp_body = _json_or_none(getattr(response, "content", b""))
                if resp_body is not None:
                    out.append(_c(_DIM, "  resp:"))
                    out.append(_pretty_block(resp_body))

            logger.debug("\n".join(out))
        except Exception:  # noqa: BLE001 — el logging jamás debe tirar el request
            logger.debug("(logging middleware: error al loguear, ignorado)")
        return response
