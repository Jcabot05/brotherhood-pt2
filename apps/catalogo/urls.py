"""Rutas del catálogo: servicios y barberos."""

from django.urls import path

from apps.catalogo import views

urlpatterns = [
    path("servicios/", views.ListaServicios.as_view(), name="servicios"),
    path(
        "servicios/<int:id_servicio>",
        views.DetalleServicio.as_view(),
        name="servicio-detalle",
    ),
    path(
        "servicios/<int:id_servicio>/reactivar",
        views.reactivar_servicio,
        name="servicio-reactivar",
    ),
    path("barberos/", views.ListaBarberos.as_view(), name="barberos"),
    path(
        "barberos/<int:id_barbero>",
        views.DetalleBarbero.as_view(),
        name="barbero-detalle",
    ),
]
