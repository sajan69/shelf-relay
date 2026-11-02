from django.core.management.base import BaseCommand

from lending.roles import setup_roles


class Command(BaseCommand):
    help = "Create the Viewer, Lender and Manager permission groups."

    def handle(self, *args, **options):
        setup_roles()
        self.stdout.write("Permission groups configured.")
