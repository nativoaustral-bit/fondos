import hashlib
from django.db import models


class EstadoSolicitud(models.TextChoices):
    NUEVA = 'nueva', 'Nueva'
    EN_ATENCION = 'en_atencion', 'En atención'
    RESUELTA = 'resuelta', 'Resuelta'


class SolicitudApoyo(models.Model):
    """
    Solicitud voluntaria de apoyo enviada por el emprendedor tras consultar resultados.
    """
    nombre = models.CharField(max_length=150, verbose_name='Nombre o cómo te llamas')
    canal_contacto = models.CharField(
        max_length=20,
        choices=[('email', 'Correo electrónico'), ('whatsapp', 'WhatsApp')],
        verbose_name='Canal de contacto preferido'
    )
    contacto_valor = models.CharField(
        max_length=150,
        verbose_name='Dato de contacto (correo o teléfono)'
    )
    mensaje = models.TextField(
        blank=True,
        default='',
        verbose_name='Mensaje o duda específica (opcional)'
    )
    autorizacion_contacto = models.BooleanField(
        default=False,
        verbose_name='Autorizo a Comunidad Humm a contactarme para responder esta solicitud'
    )
    respuestas_perfil = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Respuestas del formulario (adjuntas voluntariamente)'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.NUEVA,
        verbose_name='Estado de gestión'
    )
    hash_idempotencia = models.CharField(
        max_length=64,
        unique=True,
        help_text='Hash sha256 para evitar duplicados por doble pulsación'
    )
    notas_admin = models.TextField(
        blank=True,
        default='',
        verbose_name='Notas internas de atención'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud de Apoyo'
        verbose_name_plural = 'Solicitudes de Apoyo'
        ordering = ['-created_at']

    def __str__(self):
        return f"Solicitud de {self.nombre} ({self.get_canal_contacto_display()}) — {self.get_estado_display()}"

    @classmethod
    def generar_hash(cls, nombre, canal, valor, mensaje=''):
        raw = f"{nombre.strip().lower()}|{canal.strip().lower()}|{valor.strip().lower()}|{mensaje.strip().lower()}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
