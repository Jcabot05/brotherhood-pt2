"""Gestión de fichas de cliente (RF-01).

El listado completo expone nombre, teléfono y correo de toda la clientela, y
el borrado arrastra en cascada el historial de citas. Ambas cosas quedan
restringidas a administradores (RN-02, RN-04).
"""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.models import Cliente
from apps.usuarios.permisos import EsAdmin
from apps.usuarios.serializers import ClienteCrearSerializer, ClienteSerializer


class ListaClientes(ListCreateAPIView):
    """Alta pública de clientes; listado sólo para administradores."""

    queryset = Cliente.objects.order_by("id_cliente")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClienteCrearSerializer
        return ClienteSerializer

    def get_permissions(self):
        # El alta queda abierta porque es el punto de entrada de un cliente
        # nuevo; el listado no, porque son datos personales de terceros.
        return [AllowAny()] if self.request.method == "POST" else [EsAdmin()]

    def create(self, request, *args, **kwargs):
        datos = self.get_serializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cliente = datos.save()
        return Response(ClienteSerializer(cliente).data, status=status.HTTP_201_CREATED)


class DetalleCliente(RetrieveUpdateDestroyAPIView):
    """Consulta, actualiza o elimina una ficha de cliente."""

    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"
    lookup_url_kwarg = "id_cliente"

    def get_object(self):
        cliente = super().get_object()
        usuario = self.request.user

        # Un cliente sólo alcanza su propia ficha; el administrador, todas
        # (RN-03).
        if not usuario.es_admin and cliente.usuario_id != usuario.id_usuario:
            raise PermissionDenied("No puede acceder a la ficha de otro cliente.")

        return cliente

    def get_permissions(self):
        # Borrar arrastra las citas en cascada: sólo administradores.
        return [EsAdmin()] if self.request.method == "DELETE" else [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        cliente = self.get_object()
        id_cliente = cliente.id_cliente
        cliente.delete()
        return Response(
            {"mensaje": f"Cliente {id_cliente} eliminado correctamente."},
            status=status.HTTP_200_OK,
        )
