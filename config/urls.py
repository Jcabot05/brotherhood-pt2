"""Rutas de la API y del cliente web de TheBrotherhood."""

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.usuarios.urls import rutas_clientes


def salud(request):
    """Comprobación de vida del servicio."""
    return JsonResponse({"estado": "ok"})


def cliente_web(request, ruta=""):
    """Entrega el cliente de React.

    Devuelve siempre `index.html`: las rutas de la interfaz (`/login`,
    `/agendar`) las resuelve react-router dentro del navegador, no el
    servidor. Sin esto, recargar la página en una de ellas daría 404.

    Se declara al final del enrutado, así que sólo atiende lo que no haya
    reclamado antes la API.
    """
    indice = settings.CLIENTE_BUILD / "index.html"

    if not indice.is_file():
        # Sin build disponible se explica cómo generarlo, en lugar de dar un
        # 404 que no orienta.
        return JsonResponse(
            {
                "nombre": "TheBrotherhood — API de gestión de citas",
                "version": "3.0.0",
                "documentacion": "/docs",
                "detail": (
                    "El cliente web no está compilado. Ejecute "
                    "`cd cliente && npm run build`, o use el servidor de "
                    "desarrollo con `npm run dev`."
                ),
            },
            status=501,
        )

    return FileResponse(open(indice, "rb"), content_type="text/html")


urlpatterns = [
    path("salud", salud),
    # --- API ---
    path("auth/", include("apps.usuarios.urls")),
    path("", include(rutas_clientes)),
    path("", include("apps.catalogo.urls")),
    path("citas/", include("apps.citas.urls")),
    # Documentación interactiva, equivalente al Swagger que FastAPI daba de
    # forma automática.
    path("esquema", SpectacularAPIView.as_view(), name="esquema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="esquema"), name="docs"),
    # --- Cliente web ---
    # Los archivos que genera Vite llevan un hash en el nombre, así que
    # pueden cachearse sin riesgo de servir una versión vieja.
    re_path(
        r"^assets/(?P<path>.*)$",
        serve,
        {"document_root": settings.CLIENTE_BUILD / "assets"},
    ),
    # Fotografías del catálogo. Sin esta ruta las pediría el catch-all, que
    # respondería con el HTML del cliente en lugar de la imagen.
    re_path(
        r"^servicios/(?P<path>.*\.(?:jpg|jpeg|png|webp|svg))$",
        serve,
        {"document_root": settings.CLIENTE_BUILD / "servicios"},
    ),
    # Catch-all: va el último para no tapar ninguna ruta de la API.
    re_path(r"^(?P<ruta>.*)$", cliente_web),
]
