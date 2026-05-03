"""Rutas de la API REST (también Function-Based Views, decoradas con @api_view).

Estas URLs se montan bajo /api/ (ver no_me_olvido/urls.py).
"""
from django.urls import path

from . import views

urlpatterns = [
    # GET /api/calendario/?año=YYYY&mes=M → días del mes con cuidador.
    path("calendario/", views.api_calendario, name="api_calendario"),

    # GET /api/cuidadores/ → lista de cuidadores activos.
    path("cuidadores/", views.api_cuidadores, name="api_cuidadores"),

    # POST /api/turnos/registrar/ → crea o actualiza un TurnoReal.
    path("turnos/registrar/", views.api_registrar_turno, name="api_registrar_turno"),

    # GET /api/ciclo/activo/ → ciclo vigente (404 si no hay).
    path("ciclo/activo/", views.api_ciclo_activo, name="api_ciclo_activo"),

    # POST /api/ciclo/crear/ → crea un nuevo ciclo activo.
    path("ciclo/crear/", views.api_crear_ciclo, name="api_crear_ciclo"),
]
