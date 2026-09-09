from django.db import models
from django.core.exceptions import ValidationError


class CanalContacto(models.TextChoices):
    NINGUNO = 'ninguno', 'Deshabilitado'
    EMAIL = 'email', 'Solo Correo'
    WHATSAPP = 'whatsapp', 'Solo WhatsApp'
    AMBOS = 'ambos', 'Correo y WhatsApp'


class ConfiguracionGlobal(models.Model):
    """
    Configuración global de la plataforma Humm Financiamiento (Singleton).
    """
    nombre_plataforma = models.CharField(
        max_length=100,
        default='Humm Financiamiento',
        verbose_name='Nombre visible de la plataforma'
    )
    url_comunidad = models.URLField(
        max_length=500,
        default='https://comunidad.humm.cl',
        verbose_name='URL principal Comunidad Humm'
    )
    url_retorno_comunidad = models.URLField(
        max_length=500,
        default='https://comunidad.humm.cl',
        verbose_name='URL de retorno (botón volver)'
    )
    contacto_email = models.EmailField(
        default='contacto@humm.cl',
        verbose_name='Correo de contacto'
    )
    contacto_whatsapp = models.CharField(
        max_length=30,
        default='+56912345678',
        verbose_name='WhatsApp de contacto (con código país)'
    )
    canal_activo = models.CharField(
        max_length=20,
        choices=CanalContacto.choices,
        default=CanalContacto.AMBOS,
        verbose_name='Canal de contacto activo'
    )
    politica_privacidad_url = models.CharField(
        max_length=255,
        default='/privacidad/',
        verbose_name='URL de política de privacidad'
    )
    dias_revision_abierta = models.PositiveIntegerField(
        default=7,
        help_text='Días máximos recomendados para revisar una convocatoria abierta (regla Humm)'
    )
    dias_revision_instrumento = models.PositiveIntegerField(
        default=90,
        help_text='Días máximos recomendados para revisar la información del instrumento (regla Humm)'
    )
    version_catalogo = models.PositiveIntegerField(
        default=1,
        help_text='Versión secuencial del catálogo de datos'
    )

    class Meta:
        verbose_name = 'Configuración Global'
        verbose_name_plural = 'Configuración Global'

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton pattern
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"{self.nombre_plataforma} (Catálogo v{self.version_catalogo})"


class TipoPregunta(models.TextChoices):
    RADIO = 'radio', 'Selección única (radio buttons)'
    CHECKBOX_LIMIT = 'checkbox_limit', 'Selección múltiple con límite'
    SELECT = 'select', 'Selector desplegable accesible (select)'


class FormularioConfig(models.Model):
    """
    Versión del formulario de 5 preguntas.
    Permite borradores, publicación y recuperación de versiones anteriores.
    """
    version = models.PositiveIntegerField(unique=True, verbose_name='Versión')
    es_activa = models.BooleanField(default=False, verbose_name='¿Es la versión activa?')
    nombre = models.CharField(max_length=100, default='Formulario estándar Humm')
    descripcion = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Versión de Formulario'
        verbose_name_plural = 'Versiones de Formulario'
        ordering = ['-version']

    def __str__(self):
        activo = " [ACTIVA]" if self.es_activa else ""
        return f"Formulario v{self.version} — {self.nombre}{activo}"

    def save(self, *args, **kwargs):
        if self.es_activa:
            FormularioConfig.objects.exclude(pk=self.pk).update(es_activa=False)
        super().save(*args, **kwargs)


class PreguntaConfig(models.Model):
    """
    Pregunta individual del formulario (máximo 5 activas por formulario).
    Claves estables: necesidades, situacion, region, monto_buscado, rubro.
    """
    formulario = models.ForeignKey(
        FormularioConfig,
        on_delete=models.CASCADE,
        related_name='preguntas'
    )
    clave = models.CharField(
        max_length=50,
        help_text='Clave interna estable (ej. necesidades, situacion, region, monto_buscado, rubro)'
    )
    titulo = models.CharField(max_length=255, verbose_name='Título visible de la pregunta')
    ayuda = models.TextField(blank=True, default='', verbose_name='Texto de ayuda o instrucción')
    tipo = models.CharField(
        max_length=30,
        choices=TipoPregunta.choices,
        default=TipoPregunta.RADIO
    )
    limite_seleccion = models.PositiveIntegerField(
        default=1,
        help_text='Límite de opciones para selección múltiple (ej. 2 para necesidades)'
    )
    orden = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Configuración de Pregunta'
        verbose_name_plural = 'Configuración de Preguntas'
        ordering = ['orden']
        unique_together = [('formulario', 'clave')]

    def __str__(self):
        return f"{self.orden}. {self.titulo} ({self.clave})"

    def clean(self):
        # Valida que no hayan más de 5 preguntas activas en el mismo formulario
        if self.activa:
            activas = PreguntaConfig.objects.filter(
                formulario=self.formulario,
                activa=True
            ).exclude(pk=self.pk).count()
            if activas >= 5:
                raise ValidationError("No se permiten más de 5 preguntas activas en el formulario.")


class OpcionConfig(models.Model):
    """
    Opción individual de una pregunta con su código interno estable y etiqueta visible.
    """
    pregunta = models.ForeignKey(
        PreguntaConfig,
        on_delete=models.CASCADE,
        related_name='opciones'
    )
    codigo = models.CharField(max_length=64, help_text='Código interno estable (ej. equipamiento, idea, CL-LR)')
    etiqueta = models.CharField(max_length=255, verbose_name='Etiqueta visible')
    descripcion_auxiliar = models.TextField(blank=True, default='', verbose_name='Descripción auxiliar / ayuda')
    orden = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Opción de Pregunta'
        verbose_name_plural = 'Opciones de Preguntas'
        ordering = ['orden']
        unique_together = [('pregunta', 'codigo')]

    def __str__(self):
        return f"{self.etiqueta} ({self.codigo})"
