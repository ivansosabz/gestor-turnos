"""Lógica de negocio de los turnos.

Estas funciones son el "cerebro" de la app. Las vistas (HTML y API) se
limitan a parsear input, llamar a estas funciones y devolver la respuesta.

Esto permite reutilizar la misma lógica desde:
- las vistas function-based (views.py)
- el admin de Django
- management commands
- tests unitarios
"""
import calendar
from datetime import date, timedelta

from django.db import transaction

from .models import CicloConfig, CicloOrden, Cuidador, TurnoReal


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _serializar_cuidador(cuidador):
    """Convierte un Cuidador en un dict simple para enviar como JSON.

    Acepta None y devuelve None: así las vistas no se rompen si una fecha
    queda sin cuidador asignado (por ejemplo, fechas anteriores al inicio
    del ciclo).
    """
    if cuidador is None:
        return None
    return {
        "id": cuidador.id,
        "nombre": cuidador.nombre,
        "color": cuidador.color,
    }


def _cuidadores_ordenados(ciclo):
    """Devuelve la lista de Cuidadores del ciclo en orden por posición."""
    # order_by("posicion") asegura el orden incluso si el Meta del modelo cambia.
    return [orden.cuidador for orden in ciclo.ordenes.order_by("posicion")]


# ---------------------------------------------------------------------------
# Lectura del ciclo
# ---------------------------------------------------------------------------

def get_ciclo_activo():
    """Devuelve el CicloConfig actualmente activo, o None si no hay.

    Usa prefetch_related para evitar el problema N+1 cuando luego se
    iteren las órdenes.
    """
    return (
        CicloConfig.objects.filter(activo=True)
        .prefetch_related("ordenes__cuidador")
        .first()
    )


def calcular_turno_para_fecha(fecha, ciclo=None, cuidadores=None):
    """Calcula a qué Cuidador le toca la fecha indicada según el ciclo.

    Fórmula:
        dias_desde_inicio = (fecha - ciclo.fecha_inicio).days
        posicion = (dias_desde_inicio // intervalo_dias) % cantidad_cuidadores

    Ejemplo (3 cuidadores Yo/Papá/Tío, intervalo=1, inicio=2026-05-01):
        2026-05-01 → días=0 → pos=0 → Yo
        2026-05-02 → días=1 → pos=1 → Papá
        2026-05-03 → días=2 → pos=2 → Tío
        2026-05-04 → días=3 → pos=0 → Yo  (vuelve a empezar)

    Devuelve None si:
    - no hay ciclo activo
    - el ciclo no tiene cuidadores
    - la fecha es anterior a fecha_inicio (no extrapolamos hacia atrás)
    """
    # Permitimos pasar el ciclo y los cuidadores ya cargados para evitar
    # repetir queries cuando se llama en bucle (ver get_calendario).
    if ciclo is None:
        ciclo = get_ciclo_activo()
    if ciclo is None:
        return None
    if cuidadores is None:
        cuidadores = _cuidadores_ordenados(ciclo)
    if not cuidadores:
        return None

    dias = (fecha - ciclo.fecha_inicio).days
    if dias < 0:
        # Antes del inicio del ciclo no asignamos: el día queda "vacío".
        return None

    posicion = (dias // ciclo.intervalo_dias) % len(cuidadores)
    return cuidadores[posicion]


# ---------------------------------------------------------------------------
# Calendario
# ---------------------------------------------------------------------------

def get_calendario(anio, mes):
    """Devuelve la lista de días del mes con la info necesaria para pintar.

    Cada día es un dict con:
        fecha:           "YYYY-MM-DD"
        cuidador:        dict del cuidador efectivo (None si no hay ciclo)
        turno_original:  dict del cuidador que tocaba según el ciclo
        tipo:            "normal" | "cobertura" | "intercambio"
        es_turno_real:   True si hay registro en TurnoReal para esa fecha
        notas:           texto libre del TurnoReal (vacío si no hay)

    Si existe un TurnoReal para una fecha, ese registro PISA al cuidador
    teórico del ciclo: el día se pinta con el color de quien efectivamente
    durmió.
    """
    # Calcular primer y último día del mes.
    _, ultimo_dia = calendar.monthrange(anio, mes)
    primer_fecha = date(anio, mes, 1)
    ultima_fecha = date(anio, mes, ultimo_dia)

    # Cargar el ciclo activo y la lista de cuidadores UNA sola vez.
    ciclo = get_ciclo_activo()
    cuidadores = _cuidadores_ordenados(ciclo) if ciclo else []

    # Cargar TODOS los TurnoReal del mes en una sola query, indexados por fecha.
    # select_related para evitar N+1 al acceder responsable/turno_original.
    turnos_reales = {
        t.fecha: t
        for t in TurnoReal.objects.filter(
            fecha__gte=primer_fecha, fecha__lte=ultima_fecha
        ).select_related("responsable", "turno_original")
    }

    # Construir el resultado día por día.
    resultado = []
    fecha_actual = primer_fecha
    while fecha_actual <= ultima_fecha:
        # Cuidador "teórico" según el ciclo (puede ser None).
        cuidador_ciclo = calcular_turno_para_fecha(fecha_actual, ciclo, cuidadores)
        # ¿Hay un registro real para esta fecha?
        turno_real = turnos_reales.get(fecha_actual)

        if turno_real:
            # El registro real manda: usamos su responsable y su tipo.
            cuidador = turno_real.responsable
            tipo = turno_real.tipo
            es_turno_real = True
            turno_original = turno_real.turno_original
            notas = turno_real.notas
        else:
            # No hay registro: usamos lo que dicta el ciclo.
            cuidador = cuidador_ciclo
            tipo = "normal"
            es_turno_real = False
            turno_original = cuidador_ciclo
            notas = ""

        resultado.append(
            {
                "fecha": fecha_actual.isoformat(),
                "cuidador": _serializar_cuidador(cuidador),
                "turno_original": _serializar_cuidador(turno_original),
                "tipo": tipo,
                "es_turno_real": es_turno_real,
                "notas": notas,
            }
        )
        fecha_actual += timedelta(days=1)

    return resultado


# ---------------------------------------------------------------------------
# Mutaciones
# ---------------------------------------------------------------------------

def registrar_turno(fecha, responsable_id, turno_original_id, tipo, notas=""):
    """Crea o actualiza el TurnoReal correspondiente a una fecha.

    Como TurnoReal.fecha es UNIQUE, usamos update_or_create: si ya existe
    un registro para esa fecha lo pisamos con los nuevos datos.

    Args:
        fecha: date.
        responsable_id: id del Cuidador que durmió esa noche.
        turno_original_id: id del Cuidador a quien le tocaba según el ciclo.
        tipo: "normal" | "cobertura" | "intercambio".
        notas: texto libre.

    Returns:
        El TurnoReal creado o actualizado.
    """
    turno, _creado = TurnoReal.objects.update_or_create(
        fecha=fecha,
        defaults={
            "responsable_id": responsable_id,
            "turno_original_id": turno_original_id,
            "tipo": tipo,
            "notas": notas or "",  # nunca dejar None en notas
        },
    )
    return turno


@transaction.atomic
def crear_ciclo(intervalo_dias, fecha_inicio, cuidadores_ordenados):
    """Crea un nuevo CicloConfig activo con su orden de cuidadores.

    `cuidadores_ordenados` es una lista de IDs de Cuidador en el orden
    deseado. La posición 0 corresponde al primer ID, la 1 al segundo, etc.

    Esta función es atómica: o se crea todo (ciclo + sus órdenes), o nada.
    El save() del modelo CicloConfig se encarga de desactivar el ciclo
    activo anterior.
    """
    if not cuidadores_ordenados:
        raise ValueError("Se requiere al menos un cuidador en el ciclo")

    # Verificamos que TODOS los IDs existan (para no crear un ciclo con
    # FKs rotas a medias).
    ids_validos = set(
        Cuidador.objects.filter(id__in=cuidadores_ordenados).values_list(
            "id", flat=True
        )
    )
    faltantes = [cid for cid in cuidadores_ordenados if cid not in ids_validos]
    if faltantes:
        raise ValueError(f"Cuidadores inexistentes: {faltantes}")

    # Crear el ciclo (su save() desactivará los anteriores activos).
    ciclo = CicloConfig.objects.create(
        intervalo_dias=intervalo_dias,
        fecha_inicio=fecha_inicio,
        activo=True,
    )

    # Crear las órdenes preservando la posición que dio el caller.
    for posicion, cuidador_id in enumerate(cuidadores_ordenados):
        CicloOrden.objects.create(
            ciclo=ciclo, cuidador_id=cuidador_id, posicion=posicion
        )
    return ciclo
