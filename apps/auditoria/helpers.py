"""Helpers de auditoría de cambios (centraliza _ip_cliente duplicado)."""
from apps.auditoria.models import AuditoriaCambio


def ip_cliente(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '') or ''
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def auditar_cambio(request, entidad, accion, entidad_id=None, detalle=None):
    """Registra un alta/modificación/baja. Solo llamar tras éxito."""
    user = getattr(request, 'user', None)
    return AuditoriaCambio.objects.create(
        actor=user if getattr(user, 'is_authenticated', False) else None,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        detalle=detalle or {},
        ip=ip_cliente(request),
    )
