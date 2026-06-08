from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from common.mixins import AuditViewMixin
from common.serializers import AuditSerializerMixin
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


class AuditSerializerMixinTests(AuditModelTestCase):
    def _serializer_class(self):
        _model = self.AuditExample

        class _Ser(AuditSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = _model
                fields = ["id", "name", "created_by", "updated_by"]
                read_only_fields = AuditSerializerMixin.AUDIT_READ_ONLY_FIELDS

        return _Ser

    def _request(self, user):
        req = APIRequestFactory().post("/")
        req.user = user
        return req

    def test_create_stamps_actor(self):
        user = User.objects.create_user(email="sc@sc.com", password="x")
        ser = self._serializer_class()(
            data={"name": "a"}, context={"request": self._request(user)}
        )
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        self.assertEqual(obj.created_by, user)
        self.assertEqual(obj.updated_by, user)

    def test_update_stamps_updated_by(self):
        creator = User.objects.create_user(email="sc2@sc.com", password="x")
        editor = User.objects.create_user(email="se@se.com", password="x")
        obj = self.AuditExample.objects.create(
            name="a", created_by=creator, updated_by=creator
        )
        ser = self._serializer_class()(
            instance=obj,
            data={"name": "b"},
            partial=True,
            context={"request": self._request(editor)},
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        obj.refresh_from_db()
        self.assertEqual(obj.created_by, creator)
        self.assertEqual(obj.updated_by, editor)

    def test_create_without_context_does_not_crash(self):
        ser = self._serializer_class()(data={"name": "b"})
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        self.assertIsNone(obj.created_by)
        self.assertIsNone(obj.updated_by)

    def test_create_with_anonymous_user_does_not_stamp(self):
        from unittest.mock import Mock

        anon = Mock()
        anon.is_authenticated = False
        req = APIRequestFactory().post("/")
        req.user = anon
        ser = self._serializer_class()(
            data={"name": "c"}, context={"request": req}
        )
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        self.assertIsNone(obj.created_by)
        self.assertIsNone(obj.updated_by)

    def test_create_overrides_client_supplied_actor(self):
        actor = User.objects.create_user(email="real@r.com", password="x")
        spoof_target = User.objects.create_user(email="spoof@s.com", password="x")
        _model = self.AuditExample

        # Serializer que EXPONE created_by/updated_by como escribibles a propósito,
        # para verificar que el mixin igual impone el actor del request.
        class _WritableSer(AuditSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = _model
                fields = ["id", "name", "created_by", "updated_by"]

        ser = _WritableSer(
            data={
                "name": "a",
                "created_by": str(spoof_target.pk),
                "updated_by": str(spoof_target.pk),
            },
            context={"request": self._request(actor)},
        )
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        self.assertEqual(obj.created_by, actor)
        self.assertEqual(obj.updated_by, actor)
