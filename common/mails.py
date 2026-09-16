"""Helper único para los mails de contraseña temporal (opción A).

Centraliza asunto/cuerpo y la URL de ingreso (settings.LOGIN_URL) para que los
envíos —alta escuela, alta ayudante, alta profesional y reenvíos— compartan el
mismo texto y estética (colores de la app: violeta #7C5CFC, Nunito/Rubik).

En dev el EMAIL_BACKEND es console (el mail se imprime en terminal); en
producción se configura SMTP vía .env sin tocar código.
"""
import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail

TEMP_EXPIRY_HOURS = 72

# Colores de la app (lib/core/theme/app_colors.dart)
_BRAND = "#7C5CFC"
_BRAND_DARK = "#6C4DE0"
_GRAD_START = "#9B7DF0"
_GRAD_END = "#7B5BE0"
_TEXT = "#2D2D3A"
_MUTED = "#9CA3AF"


def generar_temporal(usuario=None):
    """Genera una contraseña temporal aleatoria que pasa los validators."""
    for _ in range(5):
        cand = secrets.token_urlsafe(10)
        try:
            validate_password(cand, usuario)
            return cand
        except Exception:
            continue
    return secrets.token_urlsafe(12)


def _login_url():
    return getattr(
        settings, "LOGIN_URL", "https://prosane.salta.gob.ar/login"
    )


def _cuerpo_plano(email, temp, es_reenvio):
    linea_clave = (
        f"Nueva contraseña temporal: {temp}"
        if es_reenvio
        else f"Contraseña temporal: {temp}"
    )
    verbo = "Te reenviaron" if es_reenvio else "Te crearon"
    return (
        "PROSANE — Programa Nacional de Salud Escolar (Salta)\n\n"
        f"Hola,\n\n"
        f"{verbo} un acceso en PROSANE ({email}).\n"
        f"{linea_clave}\n"
        f"Vence en {TEMP_EXPIRY_HOURS} horas. "
        "Al ingresar por primera vez el sistema te pedirá cambiarla.\n\n"
        f"Ingresá en: {_login_url()}\n\n"
        "Si no esperabas este mail, ignoralo.\n"
    )


def _cuerpo_html(email, temp, es_reenvio):
    titulo = (
        "Te reenviaron tu acceso a PROSANE"
        if es_reenvio
        else "Te crearon un acceso en PROSANE"
    )
    linea_clave = "Nueva contraseña temporal" if es_reenvio else "Contraseña temporal"
    return f"""\
<html>
<body style="margin:0;padding:0;background-color:#F1F0F5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F1F0F5;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#ffffff;border-radius:16px;overflow:hidden;">
<tr><td style="background-color:{_BRAND};background:linear-gradient(135deg,{_GRAD_START},{_GRAD_END});padding:28px 32px;text-align:center;">
<div style="font-size:26px;font-weight:bold;color:#ffffff;letter-spacing:2px;">PROSANE</div>
<div style="font-size:13px;color:#EDE9FE;margin-top:6px;">Programa Nacional de Salud Escolar &bull; Salta</div>
</td></tr>
<tr><td style="padding:28px 32px;color:{_TEXT};">
<p style="font-size:16px;margin:0 0 8px;">Hola,</p>
<p style="font-size:14px;margin:0 0 16px;">{titulo} (<b>{email}</b>). Us&aacute; esta contrase&ntilde;a temporal para tu primer ingreso:</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 16px;">
<tr><td align="center" style="background-color:#F1F0F5;border:1px dashed {_BRAND};border-radius:12px;padding:16px;">
<div style="font-size:12px;color:{_MUTED};text-transform:uppercase;letter-spacing:1px;">{linea_clave}</div>
<div style="font-size:24px;font-weight:bold;color:{_BRAND_DARK};letter-spacing:2px;margin-top:6px;">{temp}</div>
<div style="font-size:12px;color:{_MUTED};margin-top:6px;">Vence en {TEMP_EXPIRY_HOURS} horas</div>
</td></tr>
</table>
<p style="font-size:14px;font-weight:bold;margin:0 0 8px;">C&oacute;mo ingresar:</p>
<ol style="font-size:14px;margin:0 0 16px;padding-left:20px;">
<li>Abr&iacute; la app PROSANE en la tablet e ingres&aacute; con tu email y la contrase&ntilde;a temporal.</li>
<li>La app te va a pedir que elijas tu contrase&ntilde;a definitiva.</li>
<li>Listo, ya pod&eacute;s trabajar en tu escuela u operativo.</li>
</ol>
<p style="font-size:13px;color:{_MUTED};margin:0;">Si no esperabas este mail, ignoralo. Ante cualquier duda consult&aacute; con tu referente PROSANE.</p>
</td></tr>
<tr><td style="background-color:#F1F0F5;padding:16px 32px;text-align:center;font-size:12px;color:{_MUTED};">
PROSANE &bull; Salud Escolar &bull; Provincia de Salta
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def enviar_temporal(email, temp, es_reenvio=False):
    """Envía la temporal por mail (texto + HTML). No loguea la clave."""
    subject = (
        "Acceso PROSANE — nueva contraseña temporal"
        if es_reenvio
        else "Acceso PROSANE — contraseña temporal"
    )
    try:
        send_mail(
            subject=subject,
            message=_cuerpo_plano(email, temp, es_reenvio),
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
            html_message=_cuerpo_html(email, temp, es_reenvio),
        )
    except Exception:
        pass


RESET_EXPIRY_MINUTES = 30


def _cuerpo_plano_reset(email, code):
    return (
        "PROSANE — Programa Nacional de Salud Escolar (Salta)\n\n"
        "Hola,\n\n"
        f"Pediste restablecer tu contraseña en PROSANE ({email}).\n"
        f"Tu código es: {code}\n"
        f"Vence en {RESET_EXPIRY_MINUTES} minutos. "
        "Abrí la app, elegí «¿Olvidaste tu contraseña?» e ingresá el código "
        "para elegir tu nueva clave (mínimo 8 caracteres, no solo números).\n\n"
        f"Ingresá en: {_login_url()}\n\n"
        "Si no lo pediste, ignorá este mensaje.\n"
    )


def _cuerpo_html_reset(email, code):
    return f"""\
<html>
<body style="margin:0;padding:0;background-color:#F1F0F5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F1F0F5;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#ffffff;border-radius:16px;overflow:hidden;">
<tr><td style="background-color:{_BRAND};background:linear-gradient(135deg,{_GRAD_START},{_GRAD_END});padding:28px 32px;text-align:center;">
<div style="font-size:26px;font-weight:bold;color:#ffffff;letter-spacing:2px;">PROSANE</div>
<div style="font-size:13px;color:#EDE9FE;margin-top:6px;">Programa Nacional de Salud Escolar &bull; Salta</div>
</td></tr>
<tr><td style="padding:28px 32px;color:{_TEXT};">
<p style="font-size:16px;margin:0 0 8px;">Hola,</p>
<p style="font-size:14px;margin:0 0 16px;">Pediste restablecer tu contrase&ntilde;a en PROSANE (<b>{email}</b>). Us&aacute; este c&oacute;digo para elegir tu nueva clave:</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 16px;">
<tr><td align="center" style="background-color:#F1F0F5;border:1px dashed {_BRAND};border-radius:12px;padding:16px;">
<div style="font-size:12px;color:{_MUTED};text-transform:uppercase;letter-spacing:1px;">C&oacute;digo de verificaci&oacute;n</div>
<div style="font-size:32px;font-weight:bold;color:{_BRAND_DARK};letter-spacing:6px;margin-top:6px;">{code}</div>
<div style="font-size:12px;color:{_MUTED};margin-top:6px;">Vence en {RESET_EXPIRY_MINUTES} minutos</div>
</td></tr>
</table>
<p style="font-size:14px;font-weight:bold;margin:0 0 8px;">C&oacute;mo restablecerla:</p>
<ol style="font-size:14px;margin:0 0 16px;padding-left:20px;">
<li>Abr&iacute; la app PROSANE y toc&aacute; <b>&iquest;Olvidaste tu contrase&ntilde;a?</b></li>
<li>Ingres&aacute; el c&oacute;digo de 6 d&iacute;gitos.</li>
<li>Eleg&iacute; tu nueva contrase&ntilde;a (m&iacute;nimo 8 caracteres, no solo n&uacute;meros, evit&aacute; claves comunes).</li>
</ol>
<p style="font-size:13px;color:{_MUTED};margin:0;">Si no pediste este c&oacute;digo, ignor&aacute; este mensaje. Ante cualquier duda consult&aacute; con tu referente PROSANE.</p>
</td></tr>
<tr><td style="background-color:#F1F0F5;padding:16px 32px;text-align:center;font-size:12px;color:{_MUTED};">
PROSANE &bull; Salud Escolar &bull; Provincia de Salta
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def enviar_codigo_reset(email, code):
    """Envía el código de reseteo con el mismo branding que la temporal (texto + HTML)."""
    try:
        send_mail(
            subject="PROSANE — código para restablecer tu contraseña",
            message=_cuerpo_plano_reset(email, code),
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
            html_message=_cuerpo_html_reset(email, code),
        )
    except Exception:
        pass
