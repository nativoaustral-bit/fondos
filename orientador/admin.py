from django.contrib import admin
from .models import (
    Entidad, Instrumento, Convocatoria, ConfiguracionGlobal,
    FormularioConfig, PreguntaConfig, OpcionConfig,
    SolicitudApoyo, ImportacionLote, MetricaEvento
)


@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ('entidad_id', 'nombre', 'tipo', 'estado_editorial', 'created_at')
    list_filter = ('tipo', 'estado_editorial')
    search_fields = ('entidad_id', 'nombre')


class ConvocatoriaInline(admin.TabularInline):
    model = Convocatoria
    extra = 0
    fields = ('convocatoria_id', 'nombre', 'estado_fuente', 'fecha_cierre', 'estado_editorial')


@admin.register(Instrumento)
class InstrumentoAdmin(admin.ModelAdmin):
    list_display = ('instrumento_id', 'nombre', 'entidad', 'tipo_beneficio', 'monto_max', 'estado_editorial')
    list_filter = ('estado_editorial', 'tipo_beneficio', 'cobertura', 'formalizacion_requerida', 'entidad')
    search_fields = ('instrumento_id', 'nombre', 'que_financia')
    inlines = [ConvocatoriaInline]


@admin.register(Convocatoria)
class ConvocatoriaAdmin(admin.ModelAdmin):
    list_display = ('convocatoria_id', 'nombre', 'instrumento', 'estado_fuente', 'fecha_cierre', 'estado_editorial')
    list_filter = ('estado_fuente', 'estado_editorial', 'cierre_modalidad')
    search_fields = ('convocatoria_id', 'nombre', 'instrumento__nombre')


@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    list_display = ('nombre_plataforma', 'version_catalogo', 'dias_revision_abierta', 'dias_revision_instrumento')


class OpcionConfigInline(admin.TabularInline):
    model = OpcionConfig
    extra = 0
    ordering = ('orden',)


@admin.register(PreguntaConfig)
class PreguntaConfigAdmin(admin.ModelAdmin):
    list_display = ('orden', 'titulo', 'clave', 'tipo', 'activa')
    list_filter = ('activa', 'formulario')
    ordering = ('orden',)
    inlines = [OpcionConfigInline]


@admin.register(FormularioConfig)
class FormularioConfigAdmin(admin.ModelAdmin):
    list_display = ('version', 'nombre', 'es_activa', 'created_at')
    list_filter = ('es_activa',)


@admin.register(SolicitudApoyo)
class SolicitudApoyoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'canal_contacto', 'contacto_valor', 'estado', 'created_at')
    list_filter = ('estado', 'canal_contacto')
    search_fields = ('nombre', 'contacto_valor', 'mensaje')
    readonly_fields = ('hash_idempotencia', 'created_at')


@admin.register(ImportacionLote)
class ImportacionLoteAdmin(admin.ModelAdmin):
    list_display = ('lote_id', 'archivo_nombre', 'usuario_responsable', 'version_base_anterior', 'version_base_nueva', 'estado', 'created_at')
    list_filter = ('estado',)
    readonly_fields = ('lote_id', 'archivo_hash', 'created_at')


@admin.register(MetricaEvento)
class MetricaEventoAdmin(admin.ModelAdmin):
    list_display = ('tipo_evento', 'datos', 'created_at')
    list_filter = ('tipo_evento',)
    readonly_fields = ('created_at',)
