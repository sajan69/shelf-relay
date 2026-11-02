from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase

from lending import services
from lending.models import Booking, Event

from .helpers import booking, item, staff, window


class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actor = staff()
        self.item = item(self.actor)

    def race(self, operation):
        barrier = Barrier(2)
        actor_id = self.actor.pk

        def run():
            try:
                actor = User.objects.get(pk=actor_id)
                barrier.wait(timeout=10)
                operation(actor)
                return "saved"
            except ValidationError:
                return "refused"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(sorted(results), ["refused", "saved"])

    def test_racing_reservations_only_one_persists(self):
        start, end = window()
        self.race(
            lambda actor: services.reserve(
                actor, self.item.pk, "Racing borrower", start, end
            )
        )
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Event.objects.filter(action="reserved").count(), 1)

    def test_racing_handovers_only_one_event(self):
        loan = booking(self.actor, self.item)
        self.race(lambda actor: services.checkout(actor, loan.pk))
        self.assertEqual(Event.objects.filter(action="checked_out").count(), 1)
