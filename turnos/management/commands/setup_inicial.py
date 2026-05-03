"""Management command que carga datos iniciales de forma idempotente.

Uso:
    python manage.py setup_inicial

Crea los 3 cuidadores (Iván, Antonio, José) y un CicloConfig activo cuya
rotación es DIARIA (intervalo_dias=1): cada día le toca a la siguiente
persona del orden.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from turnos.models import CicloConfig, CicloOrden, Cuidador


# Lista de cuidadores que se crean si no existen.
# El ORDEN de esta lista determina la posición inicial en el ciclo
# (Iván=0 primero, Antonio=1 segundo, José=2 tercero).
CUIDADORES_INICIALES = [
    {"nombre": "Iván", "color": "#0d6efd"},
    {"nombre": "Antonio", "color": "#198754"},
    {"nombre": "José", "color": "#dc3545"},
]

# intervalo_dias = 1 → cada día rota al siguiente cuidador.
# Con 3 cuidadores eso da: día 0 Yo, día 1 Papá, día 2 Tío, día 3 Yo, ...
INTERVALO_DIAS_DEFAULT = 1


class Command(BaseCommand):
    """Comando idempotente: se puede ejecutar varias veces sin duplicar datos."""

    help = (
        "Crea los cuidadores iniciales (Iván, Antonio, José) y un ciclo activo "
        "con rotación diaria si todavía no existe ninguno activo."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        # ---- 1) Crear cuidadores que falten ----
        creados = []      # Nombres de los que recién se acaban de crear
        existentes = []   # Nombres de los que ya existían en la DB
        for data in CUIDADORES_INICIALES:
            # get_or_create es idempotente: si existe lo trae, si no lo crea.
            # Buscamos por nombre y, solo si lo creamos, asignamos el color
            # default (no pisamos colores que el usuario haya cambiado).
            cuidador, creado = Cuidador.objects.get_or_create(
                nombre=data["nombre"],
                defaults={"color": data["color"]},
            )
            (creados if creado else existentes).append(cuidador.nombre)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cuidadores creados: {creados or 'ninguno'}. "
                f"Ya existían: {existentes or 'ninguno'}."
            )
        )

        # ---- 2) Crear ciclo solo si no hay uno activo ----
        # Si ya hay un ciclo activo NO lo tocamos: respetamos cualquier cambio
        # que el usuario haya hecho desde /config/.
        if CicloConfig.objects.filter(activo=True).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Ya existe un ciclo activo. No se crea uno nuevo. "
                    "Si quieres reiniciarlo, créalo desde /config/."
                )
            )
            return

        # Creamos el ciclo activo. El método save() del modelo se encarga
        # de desactivar cualquier otro ciclo que estuviera marcado activo.
        ciclo = CicloConfig.objects.create(
            intervalo_dias=INTERVALO_DIAS_DEFAULT,
            fecha_inicio=date.today(),
            activo=True,
        )

        # Y asignamos las posiciones del ciclo en el orden de CUIDADORES_INICIALES.
        for posicion, data in enumerate(CUIDADORES_INICIALES):
            cuidador = Cuidador.objects.get(nombre=data["nombre"])
            CicloOrden.objects.create(
                ciclo=ciclo, cuidador=cuidador, posicion=posicion
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Ciclo creado: rota cada {ciclo.intervalo_dias} día(s) "
                f"desde {ciclo.fecha_inicio} con orden "
                f"{[d['nombre'] for d in CUIDADORES_INICIALES]}."
            )
        )
