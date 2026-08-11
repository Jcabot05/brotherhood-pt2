"""Rutas de autenticación. Se montan bajo `/auth/`."""

from django.urls import path

from apps.usuarios import vistas_clientes, vistas_sesion

urlpatterns = [
    path("registro", vistas_sesion.registrar, name="registro"),
    path("login", vistas_sesion.iniciar_sesion, name="login"),
    path("logout", vistas_sesion.cerrar_sesion, name="logout"),
    path("yo", vistas_sesion.consultar_cuenta, name="yo"),
]

# Rutas de fichas de cliente. Se montan en la raíz, no bajo `/auth/`, para
# conservar las mismas URLs que publicaba la versión anterior.
rutas_clientes = [
    path("clientes/", vistas_clientes.ListaClientes.as_view(), name="clientes"),
    path(
        "clientes/<int:id_cliente>",
        vistas_clientes.DetalleCliente.as_view(),
        name="cliente-detalle",
    ),
]
