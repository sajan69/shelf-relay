from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from lending import services
from lending.models import Item
from lending.roles import setup_roles


class Command(BaseCommand):
    help = "Seed fictional equipment and public demo-only staff accounts "
    "into an empty local installation."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or User.objects.exists() or Item.objects.exists():
            raise CommandError(
                "Demo requires DEBUG=1 and an empty installation; nothing was changed."
            )
        setup_roles()
        for username, role in [("demo-manager", "Manager"), ("demo-lender", "Lender")]:
            user = User.objects.create_user(username, password="demo-only-change-me")
            user.groups.add(Group.objects.get(name=role))
        actor = User.objects.get(username="demo-manager")
        camera = services.create_item(
            actor,
            "camera-01",
            "Community camera kit",
            ["Camera body", "Battery", "Charger", "Carry case"],
        )
        services.create_item(
            actor, "speaker-01", "Portable speaker", ["Speaker", "Power cable"]
        )
        services.create_item(
            actor,
            "projector-01",
            "Meeting projector",
            ["Projector", "HDMI cable", "Remote"],
        )
        now = timezone.now()
        services.reserve(
            actor,
            camera.pk,
            "Demo · Alex",
            now - timedelta(minutes=1),
            now + timedelta(days=1),
        )
        self.stdout.write(
            "Fictional demo created. Local-only login: demo-manager / "
            "demo-only-change-me"
        )
