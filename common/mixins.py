class AuditViewMixin:
    """Para vistas/viewsets genéricas de DRF: sella el actor desde request.user.

    Úsese como primera clase base:
        class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet): ...
    """

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
