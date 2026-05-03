"""Modelos de la app turnos.

Hay 4 modelos:

- Cuidador: cada persona que puede dormir con la abuela.
- CicloConfig: configuración del ciclo de rotación (intervalo + fecha de inicio).
  Solo puede haber UNO activo a la vez.
- CicloOrden: dentro de un ciclo, en qué posición (0, 1, 2...) va cada cuidador.
- TurnoReal: si la realidad fue distinta al ciclo (cobertura/intercambio) o
  para confirmar explícitamente quién durmió esa noche.
"""
from django.db import models, transaction


class Cuidador(models.Model):
    """Una persona que puede dormir con la abuela."""

    # Nombre visible (se usa para mostrar en el calendario y en los selects).
    nombre = models.CharField(max_length=100)

    # Color hexadecimal con el que se pintará su día en el calendario.
    # Formato esperado: "#RRGGBB" (ej. "#0d6efd").
    color = models.CharField(max_length=7, default="#000000")

    # Si está en False, no aparece en los selects ni en la rotación.
    # No borramos cuidadores para preservar el historial de TurnoReal.
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CicloConfig(models.Model):
    """Configuración del ciclo de rotación de turnos.

    Solo puede haber un ciclo con activo=True a la vez. Cuando se guarda
    uno nuevo activo, el método save() desactiva los anteriores
    automáticamente.
    """

    # Cuántos días seguidos duerme la misma persona antes de pasar al siguiente.
    # Con 3 cuidadores e intervalo=1 la rotación es diaria (Yo→Papá→Tío→Yo...).
    # Con intervalo=2 cada uno duerme 2 noches seguidas (YoYo→PapáPapá→TíoTío...).
    intervalo_dias = models.PositiveIntegerField()

    # Fecha desde la que se empieza a contar el ciclo. La rotación se
    # calcula como (fecha_actual - fecha_inicio) // intervalo_dias.
    fecha_inicio = models.DateField()

    # Marca cuál es el ciclo vigente. Solo uno puede estar activo.
    activo = models.BooleanField(default=True)

    # Sirve para ordenar los ciclos en /admin/ y para auditoría.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Más recientes primero (útil al listar en /admin/).
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ciclo cada {self.intervalo_dias} día(s) desde {self.fecha_inicio}"

    def save(self, *args, **kwargs):
        """Garantiza que solo haya un CicloConfig con activo=True.

        Si este ciclo se guarda como activo, marcamos como inactivos a
        todos los demás dentro de la misma transacción. Si se guarda
        como inactivo, no tocamos a los demás.
        """
        with transaction.atomic():
            if self.activo:
                # Excluimos el propio pk (puede ser None si recién se crea, en
                # cuyo caso el exclude no afecta).
                CicloConfig.objects.exclude(pk=self.pk).filter(activo=True).update(
                    activo=False
                )
            super().save(*args, **kwargs)


class CicloOrden(models.Model):
    """Posición de un cuidador dentro de un CicloConfig.

    Por ejemplo, dentro del ciclo activo:
        posicion=0 → Yo
        posicion=1 → Papá
        posicion=2 → Tío
    """

    # Ciclo al que pertenece esta posición. Si se borra el ciclo,
    # también se borran sus órdenes (CASCADE).
    ciclo = models.ForeignKey(
        CicloConfig, on_delete=models.CASCADE, related_name="ordenes"
    )

    # Cuidador que ocupa esta posición. PROTECT evita borrar un cuidador
    # que ya esté en uso en algún ciclo (mejor desactivarlo).
    cuidador = models.ForeignKey(Cuidador, on_delete=models.PROTECT)

    # Posición empezando en 0. Determina el orden de la rotación.
    posicion = models.PositiveIntegerField()

    class Meta:
        # No puede haber dos cuidadores en la misma posición del mismo ciclo.
        unique_together = ("ciclo", "posicion")
        # Por defecto los traemos ordenados por posición.
        ordering = ["posicion"]

    def __str__(self):
        return f"{self.posicion}: {self.cuidador.nombre}"


class TurnoReal(models.Model):
    """Registro de lo que pasó realmente una noche.

    El calendario "del ciclo" es teórico. Cada vez que la realidad difiere
    (porque hubo cobertura o intercambio), o cuando simplemente se quiere
    dejar registrado que el turno se cumplió, se crea un TurnoReal.

    Constraint clave: fecha es UNIQUE → como mucho un registro por día.
    """

    # Tipos posibles de turno. Almacenamos el código en la DB y mostramos
    # el label legible en el admin/forms.
    TIPO_CHOICES = [
        ("normal", "Normal"),            # Durmió quien le tocaba
        ("cobertura", "Cobertura"),      # Otra persona cubrió esta noche
        ("intercambio", "Intercambio"),  # Cambio de turno acordado
    ]

    # Fecha del turno. Unique → solo puede haber un registro por día.
    # Si se intenta crear otro para la misma fecha, se debe usar
    # update_or_create (lo hace el service registrar_turno()).
    fecha = models.DateField(unique=True)

    # Persona que efectivamente durmió esa noche.
    responsable = models.ForeignKey(
        Cuidador, on_delete=models.PROTECT, related_name="turnos_realizados"
    )

    # Persona a la que le correspondía dormir según el ciclo.
    # En tipo="normal" suele coincidir con responsable.
    turno_original = models.ForeignKey(
        Cuidador, on_delete=models.PROTECT, related_name="turnos_originales"
    )

    # Tipo de turno (ver TIPO_CHOICES).
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="normal")

    # Notas libres ("estaba enfermo", "cambio por cumpleaños", etc.).
    notas = models.TextField(blank=True)

    # Cuándo se registró este turno (auditoría).
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Más recientes primero al listar.
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.responsable.nombre} ({self.tipo})"
