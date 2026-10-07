from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import AuditoriaCambio
from apps.auditoria.serializers import AuditoriaCambioSerializer
from apps.usuarios.permissions import EsAdmin


class AuditoriaCambiosListView(APIView):
    """GET /auditoria/cambios/ — consulta de auditoría (solo superadmin).

    Filtros: ?entidad=&accion=&actor= (email parcial) &desde=aaaa-mm-dd
    &hasta=aaaa-mm-dd &limit= (default 100, max 500).
    """
    permission_classes = [EsAdmin]

    def get(self, request):
        qs = AuditoriaCambio.objects.select_related('actor').all()
        entidad = request.query_params.get('entidad')
        if entidad:
            qs = qs.filter(entidad=entidad)
        accion = request.query_params.get('accion')
        if accion:
            qs = qs.filter(accion=accion)
        actor = request.query_params.get('actor')
        if actor:
            qs = qs.filter(actor__email__icontains=actor)
        desde = request.query_params.get('desde')
        hasta = request.query_params.get('hasta')
        desde_fecha = parse_date(desde) if desde else None
        hasta_fecha = parse_date(hasta) if hasta else None
        if desde_fecha and hasta_fecha and desde_fecha > hasta_fecha:
            return Response(
                {'detail': 'El filtro "desde" debe ser menor o igual que "hasta".'},
                status=400,
            )
        if desde_fecha:
            qs = qs.filter(created_at__date__gte=desde_fecha)
        if hasta_fecha:
            qs = qs.filter(created_at__date__lte=hasta_fecha)
        try:
            limit = min(max(int(request.query_params.get('limit', 100)), 1), 500)
        except (TypeError, ValueError):
            limit = 100
        serializer = AuditoriaCambioSerializer(qs[:limit], many=True)
        return Response(serializer.data)
