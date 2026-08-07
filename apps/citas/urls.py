"""Rutas de la agenda. Se montan bajo `/citas/`."""

from django.urls import path

from apps.citas import views

urlpatterns = [
    path("", views.ListaCitas.as_view(), name="citas"),
    # Va antes que `<int:id_cita>` para que la ruta literal no quede capturada
    # por el conversor de entero.
    path(
        "disponibilidad",
        views.consultar_disponibilidad,
        name="disponibilidad",
    ),
    path("<int:id_cita>", views.DetalleCita.as_view(), name="cita-detalle"),
    path("<int:id_cita>/estado", views.cambiar_estado, name="cita-estado"),
]
