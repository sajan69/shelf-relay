from django.contrib.auth.models import Group, Permission


def setup_roles():
    reader = ["view_item"]
    for name, codes in {
        "Viewer": reader,
        "Lender": reader + ["operate_loans"],
        "Manager": reader + ["operate_loans", "manage_catalogue"],
    }.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="lending", codename__in=codes
            )
        )
