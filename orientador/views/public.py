import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from ..models import (
    FormularioConfig, PreguntaConfig, SolicitudApoyo,
    MetricaEvento, TipoMetrica
)
from ..services.matching_engine import evaluar_perfil_financiamiento


def formulario_view(request):
    """
    Muestra el formulario oficial de 5 preguntas en una sola página con desplazamiento vertical.
    Conserva las respuestas previas si el usuario vuelve a editarlas.
    """
    form_activo = FormularioConfig.objects.filter(es_activa=True).first()
    if not form_activo:
        form_activo = FormularioConfig.objects.first()

    preguntas = []
    if form_activo:
        preguntas = form_activo.preguntas.filter(activa=True).prefetch_related('opciones').order_by('orden')

    # Recuperar respuestas previas de la sesión
    respuestas_previas = request.session.get('humm_respuestas_perfil', {})
    error = request.session.pop('humm_form_error', None)

    # Registrar inicio de consulta (anónimo, sin PII)
    if 'consulta_iniciada_registrada' not in request.session:
        MetricaEvento.objects.create(tipo_evento=TipoMetrica.CONSULTA_INICIADA)
        request.session['consulta_iniciada_registrada'] = True

    return render(request, 'orientador/formulario.html', {
        'preguntas': preguntas,
        'respuestas_previas': respuestas_previas,
        'error': error,
    })


def procesar_consulta_view(request):
    """
    Recibe las respuestas del formulario, ejecuta el motor determinista y muestra los resultados.
    """
    if request.method != 'POST':
        return redirect('orientador:formulario')

    necesidades = request.POST.getlist('necesidades')
    situacion = request.POST.get('situacion', '').strip()
    region = request.POST.get('region', '').strip()
    monto_buscado = request.POST.get('monto_buscado', 'no_se').strip()
    rubro = request.POST.get('rubro', 'otro').strip()

    # Validaciones amigables
    if not necesidades:
        request.session['humm_form_error'] = "Por favor selecciona al menos una necesidad de financiamiento."
        return redirect('orientador:formulario')

    if len(necesidades) > 2:
        necesidades = necesidades[:2]

    if not situacion:
        request.session['humm_form_error'] = "Por favor indica en qué situación está tu emprendimiento."
        return redirect('orientador:formulario')

    if not region:
        request.session['humm_form_error'] = "Por favor selecciona la región donde desarrollarás el proyecto."
        return redirect('orientador:formulario')

    respuestas = {
        'necesidades': necesidades,
        'situacion': situacion,
        'region': region,
        'monto_buscado': monto_buscado,
        'rubro': rubro,
    }

    # Guardar en sesión para permitir volver a editar
    request.session['humm_respuestas_perfil'] = respuestas

    # Ejecutar motor de orientación determinista
    evaluacion = evaluar_perfil_financiamiento(respuestas)

    # Métrica anónima agregada
    if evaluacion['estado_vacio']:
        MetricaEvento.objects.create(
            tipo_evento=TipoMetrica.CONSULTA_SIN_RESULTADOS,
            datos={'region': region, 'situacion': situacion}
        )
    else:
        MetricaEvento.objects.create(
            tipo_evento=TipoMetrica.CONSULTA_COMPLETADA,
            datos={'region': region, 'situacion': situacion, 'total': evaluacion['total_pertinentes']}
        )

    context = {
        'resumen_perfil': evaluacion['resumen_perfil'],
        'pertinentes': evaluacion['pertinentes'],
        'proxima_etapa': evaluacion['proxima_etapa'],
        'total_pertinentes': evaluacion['total_pertinentes'],
        'total_proxima_etapa': evaluacion['total_proxima_etapa'],
        'siguiente_paso': evaluacion['siguiente_paso'],
        'estado_vacio': evaluacion['estado_vacio'],
    }

    return render(request, 'orientador/resultados.html', context)


@require_POST
def solicitar_apoyo_view(request):
    """
    Endpoint para registrar la solicitud voluntaria de apoyo de un emprendedor.
    Incluye protección contra doble pulsación y deduplicación.
    """
    nombre = request.POST.get('nombre', '').strip()
    canal = request.POST.get('canal_contacto', 'whatsapp').strip()
    contacto = request.POST.get('contacto_valor', '').strip()
    mensaje = request.POST.get('mensaje', '').strip()
    autorizacion = request.POST.get('autorizacion_contacto') == 'si'
    adjuntar_perfil = request.POST.get('adjuntar_perfil') == 'si'

    if not nombre or not contacto:
        return JsonResponse({'ok': False, 'error': 'Debes ingresar tu nombre y dato de contacto.'}, status=400)

    if not autorizacion:
        return JsonResponse({'ok': False, 'error': 'Debes autorizar a Comunidad Humm para responder tu consulta.'}, status=400)

    respuestas_perfil = None
    if adjuntar_perfil:
        respuestas_perfil = request.session.get('humm_respuestas_perfil')

    hash_idempotencia = SolicitudApoyo.generar_hash(nombre, canal, contacto, mensaje)

    # Comprobar si ya existe una solicitud idéntica (protección anti doble pulsación)
    existente = SolicitudApoyo.objects.filter(hash_idempotencia=hash_idempotencia).first()
    if existente:
        return JsonResponse({
            'ok': True,
            'mensaje': 'Tu solicitud ya fue registrada con anterioridad. Un orientador de Humm se comunicará contigo pronto.',
            'id': existente.id,
        })

    solicitud = SolicitudApoyo.objects.create(
        nombre=nombre,
        canal_contacto=canal,
        contacto_valor=contacto,
        mensaje=mensaje,
        autorizacion_contacto=autorizacion,
        respuestas_perfil=respuestas_perfil,
        hash_idempotencia=hash_idempotencia,
    )

    MetricaEvento.objects.create(
        tipo_evento=TipoMetrica.SOLICITUD_APOYO,
        datos={'canal': canal}
    )

    return JsonResponse({
        'ok': True,
        'mensaje': f'Gracias {nombre}, hemos recibido tu solicitud. Te responderemos vía {solicitud.get_canal_contacto_display()}.',
        'id': solicitud.id,
    })
