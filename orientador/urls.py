from django.urls import path
from .views import public, admin_views

app_name = 'orientador'

urlpatterns = [
    # Rutas públicas (Orientador de Financiamiento)
    path('', public.formulario_view, name='formulario'),
    path('resultados/', public.procesar_consulta_view, name='procesar_consulta'),
    path('solicitar-apoyo/', public.solicitar_apoyo_view, name='solicitar_apoyo'),

    # Rutas administrativas Humm (Protegidas en servidor)
    path('gestion/login/', admin_views.admin_login_view, name='admin_login'),
    path('gestion/logout/', admin_views.admin_logout_view, name='admin_logout'),
    path('gestion/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('gestion/catalogo/', admin_views.admin_catalogo_list_view, name='admin_catalogo'),
    path('gestion/entidades/guardar/', admin_views.admin_entidad_guardar_view, name='admin_entidad_guardar'),
    path('gestion/instrumentos/guardar-estado/', admin_views.admin_instrumento_guardar_estado_view, name='admin_instrumento_guardar_estado'),
    path('gestion/convocatorias/guardar/', admin_views.admin_convocatoria_guardar_view, name='admin_convocatoria_guardar'),
    path('gestion/preguntas/', admin_views.admin_preguntas_editor_view, name='admin_preguntas'),
    path('gestion/importar-exportar/', admin_views.admin_import_export_view, name='admin_import_export'),
    path('gestion/descargar-plantilla/', admin_views.admin_descargar_plantilla_view, name='admin_plantilla'),
    path('gestion/exportar-base/', admin_views.admin_exportar_base_view, name='admin_exportar'),
    path('gestion/subir-excel/', admin_views.admin_subir_excel_view, name='admin_subir_excel'),
    path('gestion/confirmar-importacion/', admin_views.admin_confirmar_importacion_view, name='admin_confirmar_importacion'),
    path('gestion/revertir/<str:lote_id>/', admin_views.admin_revertir_lote_view, name='admin_revertir'),
    path('gestion/configuracion/', admin_views.admin_configuracion_view, name='admin_configuracion'),
]
