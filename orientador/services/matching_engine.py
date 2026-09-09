"""
Motor de Orientación y Recomendación Determinista
Reglas de la Sección 8 y 9 de la especificación Humm Financiamiento.
"""

from decimal import Decimal
from typing import Dict, List, Any
from ..models import (
    Instrumento, Convocatoria, EstadoEditorial, NoReembolsableConfirmado,
    FormalizacionRequerida, Moneda
)
from .status_engine import calcular_estado_convocatoria, evaluar_vigencia_instrumento, CodigoEstadoCalculado

# Nombres legibles para los códigos del formulario
ETIQUETAS_NECESIDADES = {
    'equipamiento': 'Equipos y herramientas',
    'capital_trabajo': 'Insumos y capital de trabajo',
    'ventas_digital': 'Ventas y digitalización',
    'prototipo': 'Prototipo o validación de una idea',
    'infraestructura': 'Habilitación o infraestructura',
    'asistencia_tecnica': 'Asesorías, capacitación o certificaciones',
}

ETIQUETAS_SITUACION = {
    'idea': 'Tengo una idea y todavía no vendo',
    'prototipo': 'Estoy desarrollando o probando un prototipo',
    'ventas_informales': 'Ya vendo, pero mi negocio no está formalizado',
    'ventas_formales': 'Tengo un negocio formalizado y ventas a pequeña escala',
}

ETIQUETAS_MONTOS = {
    'menor_1m': 'Menos de $1 millón',
    'de_1m_a_3_5m': 'Entre $1 y $3,5 millones',
    'mas_3_5m_a_10m': 'Más de $3,5 y hasta $10 millones',
    'mas_10m_a_20m': 'Más de $10 y hasta $20 millones',
    'mas_20m': 'Más de $20 millones',
    'no_se': 'Monto por definir',
}

ETIQUETAS_RUBROS = {
    'alimentos': 'Alimentos y elaboración',
    'comercio': 'Comercio',
    'servicios': 'Servicios',
    'turismo': 'Turismo',
    'agro_rural': 'Agricultura o actividad rural',
    'pesca': 'Pesca o acuicultura',
    'cultura_artesania': 'Cultura o artesanía',
    'tecnologia': 'Tecnología',
    'otro': 'Otro rubro',
}

REGIONES_CHILE = {
    'CL-AP': 'Arica y Parinacota',
    'CL-TA': 'Tarapacá',
    'CL-AN': 'Antofagasta',
    'CL-AT': 'Atacama',
    'CL-CO': 'Coquimbo',
    'CL-VA': 'Valparaíso',
    'CL-RM': 'Metropolitana de Santiago',
    'CL-OH': "O'Higgins",
    'CL-ML': 'Maule',
    'CL-NB': 'Ñuble',
    'CL-BI': 'Biobío',
    'CL-AR': 'La Araucanía',
    'CL-LR': 'Los Ríos',
    'CL-LL': 'Los Lagos',
    'CL-AI': 'Aysén',
    'CL-MA': 'Magallanes',
}


def evaluar_perfil_financiamiento(respuestas: Dict[str, Any], reference_time=None) -> Dict[str, Any]:
    """
    Ejecuta el motor de orientación sobre la base de datos persistente.
    Retorna resultados divididos en:
      - 'pertinentes': Opciones para postular o preparar ahora.
      - 'proxima_etapa': Opciones para cuando se alcance un hito (ej. formalización).
      - 'siguiente_paso': Estrategia personalizada.
      - 'resumen_perfil': Datos interpretados del usuario.
    """
    necesidades_usuario = respuestas.get('necesidades', [])
    if isinstance(necesidades_usuario, str):
        necesidades_usuario = [necesidades_usuario]
    necesidades_usuario = [n for n in necesidades_usuario if n]

    situacion_usuario = respuestas.get('situacion', '').strip()
    region_usuario = respuestas.get('region', '').strip()
    monto_usuario = respuestas.get('monto_buscado', 'no_se').strip()
    rubro_usuario = respuestas.get('rubro', 'otro').strip()

    resumen_perfil = {
        'necesidades': [ETIQUETAS_NECESIDADES.get(n, n) for n in necesidades_usuario],
        'situacion': ETIQUETAS_SITUACION.get(situacion_usuario, situacion_usuario),
        'region': REGIONES_CHILE.get(region_usuario, region_usuario),
        'monto': ETIQUETAS_MONTOS.get(monto_usuario, monto_usuario),
        'rubro': ETIQUETAS_RUBROS.get(rubro_usuario, rubro_usuario),
        'codigos': {
            'necesidades': necesidades_usuario,
            'situacion': situacion_usuario,
            'region': region_usuario,
            'monto_buscado': monto_usuario,
            'rubro': rubro_usuario,
        }
    }

    # 1. Filtro base: Solo instrumentos publicados y con no_reembolsable_confirmado == 'si'
    qs_instrumentos = Instrumento.objects.filter(
        estado_editorial=EstadoEditorial.PUBLICADO,
        no_reembolsable_confirmado=NoReembolsableConfirmado.SI
    ).select_related('entidad').prefetch_related('convocatorias')

    pertinentes = []
    proxima_etapa = []

    for inst in qs_instrumentos:
        evaluacion = evaluar_instrumento_con_perfil(
            instrumento=inst,
            necesidades=necesidades_usuario,
            situacion=situacion_usuario,
            region=region_usuario,
            monto_buscado=monto_usuario,
            rubro=rubro_usuario,
            reference_time=reference_time
        )

        if evaluacion['es_pertinente_ahora']:
            pertinentes.append(evaluacion)
        elif evaluacion['es_proxima_etapa']:
            proxima_etapa.append(evaluacion)

    # Ordenar pertinentes: priorizar los que tienen convocatoria abierta verificada, luego anunciada, etc.
    def score_orden(item):
        conv = item.get('convocatoria_principal')
        if not conv:
            return 10
        codigo = conv['estado_calculado']['codigo']
        orden_prioridad = {
            CodigoEstadoCalculado.ABIERTA_VERIFICADA: 1,
            CodigoEstadoCalculado.CIERRA_HOY_CONFIRMAR_HORA: 2,
            CodigoEstadoCalculado.VIGENCIA_POR_CONFIRMAR: 3,
            CodigoEstadoCalculado.APERTURA_PREVISTA: 4,
            CodigoEstadoCalculado.ANUNCIADA: 5,
            CodigoEstadoCalculado.PLAZO_FINALIZADO: 6,
            CodigoEstadoCalculado.CERRADA: 7,
            CodigoEstadoCalculado.POR_CONFIRMAR: 8,
            CodigoEstadoCalculado.SUSPENDIDA: 9,
            CodigoEstadoCalculado.CANCELADA: 11,
        }
        return orden_prioridad.get(codigo, 10)

    pertinentes.sort(key=score_orden)
    proxima_etapa.sort(key=score_orden)

    siguiente_paso = generar_siguiente_paso(
        situacion=situacion_usuario,
        necesidades=necesidades_usuario,
        pertinentes=pertinentes,
        proxima_etapa=proxima_etapa
    )

    return {
        'resumen_perfil': resumen_perfil,
        'pertinentes': pertinentes,
        'proxima_etapa': proxima_etapa,
        'total_pertinentes': len(pertinentes),
        'total_proxima_etapa': len(proxima_etapa),
        'siguiente_paso': siguiente_paso,
        'estado_vacio': len(pertinentes) == 0 and len(proxima_etapa) == 0,
    }


def evaluar_instrumento_con_perfil(
    instrumento: Instrumento,
    necesidades: List[str],
    situacion: str,
    region: str,
    monto_buscado: str,
    rubro: str,
    reference_time=None
) -> Dict[str, Any]:
    """
    Evalúa un instrumento específico contra las respuestas dadas.
    """
    # Evaluar convocatorias activas / aplicables
    convocatorias_publicadas = list(
        instrumento.convocatorias.filter(
            estado_editorial=EstadoEditorial.PUBLICADO
        )
    )

    # Evaluar territorialidad
    # Si alguna convocatoria coincide con la región, o si el instrumento cubre la región
    inst_regiones = instrumento.get_regiones_list()
    cubre_region_inst = ('todos' in inst_regiones or region in inst_regiones or not region)

    convocatorias_evaluadas = []
    for conv in convocatorias_publicadas:
        conv_regiones = conv.get_effective_regiones()
        cubre_conv_region = ('todos' in conv_regiones or region in conv_regiones or not region)
        if cubre_conv_region:
            estado_calc = calcular_estado_convocatoria(conv, reference_time=reference_time)
            convocatorias_evaluadas.append({
                'objeto': conv,
                'nombre': conv.nombre,
                'convocatoria_id': conv.convocatoria_id,
                'estado_calculado': estado_calc,
                'monto_max': conv.get_effective_monto_max(),
                'moneda': conv.get_effective_moneda(),
                'url': conv.url_convocatoria or conv.instrumento.url_programa or conv.instrumento.entidad.url_oficial,
                'comunas': conv.comunas,
            })

    # Si el instrumento tiene convocatorias regionales pero ninguna para esta región,
    # y el instrumento mismo no es nacional general, no coincide territorialmente
    if not cubre_region_inst and not convocatorias_evaluadas:
        return {
            'instrumento': instrumento,
            'es_pertinente_ahora': False,
            'es_proxima_etapa': False,
            'motivo_exclusion': 'Territorial: no disponible en tu región.',
        }

    # Evaluar Necesidades
    inst_necesidades = instrumento.get_necesidades_list()
    necesidades_cubiertas = []
    if 'todos' in inst_necesidades:
        necesidades_cubiertas = [ETIQUETAS_NECESIDADES.get(n, n) for n in necesidades]
    else:
        for n in necesidades:
            if n in inst_necesidades:
                necesidades_cubiertas.append(ETIQUETAS_NECESIDADES.get(n, n))

    if not necesidades_cubiertas and necesidades:
        # No cubre ninguna de las necesidades seleccionadas
        return {
            'instrumento': instrumento,
            'es_pertinente_ahora': False,
            'es_proxima_etapa': False,
            'motivo_exclusion': 'No cubre las necesidades seleccionadas.',
        }

    # Evaluar Rubro
    inst_rubros = instrumento.get_rubros_list()
    rubro_coincide = ('todos' in inst_rubros or rubro in inst_rubros or rubro == 'otro' and 'todos' in inst_rubros)
    if not rubro_coincide:
        return {
            'instrumento': instrumento,
            'es_pertinente_ahora': False,
            'es_proxima_etapa': False,
            'motivo_exclusion': 'Rubro específico no compatible.',
        }

    # Evaluar Situación y Formalización
    # Separar entre "Postular ahora" vs "Para una próxima etapa"
    formalizacion_req = instrumento.formalizacion_requerida
    es_pertinente_ahora = True
    es_proxima_etapa = False
    motivo_proxima_etapa = ""
    condiciones_pendientes = []

    if formalizacion_req in [FormalizacionRequerida.CON_INICIO_PRIMERA, FormalizacionRequerida.FORMALIZACION_DECLARADA]:
        if situacion in ['idea', 'prototipo', 'ventas_informales']:
            es_pertinente_ahora = False
            es_proxima_etapa = True
            motivo_proxima_etapa = "Requiere tener empresa formalizada con inicio de actividades en 1ª categoría ante el SII. Tu situación actual es preparatoria para este fondo."
        else:
            # ventas_formales
            condiciones_pendientes.append("Acreditar inicio de actividades en 1ª categoría y antigüedad mínima según bases.")
    elif formalizacion_req == FormalizacionRequerida.SIN_INICIO_PRIMERA:
        if situacion == 'ventas_formales':
            # Fondos exclusivos para no formalizados (ej. Capital Semilla / Abeja tradicional)
            es_pertinente_ahora = False
            es_proxima_etapa = False
            return {
                'instrumento': instrumento,
                'es_pertinente_ahora': False,
                'es_proxima_etapa': False,
                'motivo_exclusion': 'Diseñado exclusivamente para personas sin inicio de actividades en 1ª categoría.',
            }
        else:
            condiciones_pendientes.append("Confirmar no tener inicio de actividades en 1ª categoría ante el SII.")

    # Requisitos institucionales conocidos a advertir
    entidad_nombre = instrumento.entidad.nombre.upper()
    if 'FOSIS' in entidad_nombre:
        condiciones_pendientes.append("Registro Social de Hogares (RSH): pertenecer al tramo de vulnerabilidad exigido (habitualmente 40% a 60%).")
    elif 'SERCOTEC' in entidad_nombre:
        if 'ABEJA' in instrumento.nombre.upper():
            condiciones_pendientes.append("Postulante debe ser mujer (exclusivo para emprendedoras según bases).")
    elif 'CORFO' in entidad_nombre or 'START-UP CHILE' in entidad_nombre:
        condiciones_pendientes.append("Innovación y potencial de crecimiento: requiere solución con diferenciación clara frente a la oferta existente.")

    # Convocatoria principal a destacar
    convocatoria_principal = convocatorias_evaluadas[0] if convocatorias_evaluadas else None

    # Explicación de por qué aparece
    por_que_aparece = f"Coincide con tu necesidad de {', '.join(necesidades_cubiertas) if necesidades_cubiertas else 'financiamiento'} y tu etapa actual."
    if instrumento.cobertura == 'nacional':
        por_que_aparece += " Disponible en todo Chile."
    elif region:
        por_que_aparece += f" Convocatoria aplicable a la Región de {REGIONES_CHILE.get(region, region)}."

    # Comparación prudente de monto
    nota_monto = ""
    monto_max = instrumento.monto_max
    if convocatoria_principal and convocatoria_principal['monto_max']:
        monto_max = convocatoria_principal['monto_max']

    moneda = instrumento.moneda
    if monto_max:
        if moneda == Moneda.CLP:
            monto_fmt = f"${monto_max:,.0f}".replace(',', '.')
        else:
            monto_fmt = f"{monto_max} {moneda}"

        if monto_buscado == 'mas_10m_a_20m' or monto_buscado == 'mas_20m':
            if moneda == Moneda.CLP and monto_max <= Decimal('10000000'):
                nota_monto = f"Aporte de hasta {monto_fmt} (cubre parte de tu meta de financiamiento)."
            else:
                nota_monto = f"Aporta hasta {monto_fmt} según bases."
        else:
            nota_monto = f"Aporta hasta {monto_fmt}."

    vigencia_info = evaluar_vigencia_instrumento(instrumento, reference_time=reference_time)

    return {
        'instrumento': instrumento,
        'es_pertinente_ahora': es_pertinente_ahora,
        'es_proxima_etapa': es_proxima_etapa,
        'motivo_proxima_etapa': motivo_proxima_etapa,
        'por_que_aparece': por_que_aparece,
        'necesidades_cubiertas': necesidades_cubiertas,
        'condiciones_pendientes': condiciones_pendientes[:2],  # Hasta 2 prioritarias en tarjeta
        'todas_condiciones_pendientes': condiciones_pendientes,
        'nota_monto': nota_monto,
        'vigencia_info': vigencia_info,
        'convocatoria_principal': convocatoria_principal,
        'otras_convocatorias': convocatorias_evaluadas[1:] if len(convocatorias_evaluadas) > 1 else [],
    }


def generar_siguiente_paso(situacion: str, necesidades: List[str], pertinentes: List[Any], proxima_etapa: List[Any]) -> Dict[str, Any]:
    """
    Construye la recomendación de la Sección 9:
    Una acción concreta y hasta tres tareas breves, pertinentes al perfil.
    """
    if situacion == 'idea':
        accion_principal = "Clarificar el modelo básico y cotizar la inversión prioritaria"
        tareas = [
            "Define exactamente qué equipos o herramientas necesitas y solicita 2 o 3 cotizaciones referenciales.",
            "Revisa si los fondos disponibles exigen no tener inicio de actividades antes de dar cualquier paso en el SII.",
            "Revisa las bases de convocatorias anteriores para familiarizarte con las preguntas de postulación."
        ]
    elif situacion == 'prototipo':
        accion_principal = "Validar técnicamente el prototipo con usuarios reales"
        tareas = [
            "Documenta las pruebas realizadas y el resultado del prototipo para sustentar la postulación.",
            "Desglosa los costos específicos de materiales e insumos necesarios para la siguiente fase.",
            "Verifica si tu solución cuenta con mérito innovador para postular a líneas de Corfo o Start-Up Chile."
        ]
    elif situacion == 'ventas_informales':
        accion_principal = "Ordenar números de ventas y evaluar el momento oportuno de formalización"
        tareas = [
            "Registra tus ventas y costos mensuales de los últimos 6 meses en una planilla sencilla.",
            "Comprueba los requisitos de inicio de actividades: algunos fondos premian formalizarse con el subsidio, mientras otros exigen antigüedad previa.",
            "Revisa si tu grupo familiar cuenta con Registro Social de Hogares (RSH) actualizado en caso de postular a líneas FOSIS."
        ]
    elif situacion == 'ventas_formales':
        accion_principal = "Preparar antecedentes tributarios y cotizaciones de inversión"
        tareas = [
            "Descarga tu Carpeta Tributaria para Solicitar Créditos/Fondos desde el portal del SII.",
            "Verifica que el tramo de ventas de tu empresa coincida con los límites de micro o pequeña empresa de la convocatoria.",
            "Cotiza los gastos en digitalización, infraestructura o equipamiento con facturas proforma."
        ]
    else:
        accion_principal = "Preparar antecedentes clave del proyecto"
        tareas = [
            "Identifica tu necesidad prioritaria de financiamiento.",
            "Revisa los requisitos de admisibilidad de las opciones presentadas.",
            "Descarga las bases oficiales de la convocatoria que más se ajuste a tu etapa."
        ]

    return {
        'accion_principal': accion_principal,
        'tareas': tareas[:3],
    }
