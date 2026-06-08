from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from common.mixins import AuditViewMixin
from common.tests.base import AuditModelTestCase

User = get_user_model()


class AuditViewMixinTests(AuditModelTestCase):
    def _serializer_class(self):
        _model = self.AuditExample

        class _ExampleSerializer(serializers.ModelSerializer):
            class Meta:
                model = _model
                fields = ["id", "name", "created_by", "updated_by"]
                read_only_fields = ["created_by", "updated_by"]

        return _ExampleSerializer

    def _view_with_user(self, user):
        class _View(AuditViewMixin):
            pass

        view = _View()
        request = APIRequestFactory().post("/")
        request.user = user
        view.request = request
        return view

    def test_perform_create_stamps_actor(self):
        user = User.objects.create_user(email="v@v.com", password="x")
        serializer = self._serializer_class()(data={"name": "a"})
        serializer.is_valid(raise_exception=True)

        self._view_with_user(user).perform_create(serializer)

        obj = serializer.instance
        self.assertEqual(obj.created_by, user)
        self.assertEqual(obj.updated_by, user)

    def test_perform_update_stamps_updated_by(self):
        creator = User.objects.create_user(email="c@c.com", password="x")
        editor = User.objects.create_user(email="e@e.com", password="x")
        obj = self.AuditExample.objects.create(
            name="a", created_by=creator, updated_by=creator
        )

        serializer = self._serializer_class()(
            instance=obj, data={"name": "b"}, partial=True
        )
        serializer.is_valid(raise_exception=True)

        self._view_with_user(editor).perform_update(serializer)

        obj.refresh_from_db()
        self.assertEqual(obj.created_by, creator)
        self.assertEqual(obj.updated_by, editor)
