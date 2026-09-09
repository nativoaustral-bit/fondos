from django.db import models
from .entidad import Entidad, EstadoEditorial


class CoberturaTerritorial(models.TextChoices):
    NACIONAL = 'nacional', 'Nacional'
    REGIONAL = 'regional', 'Regional'
    COMUNAL = 'comunal', 'Comunal'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class FormalizacionRequerida(models.TextChoices):
    CUALQUIERA = 'cualquiera', 'Cualquiera (con o sin formalización)'
    FORMALIZACION_DECLARADA = 'formalizacion_declarada', 'Formalización declarada'
    SIN_INICIO_PRIMERA = 'sin_inicio_primera', 'Sin inicio de actividades en 1ª categoría'
    CON_INICIO_PRIMERA = 'con_inicio_primera', 'Con inicio de actividades en 1ª categoría'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class TipoBeneficio(models.TextChoices):
    SUBSIDIO = 'subsidio', 'Subsidio'
    PREMIO = 'premio', 'Premio'
    BONIFICACION = 'bonificacion', 'Bonificación'
    VOUCHER = 'voucher', 'Voucher / Vale'
    EN_ESPECIE = 'en_especie', 'En especie / Bienes o servicios'
    BECA = 'beca', 'Beca'


class NoReembolsableConfirmado(models.TextChoices):
    SI = 'si', 'Sí'
    NO = 'no', 'No'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class ModalidadEntrega(models.TextChoices):
    ANTICIPO = 'anticipo', 'Anticipo'
    CONTRA_GASTOS = 'contra_gastos', 'Contra rendición de gastos'
    EN_ESPECIE = 'en_especie', 'En especie / Bienes o servicios directos'
    MIXTA = 'mixta', 'Mixta'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class Moneda(models.TextChoices):
    CLP = 'CLP', 'Pesos Chilenos (CLP)'
    UF = 'UF', 'Unidades de Fomento (UF)'
    UTM = 'UTM', 'Unidades Tributarias Mensuales (UTM)'


class AporteBase(models.TextChoices):
    SUBSIDIO = 'subsidio', 'Porcentaje del subsidio'
    COSTO_TOTAL = 'costo_total', 'Porcentaje del costo total del proyecto'
    POR_CONFIRMAR = 'por_confirmar', 'Por confirmar'


class Instrumento(models.Model):
    """
    Programa o fondo de apoyo general (ej. INS-001 Emprendamos Semilla, INS-008 Capital Semilla).
    Define condiciones de referencia, público, qué financia y criterios base.
    """
    instrumento_id = models.CharField(
        max_length=64,
        primary_key=True,
        help_text='Identificador único e inmutable del instrumento'
    )
    entidad = models.ForeignKey(
        Entidad,
        on_delete=models.PROTECT,
        related_name='instrumentos',
        verbose_name='Entidad administradora'
    )
    nombre = models.CharField(max_length=255, verbose_name='Nombre del instrumento')
    estado_editorial = models.CharField(
        max_length=20,
        choices=EstadoEditorial.choices,
        default=EstadoEditorial.BORRADOR,
        verbose_name='Estado editorial'
    )

    # Explicación
    resumen = models.TextField(blank=True, default='', verbose_name='Resumen')
    dirigido_a = models.TextField(blank=True, default='', verbose_name='Para quién es')
    que_financia = models.TextField(blank=True, default='', verbose_name='Qué financia')
    que_no_financia = models.TextField(blank=True, default='', verbose_name='Qué no financia / Exclusiones')
    requisitos_principales = models.TextField(blank=True, default='', verbose_name='Requisitos clave')
    siguiente_paso = models.TextField(blank=True, default='', verbose_name='Siguiente paso sugerido')

    # Criterios de orientación (códigos separados por punto y coma, o 'todos')
    necesidades = models.TextField(
        default='todos',
        help_text='Códigos de necesidades cubiertas separados por punto y coma (ej. equipamiento;capital_trabajo) o "todos"'
    )
    situaciones = models.TextField(
        default='todos',
        help_text='Códigos de situaciones aplicables (ej. idea;prototipo;ventas_informales;ventas_formales) o "todos"'
    )
    rubros = models.TextField(
        default='todos',
        help_text='Códigos de rubros aplicables (ej. alimentos;turismo;comercio) o "todos"'
    )
    cobertura = models.CharField(
        max_length=32,
        choices=CoberturaTerritorial.choices,
        default=CoberturaTerritorial.NACIONAL,
        verbose_name='Cobertura territorial'
    )
    regiones = models.TextField(
        default='todos',
        help_text='Códigos de regiones aplicables (ej. CL-LR;CL-LL;CL-AI;CL-MA) o "todos"'
    )
    comunas = models.TextField(
        blank=True,
        default='',
        help_text='Comunas específicas si la cobertura es comunal'
    )
    formalizacion_requerida = models.CharField(
        max_length=32,
        choices=FormalizacionRequerida.choices,
        default=FormalizacionRequerida.CUALQUIERA,
        verbose_name='Formalización requerida'
    )

    # Beneficio
    tipo_beneficio = models.CharField(
        max_length=32,
        choices=TipoBeneficio.choices,
        default=TipoBeneficio.SUBSIDIO,
        verbose_name='Tipo de beneficio'
    )
    no_reembolsable_confirmado = models.CharField(
        max_length=20,
        choices=NoReembolsableConfirmado.choices,
        default=NoReembolsableConfirmado.POR_CONFIRMAR,
        verbose_name='No reembolsable confirmado'
    )
    modalidad_entrega = models.CharField(
        max_length=32,
        choices=ModalidadEntrega.choices,
        default=ModalidadEntrega.POR_CONFIRMAR,
        verbose_name='Modalidad de entrega'
    )

    # Montos de referencia
    monto_min = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto mínimo'
    )
    monto_max = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto máximo'
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
        verbose_name='Condiciones del monto'
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

    # Evidencia y fechas de verificación independientes
    url_programa = models.URLField(max_length=500, blank=True, default='', verbose_name='URL oficial del programa')
    requisitos_verificado_en = models.DateTimeField(null=True, blank=True, verbose_name='Requisitos verificados en')
    montos_verificado_en = models.DateTimeField(null=True, blank=True, verbose_name='Montos verificados en')
    cobertura_verificado_en = models.DateTimeField(null=True, blank=True, verbose_name='Cobertura verificada en')
    evidencia_verificacion = models.TextField(blank=True, default='', verbose_name='Evidencia / Notas de verificación')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Instrumento'
        verbose_name_plural = 'Instrumentos'
        ordering = ['entidad', 'nombre']

    def __str__(self):
        return f"{self.nombre} — {self.entidad.nombre} ({self.instrumento_id})"

    def get_necesidades_list(self):
        if not self.necesidades or self.necesidades == 'todos':
            return ['todos']
        return [n.strip() for n in self.necesidades.split(';') if n.strip()]

    def get_situaciones_list(self):
        if not self.situaciones or self.situaciones == 'todos':
            return ['todos']
        return [s.strip() for s in self.situaciones.split(';') if s.strip()]

    def get_rubros_list(self):
        if not self.rubros or self.rubros == 'todos':
            return ['todos']
        return [r.strip() for r in self.rubros.split(';') if r.strip()]

    def get_regiones_list(self):
        if not self.regiones or self.regiones == 'todos':
            return ['todos']
        return [reg.strip() for reg in self.regiones.split(';') if reg.strip()]
