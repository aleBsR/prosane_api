class AuditViewMixin:
    """Para vistas/viewsets genéricas de DRF: sella el actor desde request.user.

    Úsese como primera clase base:
        class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet): ...
    """

    # No llamamos a super().perform_create/update a propósito: el default de DRF
    # es serializer.save() sin kwargs, así que llamarlo duplicaría el guardado.
    # Este mixin termina la cadena para esos dos métodos.

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
