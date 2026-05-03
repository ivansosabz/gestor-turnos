"""Configuración del admin de Django para los modelos de turnos.

Registramos los 4 modelos para poder inspeccionar/modificar datos sin
escribir SQL ni un management command. Útil para depuración.
"""
from django.contrib import admin

from .models import CicloConfig, CicloOrden, Cuidador, TurnoReal


@admin.register(Cuidador)
class CuidadorAdmin(admin.ModelAdmin):
    """Listado de cuidadores en el admin."""

    # Columnas visibles en la lista.
    list_display = ("nombre", "color", "activo")
    # Filtros laterales.
    list_filter = ("activo",)
    # Buscador por nombre.
    search_fields = ("nombre",)


class CicloOrdenInline(admin.TabularInline):
    """Permite editar las CicloOrden directamente dentro del CicloConfig.

    Usa la representación tabular (filas) en vez de stacked (vertical).
    """

    model = CicloOrden
    extra = 0  # No mostrar filas vacías por defecto.


@admin.register(CicloConfig)
class CicloConfigAdmin(admin.ModelAdmin):
    """Listado de ciclos. Edita las posiciones inline."""

    list_display = ("intervalo_dias", "fecha_inicio", "activo", "created_at")
    list_filter = ("activo",)
    inlines = [CicloOrdenInline]


@admin.register(CicloOrden)
class CicloOrdenAdmin(admin.ModelAdmin):
    """Vista directa de órdenes (raramente se usa: mejor desde CicloConfig)."""

    list_display = ("ciclo", "posicion", "cuidador")
    list_filter = ("ciclo",)


@admin.register(TurnoReal)
class TurnoRealAdmin(admin.ModelAdmin):
    """Listado de turnos reales registrados."""

    list_display = ("fecha", "responsable", "turno_original", "tipo", "created_at")
    list_filter = ("tipo", "responsable")
    search_fields = ("notas",)
    # Navegación rápida por años/meses arriba del listado.
    date_hierarchy = "fecha"
