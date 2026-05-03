"""Serializers de DRF.

Hay dos familias de serializers:

1. ModelSerializer: para CONVERTIR objetos del modelo a JSON al
   responder en la API (Cuidador, CicloConfig, TurnoReal).

2. Serializer "manual": para VALIDAR el body de los POST que no se
   mapean 1-a-1 a un modelo (RegistrarTurnoSerializer, CrearCicloSerializer).
"""
from rest_framework import serializers

from .models import CicloConfig, Cuidador, TurnoReal


# ---------------------------------------------------------------------------
# Serializers de salida (ModelSerializer)
# ---------------------------------------------------------------------------

class CuidadorSerializer(serializers.ModelSerializer):
    """JSON de un Cuidador (lo que ve el frontend)."""

    class Meta:
        model = Cuidador
        fields = ["id", "nombre", "color", "activo"]


class CicloConfigSerializer(serializers.ModelSerializer):
    """JSON de un CicloConfig + sus cuidadores ordenados.

    `cuidadores_ordenados` es un campo computado que devuelve la lista
    de órdenes con su cuidador anidado, en el orden correcto.
    """

    cuidadores_ordenados = serializers.SerializerMethodField()

    class Meta:
        model = CicloConfig
        fields = [
            "id",
            "intervalo_dias",
            "fecha_inicio",
            "activo",
            "cuidadores_ordenados",
        ]

    def get_cuidadores_ordenados(self, obj):
        """Devuelve la lista [{posicion, cuidador}, ...] en orden ascendente.

        Usamos select_related para traer el Cuidador en la misma query
        y evitar N+1.
        """
        ordenes = obj.ordenes.order_by("posicion").select_related("cuidador")
        return [
            {
                "posicion": o.posicion,
                "cuidador": CuidadorSerializer(o.cuidador).data,
            }
            for o in ordenes
        ]


class TurnoRealSerializer(serializers.ModelSerializer):
    """JSON de un TurnoReal con responsable/turno_original anidados.

    Devolvemos los Cuidadores como objetos completos (no solo IDs) para
    que el frontend pueda mostrar nombre y color sin un round-trip extra.
    """

    responsable = CuidadorSerializer(read_only=True)
    turno_original = CuidadorSerializer(read_only=True)

    class Meta:
        model = TurnoReal
        fields = [
            "id",
            "fecha",
            "responsable",
            "turno_original",
            "tipo",
            "notas",
            "created_at",
        ]


# ---------------------------------------------------------------------------
# Serializers de entrada (validación de POSTs)
# ---------------------------------------------------------------------------

class RegistrarTurnoSerializer(serializers.Serializer):
    """Valida el body de POST /api/turnos/registrar/.

    No es ModelSerializer porque queremos recibir los FKs como
    `responsable_id` y `turno_original_id` (IDs planos) en vez de objetos.
    """

    fecha = serializers.DateField()
    responsable_id = serializers.IntegerField()
    turno_original_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TurnoReal.TIPO_CHOICES)
    notas = serializers.CharField(required=False, allow_blank=True, default="")


class CrearCicloSerializer(serializers.Serializer):
    """Valida el body de POST /api/ciclo/crear/."""

    # min_value=1: no tiene sentido un intervalo de 0 días.
    intervalo_dias = serializers.IntegerField(min_value=1)
    fecha_inicio = serializers.DateField()
    # min_length=1: el ciclo no puede estar vacío.
    cuidadores_ordenados = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
