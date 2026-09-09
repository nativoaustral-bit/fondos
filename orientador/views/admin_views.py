import io
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q

from ..models import (
    Entidad, Instrumento, Convocatoria, ConfiguracionGlobal,
    FormularioConfig, PreguntaConfig, OpcionConfig, SolicitudApoyo,
    ImportacionLote, EstadoEditorial, EstadoFuente, MetricaEvento
)
from ..services.status_engine import (
    calcular_estado_convocatoria, evaluar_vigencia_instrumento, CodigoEstadoCalculado
)
from ..services.excel_contract import (
    generar_excel_catalogo, validar_y_previsualizar_excel,
    aplicar_actualizacion_excel, revertir_lote_importacion
)


def es_administrador(user):
    """Verifica si el usuario tiene rol de staff o superuser."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_dashboard_view(request):
    """
    Inicio de la administración: conteos clave, convocatorias que requieren revisión,
    registros incompletos y accesos rápidos a exportar/importar.
    """
    config = ConfiguracionGlobal.get_solo()
    total_entidades = Entidad.objects.count()
    total_instrumentos = Instrumento.objects.count()
    total_convocatorias = Convocatoria.objects.count()
    total_solicitudes = SolicitudApoyo.objects.count()
    solicitudes_nuevas = SolicitudApoyo.objects.filter(estado='nueva').count()

    # Evaluar convocatorias que requieren atención
    convocatorias = Convocatoria.objects.all().select_related('instrumento')
    requieren_atencion = []
    abiertas_activas = []
    
    for conv in convocatorias:
        calc = calcular_estado_convocatoria(conv, max_dias_abierta=config.dias_revision_abierta)
        if calc['requiere_atencion']:
            requieren_atencion.append({
                'convocatoria': conv,
                'estado': calc,
            })
        if calc['codigo'] in [CodigoEstadoCalculado.ABIERTA_VERIFICADA, CodigoEstadoCalculado.CIERRA_HOY_CONFIRMAR_HORA]:
            abiertas_activas.append({
                'convocatoria': conv,
                'estado': calc,
            })

    # Últimos lotes de importación
    ultimos_lotes = ImportacionLote.objects.all().order_by('-created_at')[:5]

    context = {
        'total_entidades': total_entidades,
        'total_instrumentos': total_instrumentos,
        'total_convocatorias': total_convocatorias,
        'total_solicitudes': total_solicitudes,
        'solicitudes_nuevas': solicitudes_nuevas,
        'requieren_atencion': requieren_atencion,
        'abiertas_activas': abiertas_activas,
        'ultimos_lotes': ultimos_lotes,
        'config': config,
    }
    return render(request, 'admin_humm/dashboard.html', context)


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_catalogo_list_view(request):
    """
    Catálogo: búsqueda, filtros y listado de entidades, instrumentos y convocatorias.
    """
    seccion = request.GET.get('seccion', 'instrumentos')
    query = request.GET.get('q', '').strip()

    entidades = []
    instrumentos = []
    convocatorias = []

    if seccion == 'entidades':
        qs = Entidad.objects.all().order_by('nombre')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(entidad_id__icontains=query))
        entidades = qs
    elif seccion == 'convocatorias':
        qs = Convocatoria.objects.all().select_related('instrumento', 'instrumento__entidad').order_by('-updated_at')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(convocatoria_id__icontains=query))
        convocatorias = [
            {'objeto': c, 'estado_calc': calcular_estado_convocatoria(c)}
            for c in qs
        ]
    else:
        # Por defecto instrumentos
        qs = Instrumento.objects.all().select_related('entidad').order_by('-updated_at')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(instrumento_id__icontains=query))
        instrumentos = [
            {'objeto': inst, 'vigencia': evaluar_vigencia_instrumento(inst)}
            for inst in qs
        ]

    context = {
        'seccion': seccion,
        'query': query,
        'entidades': entidades,
        'instrumentos': instrumentos,
        'convocatorias': convocatorias,
    }
    return render(request, 'admin_humm/catalogo_list.html', context)


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_preguntas_editor_view(request):
    """
    Preguntas y orientación: permite editar títulos, ayudas, etiquetas y orden.
    Valida límite estricto de máximo 5 preguntas.
    """
    formulario = FormularioConfig.objects.filter(es_activa=True).first()
    if not formulario:
        formulario = FormularioConfig.objects.first()

    if request.method == 'POST':
        # Guardar cambios en preguntas existentes
        for p in formulario.preguntas.all():
            titulo = request.POST.get(f'titulo_{p.id}')
            ayuda = request.POST.get(f'ayuda_{p.id}')
            activa = request.POST.get(f'activa_{p.id}') == 'on'

            if titulo:
                p.titulo = titulo.strip()
            if ayuda is not None:
                p.ayuda = ayuda.strip()
            p.activa = activa
            p.save()

            # Opciones
            for op in p.opciones.all():
                etq = request.POST.get(f'op_etiqueta_{op.id}')
                desc = request.POST.get(f'op_desc_{op.id}')
                op_activa = request.POST.get(f'op_activa_{op.id}') == 'on'
                if etq:
                    op.etiqueta = etq.strip()
                if desc is not None:
                    op.descripcion_auxiliar = desc.strip()
                op.activa = op_activa
                op.save()

        messages.success(request, "Cuestionario actualizado exitosamente.")
        return redirect('orientador:admin_preguntas')

    preguntas = []
    if formulario:
        preguntas = formulario.preguntas.all().prefetch_related('opciones').order_by('orden')

    return render(request, 'admin_humm/preguntas_editor.html', {
        'formulario': formulario,
        'preguntas': preguntas,
    })


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_import_export_view(request):
    """
    Importar y exportar: descargar plantilla .xlsx, exportar base y subir actualización.
    """
    config = ConfiguracionGlobal.get_solo()
    historial_lotes = ImportacionLote.objects.all().order_by('-created_at')[:10]

    return render(request, 'admin_humm/import_export.html', {
        'config': config,
        'historial_lotes': historial_lotes,
    })


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_descargar_plantilla_view(request):
    """Descarga la plantilla vacía estándar con el esquema canónico."""
    buf = generar_excel_catalogo(incluir_datos=False)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Plantilla_Fondos_Humm.xlsx"'
    return response


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_exportar_base_view(request):
    """Exporta todo el catálogo actual de la base de datos a un archivo .xlsx canónico."""
    buf = generar_excel_catalogo(incluir_datos=True)
    config = ConfiguracionGlobal.get_solo()
    ahora_str = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"Catalogo_Humm_Fondos_v{config.version_catalogo}_{ahora_str}.xlsx"
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_subir_excel_view(request):
    """
    Recibe el archivo Excel cargado y muestra la previsualización de diferencias antes de aplicar.
    """
    if request.method != 'POST' or 'archivo_excel' not in request.FILES:
        messages.error(request, "Por favor selecciona un archivo .xlsx válido.")
        return redirect('orientador:admin_import_export')

    archivo = request.FILES['archivo_excel']
    if not archivo.name.endswith('.xlsx'):
        messages.error(request, "El archivo debe tener formato .xlsx (Excel).")
        return redirect('orientador:admin_import_export')

    content = archivo.read()

    # Guardar en sesión para confirmación
    request.session['excel_import_content'] = content.hex()
    request.session['excel_import_filename'] = archivo.name

    resumen = validar_y_previsualizar_excel(content, archivo.name)

    return render(request, 'admin_humm/import_preview.html', {
        'resumen': resumen,
    })


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_confirmar_importacion_view(request):
    """
    Aplica atómicamente la actualización confirmada por el administrador.
    """
    if request.method != 'POST':
        return redirect('orientador:admin_import_export')

    content_hex = request.session.pop('excel_import_content', None)
    filename = request.session.pop('excel_import_filename', 'actualizacion.xlsx')

    if not content_hex:
        messages.error(request, "La sesión de importación expiró. Por favor carga el archivo nuevamente.")
        return redirect('orientador:admin_import_export')

    content = bytes.fromhex(content_hex)
    usuario = request.user.username or 'admin'

    try:
        lote = aplicar_actualizacion_excel(content, filename, usuario)
        messages.success(request, f"¡Actualización aplicada con éxito! {lote.resumen}")
    except Exception as e:
        messages.error(request, f"Error al aplicar la actualización: {str(e)}")

    return redirect('orientador:admin_dashboard')


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_revertir_lote_view(request, lote_id):
    """Revierte un lote de importación previo si es seguro."""
    if request.method != 'POST':
        return redirect('orientador:admin_dashboard')

    usuario = request.user.username or 'admin'
    try:
        res = revertir_lote_importacion(lote_id, usuario)
        messages.success(request, res['mensaje'])
    except Exception as e:
        messages.error(request, f"No se pudo revertir el lote: {str(e)}")

    return redirect('orientador:admin_dashboard')


@user_passes_test(es_administrador, login_url='/admin/login/')
def admin_configuracion_view(request):
    """Configuración global: nombre de plataforma, retornos, contacto, umbrales de revisión."""
    config = ConfiguracionGlobal.get_solo()

    if request.method == 'POST':
        config.nombre_plataforma = request.POST.get('nombre_plataforma', config.nombre_plataforma).strip()
        config.url_retorno_comunidad = request.POST.get('url_retorno_comunidad', config.url_retorno_comunidad).strip()
        config.contacto_email = request.POST.get('contacto_email', config.contacto_email).strip()
        config.contacto_whatsapp = request.POST.get('contacto_whatsapp', config.contacto_whatsapp).strip()
        config.canal_activo = request.POST.get('canal_activo', config.canal_activo)
        try:
            config.dias_revision_abierta = int(request.POST.get('dias_revision_abierta', 7))
            config.dias_revision_instrumento = int(request.POST.get('dias_revision_instrumento', 90))
        except ValueError:
            pass
        config.save()
        messages.success(request, "Configuración guardada correctamente.")
        return redirect('orientador:admin_configuracion')

    return render(request, 'admin_humm/configuracion.html', {'config': config})
