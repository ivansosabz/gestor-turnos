"""Rutas de las vistas HTML (Function-Based Views).

Estas URLs se montan en la raíz del proyecto (ver no_me_olvido/urls.py),
así que coinciden directamente con lo que se ve en la barra del navegador.
"""
from django.urls import path

from . import views

urlpatterns = [
    # Pantalla principal: calendario interactivo.
    path("", views.index, name="index"),

    # Formulario para registrar quién durmió una noche.
    path("registrar/", views.registrar, name="registrar"),

    # Vista pública de solo lectura (para Papá y Tío).
    path("compartir/", views.compartir, name="compartir"),

    # Configuración del ciclo (intervalo + orden de cuidadores).
    path("config/", views.config, name="config"),
]
