"""Vistas del catálogo: servicios (RF-03, RF-04) y barberos (RF-02).

Consultar el catálogo es público (RN-01, HU-01): un visitante debe poder ver
qué se ofrece antes de crear una cuenta. Modificarlo exige rol de
administrador (RN-04).
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from apps.catalogo.models import Barbero, Servicio
from apps.catalogo.serializers import BarberoSerializer, ServicioSerializer
from apps.usuarios.permisos import EsAdmin, SoloLecturaPublica


# --- Servicios -------------------------------------------------------------


class ListaServicios(ListCreateAPIView):
    """Catálogo de servicios. Lectura pública, alta sólo para administradores."""

    serializer_class = ServicioSerializer
    permission_classes = [SoloLecturaPublica]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "incluir_inactivos",
                bool,
                description="Incluye los servicios retirados del catálogo.",
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        consulta = Servicio.objects.order_by("id_servicio")

        # Los servicios retirados sólo se listan si se piden expresamente, y
        # sólo para administradores: el visitante no debe ver lo que ya no se
        # ofrece (RN-16).
        incluir = self.request.query_params.get("incluir_inactivos", "").lower()
        usuario = self.request.user
        if incluir in ("true", "1") and usuario is not None and usuario.es_admin:
            return consulta

        return consulta.filter(activo=True)


class DetalleServicio(RetrieveUpdateDestroyAPIView):
    """Consulta, actualiza o retira un servicio."""

    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [SoloLecturaPublica]
    lookup_field = "pk"
    lookup_url_kwarg = "id_servicio"

    def destroy(self, request, *args, **kwargs):
        """Retiro lógico (RN-16).

        Un servicio con citas asociadas no se elimina físicamente: se marca
        como inactivo para preservar el historial.
        """
        servicio = self.get_object()
        servicio.activo = False
        servicio.save(update_fields=["activo"])
        return Response(
            {"mensaje": f"Servicio {servicio.id_servicio} retirado del catálogo."},
            status=status.HTTP_200_OK,
        )


@extend_schema(request=None, responses={200: ServicioSerializer})
@api_view(["POST"])
@permission_classes([EsAdmin])
def reactivar_servicio(request, id_servicio: int):
    """Devuelve al catálogo un servicio retirado."""
    servicio = Servicio.objects.filter(pk=id_servicio).first()
    if servicio is None:
        return Response(
            {"detail": f"No existe un servicio con id {id_servicio}."},
            status=status.HTTP_404_NOT_FOUND,
        )

    servicio.activo = True
    servicio.save(update_fields=["activo"])
    return Response(ServicioSerializer(servicio).data)


# --- Barberos --------------------------------------------------------------
# El listado es público porque el formulario de agendar necesita ofrecer los
# barberos disponibles. Las escrituras, en cambio, son de administración.


class ListaBarberos(ListCreateAPIView):
    """Barberos de la barbería. Lectura pública, alta sólo administradores."""

    queryset = Barbero.objects.order_by("id_barbero")
    serializer_class = BarberoSerializer
    permission_classes = [SoloLecturaPublica]


class DetalleBarbero(RetrieveUpdateDestroyAPIView):
    """Consulta, actualiza o elimina un barbero."""

    queryset = Barbero.objects.all()
    serializer_class = BarberoSerializer
    permission_classes = [SoloLecturaPublica]
    lookup_field = "pk"
    lookup_url_kwarg = "id_barbero"

    def destroy(self, request, *args, **kwargs):
        barbero = self.get_object()
        id_barbero = barbero.id_barbero
        # Ojo: la FK de cita es ON DELETE CASCADE, así que esto se lleva por
        # delante las citas del barbero. Por eso exige rol de administrador.
        barbero.delete()
        return Response(
            {"mensaje": f"Barbero {id_barbero} eliminado correctamente."},
            status=status.HTTP_200_OK,
        )
