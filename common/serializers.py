class AuditSerializerMixin:
    """Sella el actor desde el request, para serializers usados fuera de una vista con AuditViewMixin (ambos componen de forma segura gracias a setdefault).

    Los serializers concretos deberían marcar los campos de auditoría como
    read-only, por ejemplo en Meta:
        read_only_fields = AuditSerializerMixin.AUDIT_READ_ONLY_FIELDS
    """

    AUDIT_READ_ONLY_FIELDS = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
    )

    def _actor(self):
        request = self.context.get("request")
        return getattr(request, "user", None) if request is not None else None

    def create(self, validated_data):
        actor = self._actor()
        if actor is not None and getattr(actor, "is_authenticated", False):
            # Sobrescribimos (no setdefault): el actor del request manda. Así la
            # auditoría es a prueba de spoofing aunque un serializer concreto
            # olvide marcar created_by/updated_by como read-only.
            validated_data["created_by"] = actor
            validated_data["updated_by"] = actor
        return super().create(validated_data)

    def update(self, instance, validated_data):
        actor = self._actor()
        if actor is not None and getattr(actor, "is_authenticated", False):
            validated_data["updated_by"] = actor
        return super().update(instance, validated_data)
