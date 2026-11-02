from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import F, Q, Value
from django.utils import timezone


class Item(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    components = models.JSONField(default=list)
    needs_attention = models.BooleanField(default=False)

    class Meta:
        ordering = ["name", "pk"]
        permissions = [
            ("operate_loans", "Reserve, hand over and receive items"),
            ("manage_catalogue", "Create items and resolve incomplete kits"),
        ]

    def __str__(self):
        return f"{self.code} · {self.name}"


class Booking(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        OUT = "out", "Checked out"
        RETURNED = "returned", "Returned"
        CANCELLED = "cancelled", "Cancelled"

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="bookings")
    borrower = models.CharField(max_length=80)
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status, default=Status.RESERVED)
    component_snapshot = models.JSONField(default=list)
    missing_components = models.JSONField(default=list)
    checked_out_at = models.DateTimeField(null=True)
    returned_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["-start", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="positive_booking_window"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["reserved", "out", "returned", "cancelled"]),
                name="known_booking_status",
            ),
            models.UniqueConstraint(
                fields=["item"], condition=Q(status="out"), name="one_physical_checkout"
            ),
            ExclusionConstraint(
                name="no_overlapping_active_bookings",
                expressions=[
                    ("item", RangeOperators.EQUAL),
                    (
                        models.Func(
                            F("start"),
                            F("end"),
                            Value("[)"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(status__in=["reserved", "out"]),
            ),
        ]

    @property
    def overdue(self):
        return self.status == self.Status.OUT and self.end < timezone.now()


class Event(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="events")
    booking = models.ForeignKey(
        Booking, null=True, on_delete=models.PROTECT, related_name="events"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at", "-pk"]

    @property
    def action_label(self):
        return {
            "created": "Item added",
            "reserved": "Reservation saved",
            "checked_out": "Handover recorded",
            "cancelled": "Reservation cancelled",
            "returned_incomplete": "Incomplete return recorded",
            "returned_complete": "Complete return recorded",
            "attention_resolved": "Missing components resolved",
        }.get(self.action, "Other event")
