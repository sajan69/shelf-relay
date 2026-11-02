from django.conf import settings


def site_zone(request):
    return {"site_zone": settings.TIME_ZONE}
