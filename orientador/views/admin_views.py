import io
import re
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q

from ..models import (
    Entidad, TipoEntidad, Instrumento, Convocatoria, ConfiguracionGlobal,
    FormularioConfig, PreguntaConfig, OpcionConfig, SolicitudApoyo,
    ImportacionLote, EstadoEditorial, EstadoFuente, CierreModalidad, MetricaEvento
)
from ..services.status_engine import (
    calcular_estado_convocatoria, evaluar_vigencia_instrumento, CodigoEstadoCalculado
)
from ..services.excel_contract import (
    generar_excel_catalogo, validar_y_previsualizar_excel,
    aplicar_actualizacion_excel, revertir_lote_importacion
)


from django.contrib.auth import authenticate, login, logout
from django.utils.http import url_has_allowed_host_and_scheme

def es_administrador(user):
    """Verifica si el usuario tiene rol de staff o superuser."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def admin_login_view(request):
    """Pantalla de inicio de sesión con la identidad visual oficial de Humm."""
    raw_next = request.GET.get('next') or request.POST.get('next') or '/gestion/'
    allowed_hosts = {request.get_host()}
    if url_has_allowed_host_and_scheme(url=raw_next, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        next_url = raw_next
    else:
        next_url = '/gestion/'

    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect(next_url)

    error = None
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        user = authenticate(request, username=u, password=p)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect(next_url)
        else:
            error = "Usuario o contraseña incorrectos, o no tienes permisos de administración."

    return render(request, 'admin_humm/login.html', {
        'error': error,
        'next_url': next_url,
    })


def admin_logout_view(request):
    """Cierra la sesión y regresa al orientador público."""
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect('orientador:formulario')


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


def obtener_siguiente_entidad_id():
    """Calcula el siguiente código ENT-XXX correlativo disponible."""
    ids = Entidad.objects.values_list('entidad_id', flat=True)
    numeros = []
    for eid in ids:
        m = re.match(r'^ENT-(\d+)$', str(eid).strip(), re.IGNORECASE)
        if m:
            numeros.append(int(m.group(1)))
    siguiente_num = (max(numeros) + 1) if numeros else 1
    return f"ENT-{siguiente_num:03d}"


def obtener_siguiente_convocatoria_id():
    """Calcula el siguiente código CONV-XXX correlativo disponible."""
    ids = Convocatoria.objects.values_list('convocatoria_id', flat=True)
    numeros = []
    for cid in ids:
        m = re.match(r'^CONV-(\d+)$', str(cid).strip(), re.IGNORECASE)
        if m:
            numeros.append(int(m.group(1)))
    siguiente_num = (max(numeros) + 1) if numeros else 1
    return f"CONV-{siguiente_num:03d}"


def parse_date_safe(val):
    """Parsea una fecha de manera segura desde formatos ISO o estándar."""
    if not val:
        return None
    val = str(val).strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(val, '%d-%m-%Y').date()
        except (ValueError, TypeError):
            return None


@user_passes_test(es_administrador, login_url='/gestion/login/')
def admin_catalogo_list_view(request):
    """
    Catálogo: búsqueda, filtros y listado de entidades, instrumentos y convocatorias.
    """
    seccion = request.GET.get('seccion', 'entidades').lower()
    query = request.GET.get('q', '').strip()

    total_entidades = Entidad.objects.count()
    total_instrumentos = Instrumento.objects.count()
    total_convocatorias = Convocatoria.objects.count()

    entidades = []
    instrumentos = []
    convocatorias = []
    resultados_conteo = 0

    if seccion == 'instrumentos':
        qs = Instrumento.objects.all().select_related('entidad').prefetch_related('convocatorias').order_by('-updated_at')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(instrumento_id__icontains=query))
        instrumentos = []
        for inst in qs:
            conv_principal = inst.convocatorias.filter(estado_editorial=EstadoEditorial.PUBLICADO).order_by('-updated_at').first()
            if not conv_principal:
                conv_principal = inst.convocatorias.order_by('-updated_at').first()
            estado_calc = calcular_estado_convocatoria(conv_principal) if conv_principal else None
            instrumentos.append({
                'objeto': inst,
                'vigencia': evaluar_vigencia_instrumento(inst),
                'convocatoria_principal': conv_principal,
                'estado_calc': estado_calc,
            })
        resultados_conteo = len(instrumentos)
    elif seccion == 'convocatorias':
        qs = Convocatoria.objects.all().select_related('instrumento', 'instrumento__entidad').order_by('-updated_at')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(convocatoria_id__icontains=query))
        convocatorias = [
            {'objeto': c, 'estado_calc': calcular_estado_convocatoria(c)}
            for c in qs
        ]
        resultados_conteo = len(convocatorias)
    else:
        # Por defecto entidades
        seccion = 'entidades'
        qs = Entidad.objects.all().order_by('nombre')
        if query:
            qs = qs.filter(Q(nombre__icontains=query) | Q(entidad_id__icontains=query))
        entidades = qs
        resultados_conteo = qs.count()

    context = {
        'seccion': seccion,
        'query': query,
        'entidades': entidades,
        'instrumentos': instrumentos,
        'convocatorias': convocatorias,
        'total_entidades': total_entidades,
        'total_instrumentos': total_instrumentos,
        'total_convocatorias': total_convocatorias,
        'resultados_conteo': resultados_conteo,
        'tipos_entidad': TipoEntidad.choices,
        'estados_editorial': EstadoEditorial.choices,
        'estados_fuente': EstadoFuente.choices,
        'modalidades_cierre': CierreModalidad.choices,
        'siguiente_entidad_id': obtener_siguiente_entidad_id(),
        'siguiente_convocatoria_id': obtener_siguiente_convocatoria_id(),
    }
    return render(request, 'admin_humm/catalogo_list.html', context)


@user_passes_test(es_administrador, login_url='/gestion/login/')
def admin_instrumento_guardar_estado_view(request):
    """
    Permite editar en caliente el estado (abierto/cerrado) y las fechas de apertura y cierre
    del llamado correspondiente a un instrumento.
    """
    if request.method != 'POST':
        return redirect('/gestion/catalogo/?seccion=instrumentos')

    instrumento_id = request.POST.get('instrumento_id', '').strip()
    instrumento = get_object_or_404(Instrumento, instrumento_id=instrumento_id)

    estado_llamado = request.POST.get('estado_llamado', EstadoFuente.ABIERTA).strip().lower()
    fecha_apertura = parse_date_safe(request.POST.get('fecha_apertura'))
    fecha_cierre = parse_date_safe(request.POST.get('fecha_cierre'))
    cierre_modalidad = request.POST.get('cierre_modalidad', CierreModalidad.FECHA_DEFINIDA).strip().lower()
    estado_editorial = request.POST.get('estado_editorial', EstadoEditorial.PUBLICADO).strip().lower()

    if estado_editorial in EstadoEditorial.values:
        instrumento.estado_editorial = estado_editorial

    now = timezone.now()
    instrumento.requisitos_verificado_en = now
    instrumento.montos_verificado_en = now
    instrumento.cobertura_verificado_en = now
    instrumento.save()

    # Buscar convocatoria existente o crear una nueva asociada a este instrumento
    conv = instrumento.convocatorias.order_by('-updated_at').first()
    if not conv:
        conv = Convocatoria(
            convocatoria_id=obtener_siguiente_convocatoria_id(),
            instrumento=instrumento,
            nombre=f"Convocatoria {instrumento.nombre}",
            estado_editorial=EstadoEditorial.PUBLICADO,
        )

    conv.estado_fuente = estado_llamado if estado_llamado in EstadoFuente.values else EstadoFuente.ABIERTA
    conv.fecha_apertura = fecha_apertura
    conv.fecha_cierre = fecha_cierre
    conv.cierre_modalidad = cierre_modalidad if cierre_modalidad in CierreModalidad.values else CierreModalidad.FECHA_DEFINIDA
    conv.estado_editorial = EstadoEditorial.PUBLICADO
    conv.fechas_verificado_en = now
    conv.estado_verificado_en = now
    conv.save()

    messages.success(request, f"Instrumento '{instrumento.nombre}': estado ({conv.get_estado_fuente_display()}) y fechas actualizados exitosamente.")
    return redirect('/gestion/catalogo/?seccion=instrumentos')


@user_passes_test(es_administrador, login_url='/gestion/login/')
def admin_convocatoria_guardar_view(request):
    """
    Permite editar en caliente el estado (abierto/cerrado), fechas de apertura y cierre,
    y detalles de una convocatoria existente.
    """
    if request.method != 'POST':
        return redirect('/gestion/catalogo/?seccion=convocatorias')

    convocatoria_id = request.POST.get('convocatoria_id', '').strip()
    conv = get_object_or_404(Convocatoria, convocatoria_id=convocatoria_id)

    nombre = request.POST.get('nombre', '').strip()
    estado_fuente = request.POST.get('estado_fuente', EstadoFuente.ABIERTA).strip().lower()
    fecha_apertura = parse_date_safe(request.POST.get('fecha_apertura'))
    fecha_cierre = parse_date_safe(request.POST.get('fecha_cierre'))
    cierre_modalidad = request.POST.get('cierre_modalidad', CierreModalidad.FECHA_DEFINIDA).strip().lower()
    estado_editorial = request.POST.get('estado_editorial', EstadoEditorial.PUBLICADO).strip().lower()

    if nombre:
        conv.nombre = nombre
    conv.estado_fuente = estado_fuente if estado_fuente in EstadoFuente.values else EstadoFuente.ABIERTA
    conv.fecha_apertura = fecha_apertura
    conv.fecha_cierre = fecha_cierre
    conv.cierre_modalidad = cierre_modalidad if cierre_modalidad in CierreModalidad.values else CierreModalidad.FECHA_DEFINIDA
    if estado_editorial in EstadoEditorial.values:
        conv.estado_editorial = estado_editorial

    now = timezone.now()
    conv.fechas_verificado_en = now
    conv.estado_verificado_en = now
    conv.save()

    messages.success(request, f"Convocatoria '{conv.nombre}' ({conv.convocatoria_id}): estado y fechas actualizados exitosamente.")
    return redirect('/gestion/catalogo/?seccion=convocatorias')


@user_passes_test(es_administrador, login_url='/gestion/login/')
def admin_entidad_guardar_view(request):
    """
    Crea o edita una Entidad directamente en la base de datos sin necesidad de recargar el Excel.
    - Modo creación: valida unicidad de ID y agrega la nueva entidad.
    - Modo edición: actualiza y reemplaza en caliente los campos (nombre, tipo, url_oficial, estado_editorial)
      de la entidad existente con el mismo ID, sin duplicar registros.
    """
    if request.method != 'POST':
        return redirect('/gestion/catalogo/?seccion=entidades')

    modo = request.POST.get('modo', 'crear').strip().lower()
    entidad_id = request.POST.get('entidad_id', '').strip()
    nombre = request.POST.get('nombre', '').strip()
    tipo = request.POST.get('tipo', TipoEntidad.PUBLICA).strip().lower()
    url_oficial = request.POST.get('url_oficial', '').strip()
    estado_editorial = request.POST.get('estado_editorial', EstadoEditorial.PUBLICADO).strip().lower()

    if not nombre:
        messages.error(request, "El nombre de la entidad es obligatorio.")
        return redirect('/gestion/catalogo/?seccion=entidades')

    if not url_oficial:
        messages.error(request, "La URL oficial es obligatoria.")
        return redirect('/gestion/catalogo/?seccion=entidades')

    if not url_oficial.startswith(('http://', 'https://')):
        url_oficial = f'https://{url_oficial}'

    if modo == 'editar':
        if not entidad_id:
            messages.error(request, "ID de entidad no proporcionado para edición.")
            return redirect('/gestion/catalogo/?seccion=entidades')

        entidad = get_object_or_404(Entidad, entidad_id=entidad_id)
        entidad.nombre = nombre
        entidad.tipo = tipo if tipo in TipoEntidad.values else TipoEntidad.PUBLICA
        entidad.url_oficial = url_oficial
        entidad.estado_editorial = estado_editorial if estado_editorial in EstadoEditorial.values else EstadoEditorial.PUBLICADO
        entidad.save()
        messages.success(request, f"Entidad '{entidad.nombre}' ({entidad.entidad_id}) actualizada correctamente.")
    else:
        # Modo creación
        if not entidad_id:
            entidad_id = obtener_siguiente_entidad_id()

        if Entidad.objects.filter(entidad_id=entidad_id).exists():
            messages.error(request, f"Ya existe una entidad con el identificador '{entidad_id}'. Para modificarla, utiliza la opción 'Editar'.")
            return redirect('/gestion/catalogo/?seccion=entidades')

        nueva_entidad = Entidad.objects.create(
            entidad_id=entidad_id,
            nombre=nombre,
            tipo=tipo if tipo in TipoEntidad.values else TipoEntidad.PUBLICA,
            url_oficial=url_oficial,
            estado_editorial=estado_editorial if estado_editorial in EstadoEditorial.values else EstadoEditorial.PUBLICADO
        )
        messages.success(request, f"Nueva entidad '{nueva_entidad.nombre}' ({nueva_entidad.entidad_id}) agregada exitosamente a la base de datos.")

    return redirect('/gestion/catalogo/?seccion=entidades')


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
def admin_descargar_plantilla_view(request):
    """Descarga la plantilla vacía estándar con el esquema canónico."""
    buf = generar_excel_catalogo(incluir_datos=False)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Plantilla_Fondos_Humm.xlsx"'
    return response


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
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


@user_passes_test(es_administrador, login_url='/gestion/login/')
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
