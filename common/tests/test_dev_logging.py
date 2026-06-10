"""Tests de la redacción de datos sensibles para el logging de dev (Ley 25.326).

La redacción es lo crítico: el logging NUNCA debe imprimir DNI/diagnósticos/emails/
tokens/passwords en texto plano. Tests puros (sin DB).
"""
from django.test import SimpleTestCase

from common.dev_logging import redact


class RedactTests(SimpleTestCase):
    def test_redacta_password(self):
        self.assertEqual(redact({"password": "secreta123"}), {"password": "***"})

    def test_redacta_email(self):
        self.assertEqual(redact({"email": "nene@x.com"}), {"email": "***"})

    def test_redacta_tokens(self):
        out = redact({"access": "ey...", "refresh": "ey...", "token": "ey..."})
        self.assertEqual(out, {"access": "***", "refresh": "***", "token": "***"})

    def test_redacta_dni_y_diagnostico(self):
        out = redact({"dni": "44555666", "diagnostico": "asma"})
        self.assertEqual(out, {"dni": "***", "diagnostico": "***"})

    def test_no_redacta_campos_no_sensibles(self):
        out = redact({"name": "firmarApto", "sort_order": 10, "is_active": True})
        self.assertEqual(out, {"name": "firmarApto", "sort_order": 10, "is_active": True})

    def test_redacta_anidado_en_dicts(self):
        data = {"user": {"email": "a@b.com", "nombre": "Ana"}}
        self.assertEqual(redact(data), {"user": {"email": "***", "nombre": "Ana"}})

    def test_redacta_dentro_de_listas(self):
        data = {"items": [{"password": "x"}, {"name": "ok"}]}
        self.assertEqual(redact(data), {"items": [{"password": "***"}, {"name": "ok"}]})

    def test_match_case_insensitive_y_substring(self):
        # PASSWORD_HASH, JWT_Token, userEmail → todos sensibles
        out = redact({"PASSWORD_HASH": "h", "JWT_Token": "t", "userEmail": "e"})
        self.assertEqual(out, {"PASSWORD_HASH": "***", "JWT_Token": "***", "userEmail": "***"})

    def test_no_muta_el_original(self):
        data = {"password": "x", "nombre": "Ana"}
        redact(data)
        self.assertEqual(data, {"password": "x", "nombre": "Ana"})
