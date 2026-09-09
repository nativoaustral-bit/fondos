from django.db import models


class EstadoEditorial(models.TextChoices):
    BORRADOR = 'borrador', 'Borrador'
    PUBLICADO = 'publicado', 'Publicado'
    ARCHIVADO = 'archivado', 'Archivado'


class TipoEntidad(models.TextChoices):
    PUBLICA = 'publica', 'Pública'
    PRIVADA = 'privada', 'Privada'
    MIXTA = 'mixta', 'Mixta'
    REGIONAL = 'regional', 'Regional / Subnacional'
    OTRA = 'otra', 'Otra'


class Entidad(models.Model):
    """
    Institución o entidad que administra o entrega el financiamiento.
    Identificador estable e inmutable (ej. ENT-001, sercotec, corfo).
    """
    entidad_id = models.CharField(
        max_length=64,
        primary_key=True,
        help_text='Identificador único e inmutable de la entidad'
    )
    nombre = models.CharField(max_length=255, verbose_name='Nombre de la entidad')
    tipo = models.CharField(
        max_length=32,
        choices=TipoEntidad.choices,
        default=TipoEntidad.PUBLICA,
        verbose_name='Tipo de entidad'
    )
    url_oficial = models.URLField(max_length=500, verbose_name='URL oficial')
    estado_editorial = models.CharField(
        max_length=20,
        choices=EstadoEditorial.choices,
        default=EstadoEditorial.BORRADOR,
        verbose_name='Estado editorial'
    )
    poblacion_foco = models.TextField(blank=True, default='', verbose_name='Población foco')
    notas = models.TextField(blank=True, default='', verbose_name='Notas internas')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entidad'
        verbose_name_plural = 'Entidades'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.entidad_id})"
