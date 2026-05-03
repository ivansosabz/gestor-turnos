"""Vistas de la app turnos.

TODAS las vistas son Function-Based Views (FBV):
- Las vistas HTML son funciones decoradas con @ensure_csrf_cookie.
- Las vistas API son funciones decoradas con @api_view de DRF.

La lógica pesada vive en services.py — estas vistas se limitan a:
1. Parsear / validar la entrada.
2. Llamar al service correspondiente.
3. Devolver una respuesta (HTML render o JSON Response).
"""
from datetime import date

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import services
from .models import Cuidador
from .serializers import (
    CicloConfigSerializer,
    CrearCicloSerializer,
    CuidadorSerializer,
    RegistrarTurnoSerializer,
    TurnoRealSerializer,
)


# ===========================================================================
# Vistas HTML (Function-Based)
# ===========================================================================
#
# @ensure_csrf_cookie fuerza a Django a setear la cookie csrftoken en la
# respuesta, así el JS del cliente puede leerla y enviarla en el header
# X-CSRFToken al hacer POSTs contra la API.

@ensure_csrf_cookie
def index(request):
    """Página principal: calendario interactivo del mes actual."""
    # No pasamos datos en el contexto: el JS del template hace fetch a la API.
    return render(request, "index.html")


@ensure_csrf_cookie
def registrar(request):
    """Formulario para registrar quién durmió una noche.

    Acepta el query param ?fecha=YYYY-MM-DD para prellenar el input
    cuando el usuario llega aquí haciendo click en un día del calendario.
    """
    cuidadores = Cuidador.objects.filter(activo=True).order_by("nombre")
    fecha_pre = request.GET.get("fecha", "")
    return render(
        request,
        "registrar.html",
        {"cuidadores": cuidadores, "fecha_pre": fecha_pre},
    )


def compartir(request):
    """Vista de SOLO LECTURA para compartir con familiares.

    No tiene navbar ni interacciones — solo muestra el calendario.
    Como no hay POSTs desde aquí, no necesita @ensure_csrf_cookie.
    """
    return render(request, "compartir.html")


@ensure_csrf_cookie
def config(request):
    """Pantalla para configurar el ciclo (intervalo y orden de cuidadores)."""
    cuidadores = Cuidador.objects.filter(activo=True).order_by("nombre")
    # Pasamos el ciclo activo serializado para mostrarlo "en vivo".
    ciclo = services.get_ciclo_activo()
    ciclo_data = CicloConfigSerializer(ciclo).data if ciclo else None
    return render(
        request,
        "config.html",
        {"cuidadores": cuidadores, "ciclo": ciclo_data},
    )


# ===========================================================================
# Vistas API (Function-Based con @api_view de DRF)
# ===========================================================================

@api_view(["GET"])
def api_calendario(request):
    """GET /api/calendario/?año=YYYY&mes=M

    Devuelve la lista de días del mes con la información necesaria para
    pintar el calendario (ver services.get_calendario).

    Si faltan los parámetros, usa el mes actual.
    """
    hoy = date.today()
    try:
        # Aceptamos tanto "año" (con ñ, como en la spec) como "anio" (ASCII)
        # por comodidad si alguien arma la URL a mano.
        anio = int(request.GET.get("año", request.GET.get("anio", hoy.year)))
        mes = int(request.GET.get("mes", hoy.month))
    except (TypeError, ValueError):
        return Response(
            {"detail": "Parámetros año/mes inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not 1 <= mes <= 12:
        return Response(
            {"detail": "El mes debe estar entre 1 y 12."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Delegamos al service. Devuelve una lista de dicts ya lista para JSON.
    return Response(services.get_calendario(anio, mes))


@api_view(["GET"])
def api_cuidadores(request):
    """GET /api/cuidadores/

    Lista los cuidadores activos. El frontend la usa para construir la
    leyenda del calendario y los selects del form de registrar.
    """
    cuidadores = Cuidador.objects.filter(activo=True).order_by("nombre")
    return Response(CuidadorSerializer(cuidadores, many=True).data)


@api_view(["POST"])
def api_registrar_turno(request):
    """POST /api/turnos/registrar/

    Body JSON:
        {
            "fecha": "YYYY-MM-DD",
            "responsable_id": int,
            "turno_original_id": int,
            "tipo": "normal" | "cobertura" | "intercambio",
            "notas": "..."  (opcional)
        }
    """
    # El serializer valida tipos y formato; lanza 400 si está mal.
    serializer = RegistrarTurnoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        turno = services.registrar_turno(
            fecha=data["fecha"],
            responsable_id=data["responsable_id"],
            turno_original_id=data["turno_original_id"],
            tipo=data["tipo"],
            notas=data.get("notas", ""),
        )
    except Cuidador.DoesNotExist:
        # No debería ocurrir con los IDs validados, pero por seguridad.
        return Response(
            {"detail": "Cuidador no encontrado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        TurnoRealSerializer(turno).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def api_ciclo_activo(request):
    """GET /api/ciclo/activo/

    Devuelve el ciclo actualmente activo con su orden de cuidadores.
    Si no hay ninguno, responde 404.
    """
    ciclo = services.get_ciclo_activo()
    if ciclo is None:
        return Response(
            {"detail": "No hay ciclo activo."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(CicloConfigSerializer(ciclo).data)


@api_view(["POST"])
def api_crear_ciclo(request):
    """POST /api/ciclo/crear/

    Body JSON:
        {
            "intervalo_dias": int (>=1),
            "fecha_inicio": "YYYY-MM-DD",
            "cuidadores_ordenados": [id, id, id]  (al menos 1)
        }

    Crea un nuevo ciclo activo y desactiva el anterior automáticamente.
    """
    serializer = CrearCicloSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        ciclo = services.crear_ciclo(
            intervalo_dias=data["intervalo_dias"],
            fecha_inicio=data["fecha_inicio"],
            cuidadores_ordenados=data["cuidadores_ordenados"],
        )
    except ValueError as exc:
        # Errores controlados del service (ej: cuidadores inexistentes).
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        CicloConfigSerializer(ciclo).data, status=status.HTTP_201_CREATED
    )
