from getpass import getpass

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create a staff login using Django password validation and one lending role."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--role", choices=["Viewer", "Lender", "Manager"], required=True
        )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            group = Group.objects.get(name=options["role"])
        except Group.DoesNotExist as error:
            raise CommandError("Run setup_roles before adding staff.") from error
        form = UserCreationForm(
            {
                "username": options["username"],
                "password1": getpass("Password: "),
                "password2": getpass("Repeat password: "),
            }
        )
        if not form.is_valid():
            raise CommandError(form.errors.as_text())
        user = form.save()
        user.groups.add(group)
        self.stdout.write("Staff account created without administrator privileges.")
