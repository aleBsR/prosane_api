import time

from django.contrib.auth import get_user_model

from common.tests.base import AuditModelTestCase

User = get_user_model()


class TimestampTests(AuditModelTestCase):
    def test_created_and_updated_at_set_on_create(self):
        obj = self.AuditExample.objects.create(name="a")
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

    def test_updated_at_changes_on_save(self):
        obj = self.AuditExample.objects.create(name="a")
        first = obj.updated_at
        time.sleep(0.01)
        obj.name = "b"
        obj.save()
        obj.refresh_from_db()
        self.assertGreater(obj.updated_at, first)


class SoftDeleteTests(AuditModelTestCase):
    def test_delete_sets_deleted_at_and_keeps_row(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        self.assertIsNotNone(obj.deleted_at)
        self.assertTrue(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_default_manager_hides_deleted(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        self.assertFalse(self.AuditExample.objects.filter(pk=obj.pk).exists())
        self.assertTrue(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_hard_delete_removes_row(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.hard_delete()
        self.assertFalse(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_restore_brings_back(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        obj.restore()
        self.assertIsNone(obj.deleted_at)
        self.assertTrue(self.AuditExample.objects.filter(pk=obj.pk).exists())

    def test_queryset_delete_is_soft(self):
        self.AuditExample.objects.create(name="a")
        self.AuditExample.objects.create(name="b")
        self.AuditExample.objects.all().delete()
        self.assertEqual(self.AuditExample.objects.count(), 0)
        self.assertEqual(self.AuditExample.all_objects.count(), 2)

    def test_all_objects_exposes_alive_and_dead(self):
        alive_obj = self.AuditExample.objects.create(name="alive")
        dead_obj = self.AuditExample.objects.create(name="dead")
        dead_obj.delete()

        alive_pks = set(
            self.AuditExample.all_objects.alive().values_list("pk", flat=True)
        )
        dead_pks = set(
            self.AuditExample.all_objects.dead().values_list("pk", flat=True)
        )
        self.assertEqual(alive_pks, {alive_obj.pk})
        self.assertEqual(dead_pks, {dead_obj.pk})

    def test_all_objects_queryset_delete_is_soft(self):
        self.AuditExample.objects.create(name="a")
        self.AuditExample.objects.create(name="b")
        self.AuditExample.all_objects.all().delete()
        self.assertEqual(self.AuditExample.objects.count(), 0)
        self.assertEqual(self.AuditExample.all_objects.count(), 2)


class ActorTests(AuditModelTestCase):
    def test_created_by_and_updated_by_stored(self):
        user = User.objects.create_user(email="t@t.com", password="x")
        obj = self.AuditExample.objects.create(
            name="a", created_by=user, updated_by=user
        )
        self.assertEqual(obj.created_by, user)
        self.assertEqual(obj.updated_by, user)
