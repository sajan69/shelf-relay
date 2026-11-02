"""State transitions lock the physical item first, in one transaction."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .forms import ReserveForm, clean_components
from .models import Booking, Event, Item


def authorize(actor, permission):
    if not actor.is_active or not actor.has_perm(f"lending.{permission}"):
        raise PermissionDenied


def record(item, actor, action, booking=None, note=""):
    Event.objects.create(
        item=item, actor=actor, action=action, booking=booking, note=note
    )


@transaction.atomic
def create_item(actor, code, name, components):
    authorize(actor, "manage_catalogue")
    item = Item(
        code=code, name=name, components=clean_components("\n".join(components))
    )
    item.full_clean()
    item.save()
    record(item, actor, "created")
    return item


@transaction.atomic
def reserve(actor, item_id, borrower, start, end):
    authorize(actor, "operate_loans")
    # The service validates too; forms are not the integrity boundary.
    form = ReserveForm({"borrower": borrower, "start": start, "end": end})
    if not form.is_valid():
        raise ValidationError(form.errors.as_text())
    start, end = form.cleaned_data["start"], form.cleaned_data["end"]
    item = Item.objects.select_for_update().get(pk=item_id)
    if item.needs_attention:
        raise ValidationError("This kit needs attention before another reservation.")
    if item.bookings.filter(
        status__in=["reserved", "out"], start__lt=end, end__gt=start
    ).exists():
        raise ValidationError("That time overlaps an active reservation or loan.")
    booking = Booking.objects.create(
        item=item,
        borrower=form.cleaned_data["borrower"],
        start=start,
        end=end,
        component_snapshot=item.components,
    )
    record(item, actor, "reserved", booking)
    return booking


def locked_booking(booking_id):
    item_id = Booking.objects.values_list("item_id", flat=True).get(pk=booking_id)
    item = Item.objects.select_for_update().get(pk=item_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    return item, booking


@transaction.atomic
def checkout(actor, booking_id):
    authorize(actor, "operate_loans")
    item, booking = locked_booking(booking_id)
    now = timezone.now()
    if booking.status != "reserved" or not booking.start <= now < booking.end:
        raise ValidationError("Only a current reserved booking can be checked out.")
    if item.needs_attention or item.bookings.filter(status="out").exists():
        raise ValidationError("The item is still out or needs attention.")
    booking.status, booking.checked_out_at = "out", now
    booking.save(update_fields=["status", "checked_out_at"])
    record(item, actor, "checked_out", booking)


@transaction.atomic
def cancel(actor, booking_id):
    authorize(actor, "operate_loans")
    item, booking = locked_booking(booking_id)
    if booking.status != "reserved":
        raise ValidationError("Only a reserved booking can be cancelled.")
    booking.status = "cancelled"
    booking.save(update_fields=["status"])
    record(item, actor, "cancelled", booking)


@transaction.atomic
def receive(actor, booking_id, received_indices):
    authorize(actor, "operate_loans")
    item, booking = locked_booking(booking_id)
    if booking.status != "out":
        raise ValidationError("This item is not checked out.")
    valid = {str(i) for i in range(len(booking.component_snapshot))}
    if (
        not isinstance(received_indices, list)
        or len(set(received_indices)) != len(received_indices)
        or not set(received_indices) <= valid
    ):
        raise ValidationError(
            "The component checklist changed or contains invalid choices."
        )
    missing = [
        label
        for i, label in enumerate(booking.component_snapshot)
        if str(i) not in received_indices
    ]
    booking.status, booking.returned_at, booking.missing_components = (
        "returned",
        timezone.now(),
        missing,
    )
    booking.save(update_fields=["status", "returned_at", "missing_components"])
    item.needs_attention = bool(missing)
    item.save(update_fields=["needs_attention"])
    record(
        item, actor, "returned_incomplete" if missing else "returned_complete", booking
    )


@transaction.atomic
def resolve(actor, item_id, note):
    authorize(actor, "manage_catalogue")
    item = Item.objects.select_for_update().get(pk=item_id)
    if not item.needs_attention or not 3 <= len(note.strip()) <= 300:
        raise ValidationError(
            "An attention flag and a short resolution note are required."
        )
    item.needs_attention = False
    item.save(update_fields=["needs_attention"])
    record(item, actor, "attention_resolved", note=note.strip())
