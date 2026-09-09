"""
Motor de Orientación y Recomendación Determinista — Humm Financiamiento
Implementa las directrices oficiales, evaluación en 3 estados (Coincide, Próxima Etapa, Incompatible)
y generación de Directriz Inicial conforme al documento de revisión técnica del 9 de septiembre de 2026.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional
from ..models import (
    Instrumento, Convocatoria, EstadoEditorial, NoReembolsableConfirmado,
    FormalizacionRequerida, VentasRequeridas, Moneda
)
from .status_engine import calcular_estado_convocatoria, evaluar_vigencia_instrumento, CodigoEstadoCalculado

# ---------------------------------------------------------------------------
# Catálogos de etiquetas legibles para el resumen del perfil y directrices
# ---------------------------------------------------------------------------

ETIQUETAS_OBJETIVOS = {
    'iniciar_negocio': 'Iniciar y poner en marcha un negocio',
    'fortalecer_negocio': 'Fortalecer o aumentar la capacidad de mi negocio',
    'vender_digitalizar': 'Vender más, digitalizar o llegar a nuevos mercados',
    'desarrollar_innovacion': 'Desarrollar y probar una solución nueva o mejorada',
    'sostenibilidad': 'Reducir el impacto ambiental de mi negocio',
    'proyecto_cultural': 'Crear o desarrollar un proyecto artístico o cultural',
    'por_definir': 'Aún no lo tengo claro / Por definir',
}

ETIQUETAS_NECESIDADES = {
    'equipamiento': 'Equipos y herramientas',
    'capital_trabajo': 'Insumos y capital de trabajo',
    'ventas_digital': 'Ventas, difusión y herramientas digitales',
    'prototipo': 'Desarrollo, prototipo y validación',
    'infraestructura': 'Habilitación e infraestructura',
    'asistencia_tecnica': 'Asesorías, capacitación o certificaciones',
    'produccion_cultural': 'Creación y producción de obras o contenidos',
    'por_definir': 'Inversión aún por definir',
}

ETIQUETAS_ESTADO_ACTIVIDAD = {
    'sin_primera_sin_ventas': 'Aún no vendo y no tengo inicio de actividades en 1ª categoría',
    'sin_primera_con_ventas': 'Ya vendo, pero no tengo inicio de actividades en 1ª categoría',
    'con_primera_sin_ventas': 'Tengo inicio de actividades en 1ª categoría, pero todavía no vendo',
    'con_primera_con_ventas': 'Tengo inicio de actividades en 1ª categoría y ya vendo',
    'por_confirmar': 'Situación tributaria por confirmar ante el SII',
}

# Compatibilidad con formulario v1 histórico
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
    'no_se': 'Monto referencial en bases',
}

ETIQUETAS_RUBROS = {
    'alimentos': 'Alimentos y elaboración',
    'comercio': 'Comercio y negocios de barrio',
    'servicios': 'Servicios',
    'turismo': 'Turismo',
    'agropecuario': 'Agricultura, ganadería o actividad forestal',
    'agro_rural': 'Agricultura, ganadería o actividad forestal',  # alias histórico
    'pesca': 'Pesca o acuicultura',
    'cultura': 'Cultura, artesanía e industrias creativas',
    'cultura_artesania': 'Cultura, artesanía e industrias creativas',  # alias histórico
    'tecnologia': 'Tecnología y servicios digitales',
    'otro': 'Otro rubro o multisectorial',
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


def generar_directriz_inicial(objetivo: str, estado_actividad: str) -> Dict[str, Any]:
    """
    Construye la directriz oficial de orientación según la Sección 5:
    Explica qué busca lograr la persona y la condición principal para avanzar antes de listar los fondos.
    """
    directrices_por_objetivo = {
        'iniciar_negocio': {
            'titular': 'Tu búsqueda se orienta a la puesta en marcha del negocio. Revisa alternativas de capital inicial.',
            'consejo': 'Para dar los primeros pasos te conviene priorizar programas de inicio y comprobar si exigen no registrar inicio de actividades previo.',
            'pendientes_clave': [
                'Requisitos sociales (RSH) en programas de fomento inicial',
                'Condición de primera categoría y exclusiones de bases',
                'Definición de cotizaciones y plan de compras'
            ]
        },
        'fortalecer_negocio': {
            'titular': 'Tu búsqueda se orienta a inversión y mejora de la capacidad productiva.',
            'consejo': 'Buscas escalar o consolidar operaciones. Conviene tener claridad de los equipos o infraestructura que impulsarán tu crecimiento.',
            'pendientes_clave': [
                'Ventas mínimas o máximas exigidas por tramo',
                'Antigüedad tributaria en 1ª categoría ante el SII',
                'Porcentaje de aporte propio y gastos permitidos'
            ]
        },
        'vender_digitalizar': {
            'titular': 'Tu búsqueda se orienta a mejorar ventas, canales comerciales o adopción de herramientas digitales.',
            'consejo': 'El financiamiento puede apoyar marketing, comercio electrónico o modernización tecnológica para captar más clientes.',
            'pendientes_clave': [
                'Tipo de rubro elegible (almacén, comercio minorista o servicios)',
                'Acreditación de ventas previas según el llamado',
                'Presupuesto de software o difusión digital cotizado'
            ]
        },
        'desarrollar_innovacion': {
            'titular': 'Tu búsqueda se orienta a desarrollar y validar una solución. Debes explicar su diferencia y las pruebas que realizarás.',
            'consejo': 'Los fondos de innovación exigen justificar por qué tu solución supera las alternativas de mercado y qué hitos técnicos validarás.',
            'pendientes_clave': [
                'Madurez del prototipo y grado de novedad demostrable',
                'Equipo de trabajo y dedicación al proyecto',
                'Potencial de escalabilidad e impacto de mercado'
            ]
        },
        'sostenibilidad': {
            'titular': 'Tu inversión busca reducir impacto ambiental (energía, agua o residuos). Conviene cuantificar esa mejora antes de postular.',
            'consejo': 'La sostenibilidad es transversal a cualquier rubro. Enfócate en cómo tu proyecto generará un ahorro medible o mitigará la huella ambiental.',
            'pendientes_clave': [
                'Métricas o indicadores de reducción de impacto proyectados',
                'Elegibilidad empresarial según las bases de la convocatoria',
                'Límites de cofinanciamiento y aporte propio'
            ]
        },
        'proyecto_cultural': {
            'titular': 'Tu búsqueda se orienta a financiamiento para creación y producción artística o cultural.',
            'consejo': 'Los fondos culturales se organizan en líneas y disciplinas específicas (música, audiovisual, artes escénicas, literatura, etc.).',
            'pendientes_clave': [
                'Línea y disciplina artística aplicable a la obra o proyecto',
                'Trayectoria requerida y tipo de postulante (persona natural o jurídica)',
                'Cronograma de ejecución y derechos de autor si corresponde'
            ]
        },
        'por_definir': {
            'titular': 'Explora opciones de financiamiento acordes a tu situación y necesidades principales.',
            'consejo': 'Revisa los fondos disponibles para identificar qué requisitos te conviene preparar primero.',
            'pendientes_clave': [
                'Definición del objetivo prioritario del financiamiento',
                'Requisitos tributarios y territoriales de cada convocatoria'
            ]
        }
    }

    base = directrices_por_objetivo.get(objetivo, directrices_por_objetivo['por_definir'])

    # Agregar matiz según situación ante el SII
    if estado_actividad == 'sin_primera_sin_ventas':
        matiz_tributario = "Actualmente no tienes inicio de actividades ni ventas: tu ruta natural comienza por fondos de iniciación o preparación."
    elif estado_actividad == 'sin_primera_con_ventas':
        matiz_tributario = "Tienes ventas pero sin inicio de actividades en 1ª categoría: algunos fondos apoyan formalizarte, mientras otros para empresas exigen antigüedad previa."
    elif estado_actividad == 'con_primera_sin_ventas':
        matiz_tributario = "Cuentas con 1ª categoría formalizada ante el SII sin ventas aún: puedes postular a líneas de validación o capital temprano que admitan empresas nuevas."
    elif estado_actividad == 'con_primera_con_ventas':
        matiz_tributario = "Tienes empresa formalizada con ventas activas: accedes a las líneas de fortalecimiento, crecimiento y desarrollo productivo."
    else:
        matiz_tributario = "Verifica tu situación tributaria ante el SII para confirmar los llamados donde eres elegible."

    return {
        'titular': base['titular'],
        'consejo': base['consejo'],
        'matiz_tributario': matiz_tributario,
        'pendientes_clave': base['pendientes_clave'],
    }


def evaluar_perfil_financiamiento(respuestas: Dict[str, Any], reference_time=None) -> Dict[str, Any]:
    """
    Ejecuta el motor de orientación determinista sobre la base de datos persistente.
    Soporta tanto el Formulario v2 (objetivo, necesidades, estado_actividad, region, rubro)
    como compatibilidad retroactiva con Formulario v1 (situacion, monto_buscado).
    """
    # 1. Extraer y normalizar respuestas
    objetivo_usuario = respuestas.get('objetivo_financiamiento', '').strip()
    if not objetivo_usuario:
        objetivo_usuario = 'por_definir'

    necesidades_usuario = respuestas.get('necesidades', [])
    if isinstance(necesidades_usuario, str):
        necesidades_usuario = [necesidades_usuario]
    necesidades_usuario = [n.strip() for n in necesidades_usuario if n.strip()]

    # Manejar salida discreta y exclusiva 'por_definir' en necesidades
    if 'por_definir' in necesidades_usuario:
        necesidades_usuario = ['por_definir']

    estado_actividad_usuario = respuestas.get('estado_actividad', '').strip()
    # Retrocompatibilidad si viene 'situacion' v1
    situacion_v1 = respuestas.get('situacion', '').strip()
    if not estado_actividad_usuario and situacion_v1:
        if situacion_v1 in ['idea', 'prototipo']:
            estado_actividad_usuario = 'sin_primera_sin_ventas'
        elif situacion_v1 == 'ventas_informales':
            estado_actividad_usuario = 'sin_primera_con_ventas'
        elif situacion_v1 == 'ventas_formales':
            estado_actividad_usuario = 'con_primera_con_ventas'
        else:
            estado_actividad_usuario = 'por_confirmar'

    if not estado_actividad_usuario:
        estado_actividad_usuario = 'por_confirmar'

    region_usuario = respuestas.get('region', '').strip()

    rubro_usuario = respuestas.get('rubro', 'otro').strip()
    # Normalizar alias de rubros
    if rubro_usuario == 'agro_rural':
        rubro_usuario = 'agropecuario'
    elif rubro_usuario == 'cultura_artesania':
        rubro_usuario = 'cultura'

    monto_usuario = respuestas.get('monto_buscado', 'no_se').strip()

    # 2. Generar directriz inicial
    directriz = generar_directriz_inicial(objetivo_usuario, estado_actividad_usuario)

    # 3. Resumen legible del perfil para la vista
    resumen_perfil = {
        'objetivo': ETIQUETAS_OBJETIVOS.get(objetivo_usuario, objetivo_usuario),
        'necesidades': [ETIQUETAS_NECESIDADES.get(n, n) for n in necesidades_usuario],
        'estado_actividad': ETIQUETAS_ESTADO_ACTIVIDAD.get(estado_actividad_usuario, estado_actividad_usuario),
        'situacion': ETIQUETAS_ESTADO_ACTIVIDAD.get(estado_actividad_usuario, estado_actividad_usuario),
        'region': REGIONES_CHILE.get(region_usuario, region_usuario or 'Nacional'),
        'monto': ETIQUETAS_MONTOS.get(monto_usuario, monto_usuario),
        'rubro': ETIQUETAS_RUBROS.get(rubro_usuario, rubro_usuario),
        'codigos': {
            'objetivo_financiamiento': objetivo_usuario,
            'necesidades': necesidades_usuario,
            'estado_actividad': estado_actividad_usuario,
            'situacion': estado_actividad_usuario,
            'region': region_usuario,
            'rubro': rubro_usuario,
            'monto_buscado': monto_usuario,
        }
    }

    # 4. Filtro base: Solo instrumentos publicados y no reembolsables confirmados ('si')
    qs_instrumentos = Instrumento.objects.filter(
        estado_editorial=EstadoEditorial.PUBLICADO,
        no_reembolsable_confirmado=NoReembolsableConfirmado.SI
    ).select_related('entidad').prefetch_related('convocatorias')

    pertinentes = []
    proxima_etapa = []

    for inst in qs_instrumentos:
        evaluacion = evaluar_instrumento_con_perfil(
            instrumento=inst,
            objetivo=objetivo_usuario,
            necesidades=necesidades_usuario,
            estado_actividad=estado_actividad_usuario,
            region=region_usuario,
            rubro=rubro_usuario,
            monto_buscado=monto_usuario,
            reference_time=reference_time
        )

        if evaluacion['es_pertinente_ahora']:
            pertinentes.append(evaluacion)
        elif evaluacion['es_proxima_etapa']:
            proxima_etapa.append(evaluacion)

    # 5. Ordenamiento determinista por pertinencia y vigencia
    def score_orden(item):
        conv = item.get('convocatoria_principal')
        base_score = 10
        if conv:
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
            base_score = orden_prioridad.get(codigo, 10)

        # Bonificación por ajuste exacto de objetivo
        if item.get('coincidencia_objetivo_exacta'):
            base_score -= 0.5

        return base_score

    pertinentes.sort(key=score_orden)
    proxima_etapa.sort(key=score_orden)

    # 6. Generar siguiente paso estratégico personalizado
    siguiente_paso = generar_siguiente_paso(
        estado_actividad=estado_actividad_usuario,
        objetivo=objetivo_usuario,
        necesidades=necesidades_usuario,
        pertinentes=pertinentes,
        proxima_etapa=proxima_etapa
    )

    return {
        'directriz_inicial': directriz,
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
    objetivo: str,
    necesidades: List[str],
    estado_actividad: str,
    region: str,
    rubro: str,
    monto_buscado: str = 'no_se',
    reference_time=None
) -> Dict[str, Any]:
    """
    Evalúa un instrumento y sus convocatorias contra el perfil del usuario.
    Retorna si es pertinente ahora, para una próxima etapa o incompatible con su motivo.
    """
    # Descomponer estado de actividad ante SII y ventas
    tiene_primera = None
    tiene_ventas = None

    if estado_actividad == 'sin_primera_sin_ventas':
        tiene_primera = False
        tiene_ventas = False
    elif estado_actividad == 'sin_primera_con_ventas':
        tiene_primera = False
        tiene_ventas = True
    elif estado_actividad == 'con_primera_sin_ventas':
        tiene_primera = True
        tiene_ventas = False
    elif estado_actividad == 'con_primera_con_ventas':
        tiene_primera = True
        tiene_ventas = True

    # ----------------------------------------------------
    # 1. Territorialidad (Instrumento y Convocatorias)
    # ----------------------------------------------------
    convocatorias_publicadas = list(
        instrumento.convocatorias.filter(
            estado_editorial=EstadoEditorial.PUBLICADO
        )
    )

    inst_regiones = instrumento.get_regiones_list()
    cubre_region_inst = ('todos' in inst_regiones or region in inst_regiones or not region)

    convocatorias_evaluadas = []
    for conv in convocatorias_publicadas:
        conv_regiones = conv.get_effective_regiones()
        cubre_conv_region = ('todos' in conv_regiones or region in conv_regiones or not region)
        
        # Validación territorial estricta: si la convocatoria es comunal/regional específica (ej. Cisnes CL-AI)
        if conv.cobertura in ['comunal', 'regional'] and region and region not in conv_regiones and 'todos' not in conv_regiones:
            cubre_conv_region = False

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
    # y el instrumento mismo no cubre la región, queda excluido territorialmente
    if not cubre_region_inst and not convocatorias_evaluadas:
        return {
            'instrumento': instrumento,
            'es_pertinente_ahora': False,
            'es_proxima_etapa': False,
            'motivo_exclusion': 'Territorial: no disponible en tu región.',
        }

    # ----------------------------------------------------
    # 2. Rubro y Sectorialización
    # ----------------------------------------------------
    inst_rubros = instrumento.get_rubros_list()
    
    # Comprobar si el instrumento tiene restricción sectorial estricta
    if 'todos' not in inst_rubros:
        # Instrumento especializado (ej. cultura, agropecuario, pesca, comercio;alimentos)
        rubro_coincide = (rubro in inst_rubros)
        # Excepción amigable para proyectos culturales con objetivo cultural
        if 'cultura' in inst_rubros and objetivo == 'proyecto_cultural':
            rubro_coincide = True
        # Excepción para innovación en tecnología o agro
        if 'tecnologia' in inst_rubros and objetivo == 'desarrollar_innovacion':
            rubro_coincide = True

        if not rubro_coincide:
            return {
                'instrumento': instrumento,
                'es_pertinente_ahora': False,
                'es_proxima_etapa': False,
                'motivo_exclusion': f"Sectorial: instrumento exclusivo para rubro {', '.join(inst_rubros)}.",
            }
    else:
        # El instrumento es multisectorial ('todos')
        # Pero si el usuario eligió 'proyecto_cultural' y el instrumento es un fondo general o industrial no cultural,
        # lo mantenemos elegible pero sin prioridad artificial.
        pass

    # ----------------------------------------------------
    # 3. Necesidades financiables
    # ----------------------------------------------------
    inst_necesidades = instrumento.get_necesidades_list()
    necesidades_cubiertas = []
    
    if 'por_definir' in necesidades:
        # La persona no definió gastos aún: no se excluye por necesidades
        necesidades_cubiertas = ['Gastos según bases']
    elif 'todos' in inst_necesidades:
        necesidades_cubiertas = [ETIQUETAS_NECESIDADES.get(n, n) for n in necesidades]
    else:
        for n in necesidades:
            if n in inst_necesidades:
                necesidades_cubiertas.append(ETIQUETAS_NECESIDADES.get(n, n))

        # Si el usuario indicó necesidades específicas y el instrumento no cubre ninguna, excluir
        if not necesidades_cubiertas and necesidades and 'por_definir' not in necesidades:
            return {
                'instrumento': instrumento,
                'es_pertinente_ahora': False,
                'es_proxima_etapa': False,
                'motivo_exclusion': 'No cubre las necesidades de inversión seleccionadas.',
            }

    # ----------------------------------------------------
    # 4. Objetivo del financiamiento
    # ----------------------------------------------------
    inst_objetivos = instrumento.get_objetivos_list()
    coincidencia_objetivo_exacta = False
    
    if objetivo and objetivo != 'por_definir' and inst_objetivos and 'todos' not in inst_objetivos:
        if objetivo in inst_objetivos:
            coincidencia_objetivo_exacta = True
        else:
            # Si el instrumento tiene objetivos específicos y no coincide con el objetivo del usuario
            # Solo se excluye si hay una incompatibilidad sustancial (ej. proyecto_cultural vs fondos industriales de I+D)
            if objetivo == 'proyecto_cultural' and 'proyecto_cultural' not in inst_objetivos:
                return {
                    'instrumento': instrumento,
                    'es_pertinente_ahora': False,
                    'es_proxima_etapa': False,
                    'motivo_exclusion': 'No coincide con el objetivo de proyecto artístico o cultural.',
                }
            if objetivo == 'sostenibilidad' and 'sostenibilidad' not in inst_objetivos and 'fortalecer_negocio' not in inst_objetivos:
                # Si busca sostenibilidad, preferir instrumentos sostenibles o de crecimiento
                pass

    # ----------------------------------------------------
    # 5. Formalización ante el SII y Ventas
    # ----------------------------------------------------
    formalizacion_req = instrumento.formalizacion_requerida
    ventas_req = instrumento.ventas_requeridas

    es_pertinente_ahora = True
    es_proxima_etapa = False
    motivo_proxima_etapa = ""
    condiciones_pendientes = []

    # A. Evaluación de 1ª categoría
    if formalizacion_req == FormalizacionRequerida.SIN_INICIO_PRIMERA:
        if tiene_primera is True:
            # Exclusión: Fondo exclusivo para no formalizados (ej. Capital Semilla / Abeja tradicional)
            return {
                'instrumento': instrumento,
                'es_pertinente_ahora': False,
                'es_proxima_etapa': False,
                'motivo_exclusion': 'Diseñado exclusivamente para personas sin inicio de actividades en 1ª categoría ante el SII.',
            }
        else:
            condiciones_pendientes.append("Confirmar no registrar inicio de actividades en 1ª categoría ante el SII al momento de postular.")

    elif formalizacion_req in [FormalizacionRequerida.CON_INICIO_PRIMERA, FormalizacionRequerida.FORMALIZACION_DECLARADA]:
        if tiene_primera is False:
            es_pertinente_ahora = False
            es_proxima_etapa = True
            motivo_proxima_etapa = "Requiere tener empresa formalizada con inicio de actividades en 1ª categoría ante el SII. Tu situación actual es preparatoria para este fondo."
        elif tiene_primera is True:
            condiciones_pendientes.append("Acreditar inicio de actividades en 1ª categoría y antigüedad mínima requerida por las bases.")
        else:
            condiciones_pendientes.append("Confirmar si tu situación ante el SII cumple con inicio de actividades en 1ª categoría.")

    # B. Evaluación de Ventas
    if ventas_req == VentasRequeridas.SI:
        if tiene_ventas is False:
            if not es_proxima_etapa:
                es_pertinente_ahora = False
                es_proxima_etapa = True
                motivo_proxima_etapa = "Requiere registrar ventas comerciales demostrables según las bases de la convocatoria."
        elif tiene_ventas is True:
            condiciones_pendientes.append("Verificar tramo de ventas mínimas o máximas exigidas por la convocatoria.")
    elif ventas_req == VentasRequeridas.NO:
        if tiene_ventas is True:
            # Si el fondo exige no tener ventas del negocio
            condiciones_pendientes.append("Confirmar si las ventas declaradas no exceden el tope de elegibilidad para emprendimientos iniciales.")

    # Requisitos institucionales conocidos a advertir
    entidad_nombre = instrumento.entidad.nombre.upper()
    if 'FOSIS' in entidad_nombre:
        condiciones_pendientes.append("Registro Social de Hogares (RSH): pertenecer al tramo de vulnerabilidad exigido (habitualmente 40% a 60%).")
    elif 'SERCOTEC' in entidad_nombre:
        if 'ABEJA' in instrumento.nombre.upper():
            condiciones_pendientes.append("Postulante debe ser mujer (exclusivo para emprendedoras según bases).")
        elif 'ALMACÉN' in instrumento.nombre.upper():
            condiciones_pendientes.append("Acreditar giro comercial elegible (almacén de barrio, minimarket, rotisería o pastelería).")
    elif 'CORFO' in entidad_nombre or 'START-UP CHILE' in entidad_nombre:
        condiciones_pendientes.append("Innovación y potencial de crecimiento: requiere solución con diferenciación clara frente a la oferta existente.")
    elif 'CULTURA' in entidad_nombre:
        condiciones_pendientes.append("Verificar disciplina artística, línea de postulación y antecedentes del equipo creador.")
    elif 'FIA' in entidad_nombre:
        condiciones_pendientes.append("Impacto en el sector silvoagroalimentario o cadena de valor agropecuaria.")
    elif 'INDESPA' in entidad_nombre:
        condiciones_pendientes.append("Acreditar inscripción en Registro Pesquero Artesanal (RPA) o condición de acuicultor.")

    # Convocatoria principal a destacar
    convocatoria_principal = convocatorias_evaluadas[0] if convocatorias_evaluadas else None

    # Explicación de por qué aparece
    por_que_aparece = f"Coincide con tu búsqueda de {ETIQUETAS_OBJETIVOS.get(objetivo, 'financiamiento')}"
    if necesidades_cubiertas and 'Gastos según bases' not in necesidades_cubiertas:
        por_que_aparece += f" y financia {', '.join(necesidades_cubiertas)}."
    else:
        por_que_aparece += "."

    if instrumento.cobertura == 'nacional':
        por_que_aparece += " Cobertura nacional."
    elif region:
        por_que_aparece += f" Convocatoria aplicable a la Región de {REGIONES_CHILE.get(region, region)}."

    # Comparación de monto
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
        nota_monto = f"Aporta hasta {monto_fmt} según bases."
    else:
        nota_monto = "Monto a determinar según bases oficiales."

    vigencia_info = evaluar_vigencia_instrumento(instrumento, reference_time=reference_time)

    return {
        'instrumento': instrumento,
        'es_pertinente_ahora': es_pertinente_ahora,
        'es_proxima_etapa': es_proxima_etapa,
        'motivo_proxima_etapa': motivo_proxima_etapa,
        'por_que_aparece': por_que_aparece,
        'necesidades_cubiertas': necesidades_cubiertas,
        'coincidencia_objetivo_exacta': coincidencia_objetivo_exacta,
        'condiciones_pendientes': condiciones_pendientes[:2],  # Hasta 2 prioritarias visibles en tarjeta
        'todas_condiciones_pendientes': condiciones_pendientes,
        'nota_monto': nota_monto,
        'vigencia_info': vigencia_info,
        'convocatoria_principal': convocatoria_principal,
        'otras_convocatorias': convocatorias_evaluadas[1:] if len(convocatorias_evaluadas) > 1 else [],
    }


def generar_siguiente_paso(
    estado_actividad: str,
    objetivo: str,
    necesidades: List[str],
    pertinentes: List[Any],
    proxima_etapa: List[Any]
) -> Dict[str, Any]:
    """
    Construye la recomendación de la Sección 9 adaptada a la situación tributaria y objetivo.
    Una acción concreta y hasta tres tareas breves.
    """
    if estado_actividad in ['sin_primera_sin_ventas', 'sin_primera_con_ventas']:
        accion_principal = "Clarificar cotizaciones de inversión y revisar condiciones antes de dar inicio en el SII"
        tareas = [
            "Solicita 2 o 3 cotizaciones referenciales para los equipos o insumos que necesitas financiar.",
            "Comprueba si los fondos de tu interés exigen NO registrar inicio de actividades en 1ª categoría antes de hacer cualquier trámite.",
            "Revisa las bases de convocatorias anteriores para familiarizarte con las preguntas y requisitos de postulación."
        ]
    elif estado_actividad == 'con_primera_sin_ventas':
        accion_principal = "Validar hipótesis del negocio y preparar antecedentes del proyecto"
        tareas = [
            "Documenta tu propuesta de valor y los primeros clientes potenciales o acuerdos de prueba.",
            "Prepara un presupuesto detallado de inversión que justifique el aporte solicitado al fondo.",
            "Verifica si la convocatoria exige antigüedad mínima desde el inicio de actividades en el SII."
        ]
    elif estado_actividad == 'con_primera_con_ventas':
        accion_principal = "Descargar carpeta tributaria y cotizar la inversión de crecimiento"
        tareas = [
            "Descarga tu Carpeta Tributaria Electrónica para Solicitar Fondos desde el sitio web del SII.",
            "Verifica que las ventas de los últimos 12 o 24 meses calcen con los límites de micro o pequeña empresa del fondo.",
            "Consigue facturas proforma o cotizaciones formales de los equipos, software o infraestructura que vas a financiar."
        ]
    else:
        accion_principal = "Revisar requisitos de admisibilidad de las opciones recomendadas"
        tareas = [
            "Define exactamente qué equipos o herramientas necesitas para tu siguiente paso.",
            "Verifica las bases de la convocatoria oficial que más se ajuste a tu etapa.",
            "Confirma tu situación tributaria ante el SII antes de presentar la postulación."
        ]

    return {
        'accion_principal': accion_principal,
        'tareas': tareas[:3],
    }
