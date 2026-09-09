from django.db import models
from .instrumento import (
    Instrumento, EstadoEditorial, CoberturaTerritorial, FormalizacionRequerida,
    ModalidadEntrega, Moneda, AporteBase
)


class EstadoFuente(models.TextChoices):
    ANUNCIADA = 'anunciada', 'Anunciada'
    ABIERTA = 'abierta', 'Abierta'
    CERRADA = 'cerrada', 'Cerrada'
    SUSPENDIDA = 'suspendida', 'Suspendida'
    CANCELADA = 'cancelada', 'Cancelada'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class CierreModalidad(models.TextChoices):
    FECHA_DEFINIDA = 'fecha_definida', 'Fecha y hora definida'
    PERMANENTE = 'permanente', 'Ventanilla abierta / Permanente'
    HASTA_AGOTAR = 'hasta_agotar', 'Hasta agotar fondos'
    SIN_CONFIRMAR = 'sin_confirmar', 'Sin confirmar'


class Convocatoria(models.Model):
    """
    Llamado específico en el tiempo y territorio para un instrumento.
    Una convocatoria pertenece a un solo instrumento.
    Admite HEREDAR en campos descriptivos y criterios para tomar el valor del instrumento.
    """
    convocatoria_id = models.CharField(
        max_length=64,
        primary_key=True,
        help_text='Identificador único e inmutable de la convocatoria'
    )
    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.CASCADE,
        related_name='convocatorias',
        verbose_name='Instrumento base'
    )
    nombre = models.CharField(max_length=255, verbose_name='Nombre de la convocatoria')
    estado_editorial = models.CharField(
        max_length=20,
        choices=EstadoEditorial.choices,
        default=EstadoEditorial.BORRADOR,
        verbose_name='Estado editorial'
    )

    # Condiciones efectivas (pueden ser 'HEREDAR' para tomar del instrumento)
    dirigido_a = models.TextField(
        default='HEREDAR',
        verbose_name='Para quién es (efectivo)'
    )
    que_financia = models.TextField(
        default='HEREDAR',
        verbose_name='Qué financia (efectivo)'
    )
    que_no_financia = models.TextField(
        default='HEREDAR',
        verbose_name='Qué no financia / Exclusiones'
    )
    requisitos_principales = models.TextField(
        default='HEREDAR',
        verbose_name='Requisitos principales (efectivos)'
    )

    # Criterios específicos de esta convocatoria
    necesidades = models.TextField(
        default='HEREDAR',
        help_text='Códigos separados por punto y coma, "todos" o "HEREDAR"'
    )
    situaciones = models.TextField(
        default='HEREDAR',
        help_text='Códigos separados por punto y coma, "todos" o "HEREDAR"'
    )
    rubros = models.TextField(
        default='HEREDAR',
        help_text='Códigos separados por punto y coma, "todos" o "HEREDAR"'
    )
    cobertura = models.CharField(
        max_length=32,
        default='HEREDAR',
        verbose_name='Cobertura territorial (efectiva)'
    )
    regiones = models.TextField(
        default='HEREDAR',
        help_text='Códigos de regiones aplicables, "todos" o "HEREDAR"'
    )
    comunas = models.TextField(
        blank=True,
        default='',
        help_text='Comunas específicas si aplica'
    )
    formalizacion_requerida = models.CharField(
        max_length=32,
        default='HEREDAR',
        verbose_name='Formalización requerida (efectiva)'
    )

    # Beneficio y monto específico de la convocatoria
    modalidad_entrega = models.CharField(
        max_length=32,
        default='HEREDAR',
        verbose_name='Modalidad de entrega'
    )
    monto_min = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto mínimo efectivo'
    )
    monto_max = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto máximo efectivo'
    )
    moneda = models.CharField(
        max_length=10,
        choices=Moneda.choices,
        default=Moneda.CLP,
        verbose_name='Moneda'
    )
    monto_condiciones = models.TextField(
        blank=True,
        default='',
        verbose_name='Condiciones específicas del monto'
    )
    aporte_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='% aporte propio'
    )
    aporte_base = models.CharField(
        max_length=32,
        choices=AporteBase.choices,
        default=AporteBase.COSTO_TOTAL,
        verbose_name='Base del aporte propio'
    )
    aporte_descripcion = models.TextField(
        blank=True,
        default='',
        verbose_name='Descripción del aporte'
    )

    # Calendario y tiempo
    fecha_apertura = models.DateField(null=True, blank=True, verbose_name='Fecha de apertura')
    hora_apertura = models.TimeField(null=True, blank=True, verbose_name='Hora de apertura')
    fecha_cierre = models.DateField(null=True, blank=True, verbose_name='Fecha de cierre')
    hora_cierre = models.TimeField(null=True, blank=True, verbose_name='Hora de cierre')
    zona_horaria = models.CharField(
        max_length=64,
        default='America/Santiago',
        help_text='Zona horaria IANA (ej. America/Santiago, America/Punta_Arenas)'
    )
    cierre_modalidad = models.CharField(
        max_length=32,
        choices=CierreModalidad.choices,
        default=CierreModalidad.FECHA_DEFINIDA,
        verbose_name='Modalidad de cierre'
    )

    # Evidencia y estado observado en la fuente
    estado_fuente = models.CharField(
        max_length=20,
        choices=EstadoFuente.choices,
        default=EstadoFuente.POR_CONFIRMAR,
        verbose_name='Estado observado en la fuente'
    )
    url_convocatoria = models.URLField(max_length=500, blank=True, default='', verbose_name='URL de la convocatoria oficial')
    requisitos_verificado_en = models.DateTimeField(null=True, blank=True)
    montos_verificado_en = models.DateTimeField(null=True, blank=True)
    cobertura_verificado_en = models.DateTimeField(null=True, blank=True)
    fechas_verificado_en = models.DateTimeField(null=True, blank=True)
    estado_verificado_en = models.DateTimeField(null=True, blank=True)
    evidencia_verificacion = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Convocatoria'
        verbose_name_plural = 'Convocatorias'
        ordering = ['instrumento', '-fecha_cierre']

    def __str__(self):
        return f"{self.nombre} ({self.convocatoria_id})"

    # Resolved getters handling HEREDAR
    def get_effective_field(self, field_name):
        val = getattr(self, field_name)
        if val == 'HEREDAR' or val is None or val == '':
            return getattr(self.instrumento, field_name)
        return val

    def get_effective_necesidades(self):
        val = self.necesidades
        if val == 'HEREDAR' or not val:
            return self.instrumento.get_necesidades_list()
        if val == 'todos':
            return ['todos']
        return [n.strip() for n in val.split(';') if n.strip()]

    def get_effective_situaciones(self):
        val = self.situaciones
        if val == 'HEREDAR' or not val:
            return self.instrumento.get_situaciones_list()
        if val == 'todos':
            return ['todos']
        return [s.strip() for s in val.split(';') if s.strip()]

    def get_effective_rubros(self):
        val = self.rubros
        if val == 'HEREDAR' or not val:
            return self.instrumento.get_rubros_list()
        if val == 'todos':
            return ['todos']
        return [r.strip() for r in val.split(';') if r.strip()]

    def get_effective_regiones(self):
        val = self.regiones
        if val == 'HEREDAR' or not val:
            return self.instrumento.get_regiones_list()
        if val == 'todos':
            return ['todos']
        return [reg.strip() for reg in val.split(';') if reg.strip()]

    def get_effective_formalizacion(self):
        val = self.formalizacion_requerida
        if val == 'HEREDAR' or not val:
            return self.instrumento.formalizacion_requerida
        return val

    def get_effective_monto_min(self):
        if self.monto_min is not None:
            return self.monto_min
        return self.instrumento.monto_min

    def get_effective_monto_max(self):
        if self.monto_max is not None:
            return self.monto_max
        return self.instrumento.monto_max

    def get_effective_moneda(self):
        return self.moneda or self.instrumento.moneda
