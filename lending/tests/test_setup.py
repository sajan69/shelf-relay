from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from lending.models import Item
from lending.roles import setup_roles


class SetupTests(TestCase):
    def test_staff_creation_validates_password_and_assigns_only_selected_role(self):
        setup_roles()
        with patch(
            "lending.management.commands.add_staff.getpass",
            return_value="Unique-test-only-passphrase-987",
        ):
            call_command("add_staff", "operator", role="Lender", stdout=StringIO())
        user = User.objects.get(username="operator")
        self.assertTrue(user.check_password("Unique-test-only-passphrase-987"))
        self.assertTrue(user.has_perm("lending.operate_loans"))
        self.assertFalse(user.has_perm("lending.manage_catalogue"))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        with patch("lending.management.commands.add_staff.getpass", return_value="123"):
            with self.assertRaises(CommandError):
                call_command("add_staff", "invalid", role="Manager", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="invalid").exists())

    @override_settings(DEBUG=True)
    def test_demo_refuses_reseed_without_changing_existing_records(self):
        call_command("demo", demo=True, stdout=StringIO())
        counts = User.objects.count(), Item.objects.count()
        with self.assertRaises(CommandError):
            call_command("demo", demo=True, stdout=StringIO())
        self.assertEqual(counts, (User.objects.count(), Item.objects.count()))
