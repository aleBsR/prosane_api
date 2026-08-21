from django.db import models
from django.utils import timezone

from common.models import BaseModel


class PasswordResetCode(BaseModel):
    """Código de un solo uso para restablecer la contraseña.

    Se envía por email al pedir "¿Olvidaste tu contraseña?". Vence a los
    `expires_at` y se invalida al usarlo (`used_at`).
    """
    email = models.EmailField(max_length=256, db_index=True)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "password_reset_code"

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()