"""Rutas de autenticación. Se montan bajo `/auth/`."""

from django.urls import path

from apps.usuarios import views

urlpatterns = [
    path("registro", views.registrar, name="registro"),
    path("login", views.iniciar_sesion, name="login"),
    path("logout", views.cerrar_sesion, name="logout"),
    path("yo", views.consultar_cuenta, name="yo"),
]

# Rutas de fichas de cliente. Se montan en la raíz, no bajo `/auth/`, para
# conservar las mismas URLs que publicaba la versión anterior.
rutas_clientes = [
    path("clientes/", views.ListaClientes.as_view(), name="clientes"),
    path(
        "clientes/<int:id_cliente>",
        views.DetalleCliente.as_view(),
        name="cliente-detalle",
    ),
]
