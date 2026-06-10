"""Logging verboso de requests/responses para DESARROLLO.

Se activa SOLO desde config/settings/local.py (nunca base/production). Loguea
método, path, status, duración y los bodies JSON de request/response **con los
campos sensibles redactados** (Ley 25.326: nada de DNI/diagnósticos/emails/tokens
en texto plano). No loguea headers (así el Bearer token nunca aparece).
"""
import json
import logging
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


def _is_sensitive(key):
    k = str(key).lower()
    return any(s in k for s in SENSITIVE_SUBSTRINGS)


def redact(value):
    """Devuelve una copia con los valores de claves sensibles reemplazados por ***.

    Recursivo sobre dicts y listas. No muta el original.
    """
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


class RequestResponseLoggingMiddleware:
    """Middleware de dev: loguea request/response redactados. Nunca rompe el request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        req_body = _json_or_none(getattr(request, "body", b""))
        response = self.get_response(request)
        try:
            dur_ms = (time.monotonic() - start) * 1000
            logger.debug("→ %s %s", request.method, request.get_full_path())
            if req_body is not None:
                logger.debug("  req: %s", json.dumps(redact(req_body), ensure_ascii=False))
            logger.debug("← %s (%.0f ms)", response.status_code, dur_ms)
            if response.get("Content-Type", "").startswith("application/json"):
                resp_body = _json_or_none(getattr(response, "content", b""))
                if resp_body is not None:
                    logger.debug("  resp: %s", json.dumps(redact(resp_body), ensure_ascii=False))
        except Exception:  # noqa: BLE001 — el logging jamás debe tirar el request
            logger.debug("(logging middleware: error al loguear, ignorado)")
        return response
