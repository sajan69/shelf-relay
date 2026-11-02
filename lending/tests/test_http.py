from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from lending import services
from lending.models import Booking

from .helpers import booking, item, staff


class HttpTests(TestCase):
    def setUp(self):
        self.actor = staff()
        self.item = item(self.actor)

    def test_login_and_per_permission_guards(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        user = User.objects.create_user("outsider", password="test-only")
        self.client.force_login(user)
        for url in [
            "/",
            "/items/new/",
            "/loans/",
            "/loans/export/",
            f"/items/{self.item.pk}/reserve/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_csrf_and_post_only_handover(self):
        loan = booking(self.actor, self.item)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.actor)
        url = reverse("transition", args=[loan.pk, "checkout"])
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "reserved")

    def test_labels_escaped_no_store_and_security_headers(self):
        self.item.name = "<img src=x onerror=alert(1)>"
        self.item.save()
        self.client.force_login(self.actor)
        response = self.client.get(reverse("detail", args=[self.item.pk]))
        self.assertContains(response, "&lt;img")
        self.assertNotContains(response, "<img")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", response["Content-Security-Policy"])

    def test_export_unknown_times_and_formula_mitigation(self):
        loan = booking(self.actor, self.item)
        Booking.objects.filter(pk=loan.pk).update(borrower="=1+1")
        self.client.force_login(self.actor)
        response = self.client.get("/loans/export/")
        self.assertContains(response, "'=1+1")
        self.assertIn(b'"","",""', response.content)

    def test_return_endpoint_keeps_incomplete_history(self):
        loan = booking(self.actor, self.item)
        services.checkout(self.actor, loan.pk)
        self.client.force_login(self.actor)
        self.client.post(reverse("receive", args=[loan.pk]), {"returned": ["0"]})
        loan.refresh_from_db()
        self.assertEqual(loan.missing_components, ["Cable"])
