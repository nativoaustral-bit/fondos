import uuid
from django.db import models


class EstadoLote(models.TextChoices):
    APLICADO = 'aplicado', 'Aplicado'
    REVERTIDO = 'revertido', 'Revertido'


class ImportacionLote(models.Model):
    """
    Registro histórico y de auditoría de cada actualización masiva mediante Excel.
    Permite visualizar diferencias y revertir cambios si no existen modificaciones posteriores.
    """
    lote_id = models.CharField(
        max_length=64,
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    archivo_nombre = models.CharField(max_length=255, verbose_name='Nombre del archivo')
    archivo_hash = models.CharField(max_length=64, verbose_name='Hash SHA-256 del archivo')
    usuario_responsable = models.CharField(max_length=150, verbose_name='Usuario responsable')
    version_base_anterior = models.PositiveIntegerField(verbose_name='Versión base anterior')
    version_base_nueva = models.PositiveIntegerField(verbose_name='Nueva versión de catálogo')
    resumen = models.TextField(verbose_name='Resumen de cambios aplicados')
    diferencias_json = models.JSONField(verbose_name='Detalle de diferencias (JSON)')
    estado = models.CharField(
        max_length=20,
        choices=EstadoLote.choices,
        default=EstadoLote.APLICADO,
        verbose_name='Estado del lote'
    )
    revertido_por = models.CharField(max_length=150, blank=True, default='')
    revertido_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lote de Importación'
        verbose_name_plural = 'Historial de Importaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"Lote {self.lote_id[:8]} (v{self.version_base_anterior} -> v{self.version_base_nueva}) — {self.archivo_nombre}"


class TipoMetrica(models.TextChoices):
    CONSULTA_INICIADA = 'consulta_iniciada', 'Consulta iniciada'
    CONSULTA_COMPLETADA = 'consulta_completada', 'Consulta completada'
    VISUALIZACION_FICHA = 'visualizacion_ficha', 'Visualización de ficha'
    CLIC_FUENTE_OFICIAL = 'clic_fuente_oficial', 'Clic en fuente oficial'
    CONSULTA_SIN_RESULTADOS = 'consulta_sin_resultados', 'Consulta sin resultados pertinentes'
    SOLICITUD_APOYO = 'solicitud_apoyo', 'Solicitud voluntaria de apoyo'


class MetricaEvento(models.Model):
    """
    Registro anónimo y agregado de eventos para medir adopción sin comprometer privacidad.
    No almacena IPs, cookies de seguimiento, RUT ni datos personales.
    """
    tipo_evento = models.CharField(
        max_length=40,
        choices=TipoMetrica.choices,
        verbose_name='Tipo de evento'
    )
    datos = models.JSONField(
        blank=True,
        default=dict,
        help_text='Datos no sensibles agregados (ej. region, duracion_segundos)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Métrica de Uso'
        verbose_name_plural = 'Métricas de Uso'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tipo_evento_display()} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"
