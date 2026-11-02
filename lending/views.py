import csv
import io
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import services
from .forms import ItemForm, ReserveForm, ResolveForm, ReturnForm
from .models import Booking, Item


def show_error(request, error):
    if isinstance(error, IntegrityError):
        constraint = getattr(
            getattr(error.__cause__, "diag", None), "constraint_name", ""
        )
        if constraint not in {
            "no_overlapping_active_bookings",
            "one_physical_checkout",
            "lending_item_code_key",
        }:
            raise error
        text = "Another request changed this record. Reload and try again."
    else:
        text = " ".join(error.messages)
    messages.error(request, text)


@login_required
@permission_required("lending.view_item", raise_exception=True)
def catalogue(request):
    query = request.GET.get("q", "")[:100].strip()
    items = Item.objects.all()
    if query:
        items = items.filter(name__icontains=query)
    return render(
        request,
        "lending/catalogue.html",
        {
            "page": Paginator(items, 24).get_page(request.GET.get("page")),
            "query": query,
        },
    )


@login_required
@permission_required("lending.view_item", raise_exception=True)
def detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    return render(
        request,
        "lending/detail.html",
        {
            "item": item,
            "bookings": item.bookings.all()[:20],
            "events": item.events.select_related("actor")[:20],
            "resolve_form": ResolveForm(),
        },
    )


@login_required
@permission_required("lending.manage_catalogue", raise_exception=True)
@require_http_methods(["GET", "POST"])
def new_item(request):
    form = ItemForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            item = services.create_item(
                request.user,
                form.cleaned_data["code"],
                form.cleaned_data["name"],
                form.cleaned_data["checklist"],
            )
        except (ValidationError, IntegrityError) as error:
            show_error(request, error)
        else:
            messages.success(request, "Item added to the shelf.")
            return redirect("detail", item.pk)
    return render(
        request,
        "lending/form.html",
        {"form": form, "title": "Add an item", "button": "Add item"},
    )


@login_required
@permission_required("lending.operate_loans", raise_exception=True)
@require_http_methods(["GET", "POST"])
def reserve(request, pk):
    item = get_object_or_404(Item, pk=pk)
    form = ReserveForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            services.reserve(request.user, item.pk, **form.cleaned_data)
        except (ValidationError, IntegrityError) as error:
            show_error(request, error)
        else:
            messages.success(request, "Reservation saved. Handover is a separate step.")
            return redirect("detail", pk)
    return render(
        request,
        "lending/form.html",
        {"form": form, "title": f"Reserve {item.name}", "button": "Save reservation"},
    )


@login_required
@permission_required("lending.operate_loans", raise_exception=True)
@require_POST
def transition(request, pk, action):
    booking = get_object_or_404(Booking, pk=pk)
    operations = {"checkout": services.checkout, "cancel": services.cancel}
    if action not in operations:
        return HttpResponse(status=404)
    try:
        operations[action](request.user, pk)
    except (ValidationError, IntegrityError) as error:
        show_error(request, error)
    else:
        messages.success(
            request,
            "Handover recorded." if action == "checkout" else "Reservation cancelled.",
        )
    return redirect("detail", booking.item_id)


@login_required
@permission_required("lending.operate_loans", raise_exception=True)
@require_http_methods(["GET", "POST"])
def receive(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("item"), pk=pk)
    form = ReturnForm(
        booking.component_snapshot, request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.receive(request.user, pk, form.cleaned_data["returned"])
        except (ValidationError, IntegrityError) as error:
            show_error(request, error)
        else:
            messages.success(
                request,
                "Return recorded. Any unchecked component keeps the item "
                "unavailable until a manager resolves it.",
            )
            return redirect("detail", booking.item_id)
    return render(
        request,
        "lending/form.html",
        {
            "form": form,
            "title": f"Receive {booking.item.name}",
            "button": "Record return",
            "hint": "Tick only the components received. Unticked components are "
            "recorded as missing; this is not an equipment safety inspection.",
        },
    )


@login_required
@permission_required("lending.manage_catalogue", raise_exception=True)
@require_POST
def resolve(request, pk):
    get_object_or_404(Item, pk=pk)
    form = ResolveForm(request.POST)
    if form.is_valid():
        try:
            services.resolve(request.user, pk, form.cleaned_data["note"])
        except ValidationError as error:
            show_error(request, error)
        else:
            messages.success(
                request, "Attention flag resolved. Original return history is retained."
            )
    else:
        messages.error(request, "Enter a resolution note of 3–300 characters.")
    return redirect("detail", pk)


@login_required
@permission_required("lending.view_item", raise_exception=True)
def loans(request):
    overdue_only = request.GET.get("overdue") == "1"
    bookings = Booking.objects.select_related("item")
    if overdue_only:
        bookings = bookings.filter(status="out", end__lt=timezone.now())
    return render(
        request,
        "lending/loans.html",
        {
            "page": Paginator(bookings, 30).get_page(request.GET.get("page")),
            "overdue_only": overdue_only,
        },
    )


def csv_label(text):
    if unicodedata.normalize("NFKC", text).lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@login_required
@permission_required("lending.operate_loans", raise_exception=True)
def export(request):
    rows = list(Booking.objects.select_related("item").order_by("pk")[:10001])
    if len(rows) > 10000:
        return HttpResponse(
            "Export is limited to 10,000 records; no partial file was generated.",
            status=400,
        )
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(
        [
            "booking_id",
            "item_code",
            "borrower",
            "reserved_start_utc",
            "due_utc",
            "status",
            "checked_out_at_utc",
            "returned_at_utc",
            "missing_components",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.pk,
                csv_label(row.item.code),
                csv_label(row.borrower),
                row.start.isoformat(),
                row.end.isoformat(),
                row.status,
                row.checked_out_at.isoformat() if row.checked_out_at else "",
                row.returned_at.isoformat() if row.returned_at else "",
                csv_label("; ".join(row.missing_components)),
            ]
        )
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="shelf-relay-loans.csv"'
    return response
