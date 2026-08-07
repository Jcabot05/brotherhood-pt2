"""Rutas de la API de TheBrotherhood."""

from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.usuarios.urls import rutas_clientes


def raiz(request):
    """Presenta la API y orienta hacia la documentación."""
    return JsonResponse(
        {
            "nombre": "TheBrotherhood — API de gestión de citas",
            "version": "3.0.0",
            "documentacion": "/docs",
        }
    )


def salud(request):
    """Comprobación de vida del servicio."""
    return JsonResponse({"estado": "ok"})


urlpatterns = [
    path("", raiz),
    path("salud", salud),
    path("auth/", include("apps.usuarios.urls")),
    path("", include(rutas_clientes)),
    path("", include("apps.catalogo.urls")),
    path("citas/", include("apps.citas.urls")),
    # Documentación interactiva, equivalente al Swagger que FastAPI daba
    # de forma automática.
    path("esquema", SpectacularAPIView.as_view(), name="esquema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="esquema"), name="docs"),
]
