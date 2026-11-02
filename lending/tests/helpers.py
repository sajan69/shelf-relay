from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.utils import timezone

from lending import services
from lending.roles import setup_roles


def staff(role="Manager", username="manager"):
    setup_roles()
    user = User.objects.create_user(username, password="test-only-long-password")
    user.groups.add(Group.objects.get(name=role))
    return user


def item(actor):
    return services.create_item(actor, "camera", "Camera kit", ["Body", "Cable"])


def window():
    now = timezone.now()
    return now - timedelta(minutes=1), now + timedelta(hours=2)


def booking(actor, kit):
    return services.reserve(actor, kit.pk, "Demo borrower", *window())
