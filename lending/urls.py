from django.urls import path

from . import views

urlpatterns = [
    path("", views.catalogue, name="catalogue"),
    path("items/new/", views.new_item, name="new_item"),
    path("items/<int:pk>/", views.detail, name="detail"),
    path("items/<int:pk>/reserve/", views.reserve, name="reserve"),
    path("items/<int:pk>/resolve/", views.resolve, name="resolve"),
    path("loans/", views.loans, name="loans"),
    path("loans/export/", views.export, name="export"),
    path("loans/<int:pk>/receive/", views.receive, name="receive"),
    path("loans/<int:pk>/<str:action>/", views.transition, name="transition"),
]
