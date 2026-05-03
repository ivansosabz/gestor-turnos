"""URL configuration raíz del proyecto.

Tres bloques de rutas:
- /admin/ → admin de Django
- /api/   → endpoints REST (turnos.api_urls)
- /      → vistas HTML (turnos.urls)
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # IMPORTANTE: la API va antes que la app raíz para que /api/... no
    # caiga en una vista HTML por accidente.
    path("api/", include("turnos.api_urls")),
    path("", include("turnos.urls")),
]
