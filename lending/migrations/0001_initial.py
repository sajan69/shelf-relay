import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
import django.db.models.deletion
from django.conf import settings
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.CreateModel(
            name="Booking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("borrower", models.CharField(max_length=80)),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("reserved", "Reserved"),
                            ("out", "Checked out"),
                            ("returned", "Returned"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="reserved",
                        max_length=12,
                    ),
                ),
                ("component_snapshot", models.JSONField(default=list)),
                ("missing_components", models.JSONField(default=list)),
                ("checked_out_at", models.DateTimeField(null=True)),
                ("returned_at", models.DateTimeField(null=True)),
            ],
            options={
                "ordering": ["-start", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.SlugField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("components", models.JSONField(default=list)),
                ("needs_attention", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["name", "pk"],
                "permissions": [
                    ("operate_loans", "Reserve, hand over and receive items"),
                    ("manage_catalogue", "Create items and resolve incomplete kits"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("action", models.CharField(max_length=32)),
                ("note", models.CharField(blank=True, max_length=300)),
                ("at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="lending.booking",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="lending.item",
                    ),
                ),
            ],
            options={
                "ordering": ["-at", "-pk"],
            },
        ),
        migrations.AddField(
            model_name="booking",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="lending.item",
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(
                condition=models.Q(("end__gt", models.F("start"))),
                name="positive_booking_window",
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("status__in", ["reserved", "out", "returned", "cancelled"])
                ),
                name="known_booking_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "out")),
                fields=("item",),
                name="one_physical_checkout",
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                condition=models.Q(("status__in", ["reserved", "out"])),
                expressions=[
                    ("item", "="),
                    (
                        models.Func(
                            models.F("start"),
                            models.F("end"),
                            models.Value("[)"),
                            function="TSTZRANGE",
                            output_field=django.contrib.postgres.fields.ranges.DateTimeRangeField(),
                        ),
                        "&&",
                    ),
                ],
                name="no_overlapping_active_bookings",
            ),
        ),
    ]
