from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from lending import services
from lending.models import Booking, Event

from .helpers import booking, item, staff, window


class WorkflowTests(TestCase):
    def setUp(self):
        self.actor = staff()
        self.item = item(self.actor)

    def test_complete_handover_and_return_history(self):
        loan = booking(self.actor, self.item)
        services.checkout(self.actor, loan.pk)
        services.receive(self.actor, loan.pk, ["0", "1"])
        loan.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(loan.status, "returned")
        self.assertIsNotNone(loan.checked_out_at)
        self.assertIsNotNone(loan.returned_at)
        self.assertFalse(self.item.needs_attention)
        self.assertEqual(Event.objects.filter(booking=loan).count(), 3)

    def test_incomplete_return_blocks_until_manager_resolution(self):
        loan = booking(self.actor, self.item)
        services.checkout(self.actor, loan.pk)
        services.receive(self.actor, loan.pk, ["0"])
        with self.assertRaises(ValidationError):
            booking(self.actor, self.item)
        services.resolve(self.actor, self.item.pk, "Cable recovered from the case")
        loan.refresh_from_db()
        self.assertEqual(loan.missing_components, ["Cable"])
        self.assertIsNotNone(booking(self.actor, self.item))

    def test_existing_future_reservation_cannot_checkout_attention_item(self):
        now = timezone.now()
        loan = services.reserve(
            self.actor,
            self.item.pk,
            "First",
            now - timedelta(minutes=1),
            now + timedelta(minutes=1),
        )
        future = services.reserve(
            self.actor,
            self.item.pk,
            "Next",
            now + timedelta(minutes=1),
            now + timedelta(hours=1),
        )
        services.checkout(self.actor, loan.pk)
        services.receive(self.actor, loan.pk, [])
        # Make the second booking current without relying on sleeps.
        Booking.objects.filter(pk=future.pk).update(start=now - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            services.checkout(self.actor, future.pk)

    def test_boundary_adjacency_cancel_and_overlap(self):
        start, end = window()
        loan = services.reserve(self.actor, self.item.pk, "One", start, end)
        services.reserve(self.actor, self.item.pk, "Two", end, end + timedelta(hours=1))
        with self.assertRaises(ValidationError):
            services.reserve(self.actor, self.item.pk, "Overlap", start, end)
        services.cancel(self.actor, loan.pk)
        self.assertIsNotNone(
            services.reserve(self.actor, self.item.pk, "Replacement", start, end)
        )

    def test_duplicate_transitions_do_not_create_events(self):
        loan = booking(self.actor, self.item)
        services.checkout(self.actor, loan.pk)
        before = Event.objects.count()
        for op in [services.checkout, services.cancel]:
            with self.assertRaises(ValidationError):
                op(self.actor, loan.pk)
        self.assertEqual(Event.objects.count(), before)

    def test_database_refuses_bypassed_overlap_and_nonpositive_window(self):
        loan = booking(self.actor, self.item)
        for start, end in [(loan.start, loan.end), (loan.end, loan.start)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Booking.objects.create(
                    item=self.item, borrower="Bypass", start=start, end=end
                )

    def test_physical_checkout_constraint_independent_of_reserved_window(self):
        start, end = window()
        Booking.objects.create(
            item=self.item, borrower="One", start=start, end=end, status="out"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                item=self.item,
                borrower="Two",
                start=end,
                end=end + timedelta(hours=1),
                status="out",
            )

    def test_checklist_payload_cannot_mark_unknown_or_duplicate_indices(self):
        loan = booking(self.actor, self.item)
        services.checkout(self.actor, loan.pk)
        for indices in [["9"], ["0", "0"]]:
            with self.assertRaises(ValidationError):
                services.receive(self.actor, loan.pk, indices)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "out")

    def test_service_permissions_not_only_hidden_buttons(self):
        viewer = staff("Viewer", "viewer")
        lender = staff("Lender", "lender")
        for actor, op in [
            (viewer, lambda a: booking(a, self.item)),
            (lender, lambda a: services.create_item(a, "new", "New", ["Body"])),
        ]:
            with self.assertRaises(PermissionDenied):
                op(actor)
        self.item.needs_attention = True
        self.item.save()
        with self.assertRaises(PermissionDenied):
            services.resolve(lender, self.item.pk, "Recovered")

    def test_future_checkout_refused_and_overdue_is_only_physical(self):
        now = timezone.now()
        loan = services.reserve(
            self.actor,
            self.item.pk,
            "Future",
            now + timedelta(days=1),
            now + timedelta(days=2),
        )
        with self.assertRaises(ValidationError):
            services.checkout(self.actor, loan.pk)
        Booking.objects.filter(pk=loan.pk).update(
            start=now - timedelta(days=2), end=now - timedelta(days=1)
        )
        loan.refresh_from_db()
        self.assertFalse(loan.overdue)
        loan.status = "out"
        loan.save()
        self.assertTrue(loan.overdue)
