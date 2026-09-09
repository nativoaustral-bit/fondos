"""
Motor de Cálculo de Vigencia y Estado Observado
Reglas obligatorias de la Sección 10 de la especificación Humm Financiamiento.
"""

from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from django.utils import timezone
from ..models import Convocatoria, Instrumento, EstadoFuente, CierreModalidad, ConfiguracionGlobal


class CodigoEstadoCalculado:
    ABIERTA_VERIFICADA = 'abierta_verificada'
    CIERRA_HOY_CONFIRMAR_HORA = 'cierra_hoy_confirmar_hora'
    VIGENCIA_POR_CONFIRMAR = 'vigencia_por_confirmar'
    APERTURA_PREVISTA = 'apertura_prevista'
    PLAZO_FINALIZADO = 'plazo_finalizado'
    CERRADA = 'cerrada'
    SUSPENDIDA = 'suspendida'
    CANCELADA = 'cancelada'
    ANUNCIADA = 'anunciada'
    POR_CONFIRMAR = 'por_confirmar'


def get_current_time_in_zone(tz_name='America/Santiago', reference_time=None):
    """
    Retorna el datetime actual (o de referencia) en la zona horaria IANA especificada.
    """
    if reference_time is None:
        reference_time = timezone.now()

    try:
        zi = ZoneInfo(tz_name or 'America/Santiago')
    except Exception:
        zi = ZoneInfo('America/Santiago')

    return reference_time.astimezone(zi)


def calcular_estado_convocatoria(convocatoria: Convocatoria, reference_time=None, max_dias_abierta=None):
    """
    Calcula el estado mostrado al usuario en tiempo de consulta.
    Retorna un diccionario con:
      - codigo: CodigoEstadoCalculado
      - etiqueta: Texto visible
      - clase_css: Clase para badge visual (verde, ambar, rojo, neutro)
      - explicacion: Detalle o advertencia prudente
      - fecha_referencia: Fecha real de verificación o cierre
      - requiere_atencion: Booleano para el administrador
    """
    if max_dias_abierta is None:
        try:
            config = ConfiguracionGlobal.get_solo()
            max_dias_abierta = config.dias_revision_abierta
        except Exception:
            max_dias_abierta = 7

    now_tz = get_current_time_in_zone(convocatoria.zona_horaria, reference_time)
    today_tz = now_tz.date()

    # Regla 1: Suspensión o cancelación verificada prevalece sobre el calendario
    if convocatoria.estado_fuente == EstadoFuente.SUSPENDIDA:
        return {
            'codigo': CodigoEstadoCalculado.SUSPENDIDA,
            'etiqueta': 'Convocatoria suspendida',
            'clase_css': 'estado-suspendida',
            'explicacion': 'La entidad informante suspendió este llamado. Prevalece sobre el calendario original.',
            'fecha_referencia': convocatoria.estado_verificado_en,
            'requiere_atencion': True,
        }

    if convocatoria.estado_fuente == EstadoFuente.CANCELADA:
        return {
            'codigo': CodigoEstadoCalculado.CANCELADA,
            'etiqueta': 'Convocatoria cancelada',
            'clase_css': 'estado-cancelada',
            'explicacion': 'Llamado cancelado formalmente por la institución.',
            'fecha_referencia': convocatoria.estado_verificado_en,
            'requiere_atencion': True,
        }

    # Regla 2: Un cierre informado ya vencido deja de mostrarse como abierto
    if convocatoria.fecha_cierre:
        # Si tiene hora de cierre definida
        if convocatoria.hora_cierre:
            cierre_dt = datetime.combine(
                convocatoria.fecha_cierre,
                convocatoria.hora_cierre,
                tzinfo=now_tz.tzinfo
            )
            if now_tz > cierre_dt:
                return {
                    'codigo': CodigoEstadoCalculado.PLAZO_FINALIZADO,
                    'etiqueta': 'Plazo informado finalizado',
                    'clase_css': 'estado-cerrada',
                    'explicacion': f'El plazo de postulación finalizó el {convocatoria.fecha_cierre.strftime("%d-%m-%Y")} a las {convocatoria.hora_cierre.strftime("%H:%M")}.',
                    'fecha_referencia': cierre_dt,
                    'requiere_atencion': False,
                }
        else:
            # Solo se conoce la fecha del día de cierre
            if today_tz > convocatoria.fecha_cierre:
                return {
                    'codigo': CodigoEstadoCalculado.PLAZO_FINALIZADO,
                    'etiqueta': 'Plazo informado finalizado',
                    'clase_css': 'estado-cerrada',
                    'explicacion': f'El plazo de postulación venció el {convocatoria.fecha_cierre.strftime("%d-%m-%Y")}.',
                    'fecha_referencia': convocatoria.fecha_cierre,
                    'requiere_atencion': False,
                }

            # Regla 7: Si solo se conoce el día de cierre, al llegar ese día mostrar "Cierra hoy: confirmar hora"
            if today_tz == convocatoria.fecha_cierre:
                return {
                    'codigo': CodigoEstadoCalculado.CIERRA_HOY_CONFIRMAR_HORA,
                    'etiqueta': 'Cierra hoy: confirmar hora',
                    'clase_css': 'estado-atencion',
                    'explicacion': 'La convocatoria finaliza hoy, pero las bases no especifican hora exacta. Revisa antes del mediodía en la fuente oficial.',
                    'fecha_referencia': convocatoria.fecha_cierre,
                    'requiere_atencion': True,
                }

    # Si la fuente observada indicó explícitamente "cerrada"
    if convocatoria.estado_fuente == EstadoFuente.CERRADA:
        return {
            'codigo': CodigoEstadoCalculado.CERRADA,
            'etiqueta': 'Convocatoria cerrada',
            'clase_css': 'estado-cerrada',
            'explicacion': 'Convocatoria finalizada según la última revisión oficial.',
            'fecha_referencia': convocatoria.estado_verificado_en or convocatoria.fecha_cierre,
            'requiere_atencion': False,
        }

    # Regla 3: Llegar a la fecha de apertura prevista NO basta para afirmar apertura
    if convocatoria.fecha_apertura and today_tz >= convocatoria.fecha_apertura:
        # Requiere comprobación de la fuente realizada cuando ya comenzó ese período
        if not convocatoria.estado_verificado_en or convocatoria.estado_verificado_en.date() < convocatoria.fecha_apertura:
            return {
                'codigo': CodigoEstadoCalculado.APERTURA_PREVISTA,
                'etiqueta': 'Apertura prevista: confirmar vigencia',
                'clase_css': 'estado-atencion',
                'explicacion': f'El calendario indicaba inicio para el {convocatoria.fecha_apertura.strftime("%d-%m-%Y")}, pero requiere nueva comprobación oficial de apertura.',
                'fecha_referencia': convocatoria.fecha_apertura,
                'requiere_atencion': True,
            }

    # Apertura futura aún no alcanzada
    if convocatoria.fecha_apertura and today_tz < convocatoria.fecha_apertura:
        return {
            'codigo': CodigoEstadoCalculado.ANUNCIADA,
            'etiqueta': f'Apertura prevista: {convocatoria.fecha_apertura.strftime("%d-%m-%Y")}',
            'clase_css': 'estado-anunciada',
            'explicacion': f'Apertura programada para el {convocatoria.fecha_apertura.strftime("%d-%m-%Y")}. Ideal para preparar antecedentes.',
            'fecha_referencia': convocatoria.fecha_apertura,
            'requiere_atencion': False,
        }

    # Regla 6: Sin fecha de cierre definida
    if not convocatoria.fecha_cierre:
        if convocatoria.cierre_modalidad not in [CierreModalidad.PERMANENTE, CierreModalidad.HASTA_AGOTAR]:
            # No es permanente confirmada ni hasta agotar
            return {
                'codigo': CodigoEstadoCalculado.VIGENCIA_POR_CONFIRMAR,
                'etiqueta': 'Vigencia por confirmar',
                'clase_css': 'estado-atencion',
                'explicacion': 'No se informa fecha de cierre oficial ni modalidad permanente verificada.',
                'fecha_referencia': convocatoria.estado_verificado_en,
                'requiere_atencion': True,
            }

    # Regla 5: Comprobar antigüedad de la verificación de apertura (máximo X días, por defecto 7)
    if convocatoria.estado_fuente == EstadoFuente.ABIERTA:
        if convocatoria.estado_verificado_en:
            dias_desde_revision = (now_tz.date() - convocatoria.estado_verificado_en.date()).days
            if dias_desde_revision > max_dias_abierta:
                return {
                    'codigo': CodigoEstadoCalculado.VIGENCIA_POR_CONFIRMAR,
                    'etiqueta': 'Vigencia por confirmar',
                    'clase_css': 'estado-atencion',
                    'explicacion': f'Última revisión oficial hace {dias_desde_revision} días ({convocatoria.estado_verificado_en.strftime("%d-%m-%Y")}). Requiere confirmar vigencia en portal oficial.',
                    'fecha_referencia': convocatoria.estado_verificado_en,
                    'requiere_atencion': True,
                }
            else:
                # Regla 4: "Abierta verificada" con evidencia reciente
                cierre_txt = ""
                if convocatoria.fecha_cierre:
                    dias_restantes = (convocatoria.fecha_cierre - today_tz).days
                    cierre_txt = f"Cierra el {convocatoria.fecha_cierre.strftime('%d-%m-%Y')}"
                    if convocatoria.hora_cierre:
                        cierre_txt += f" a las {convocatoria.hora_cierre.strftime('%H:%M')}"
                    cierre_txt += f" ({dias_restantes} días restantes)."
                elif convocatoria.cierre_modalidad == CierreModalidad.PERMANENTE:
                    cierre_txt = "Ventanilla permanente abierta."
                elif convocatoria.cierre_modalidad == CierreModalidad.HASTA_AGOTAR:
                    cierre_txt = "Abierta hasta agotar recursos asignados."

                return {
                    'codigo': CodigoEstadoCalculado.ABIERTA_VERIFICADA,
                    'etiqueta': 'Abierta (verificada)',
                    'clase_css': 'estado-abierta',
                    'explicacion': f"{cierre_txt} Verificado oficialmente el {convocatoria.estado_verificado_en.strftime('%d-%m-%Y')}.",
                    'fecha_referencia': convocatoria.estado_verificado_en,
                    'requiere_atencion': False,
                }

    # Caso residual
    return {
        'codigo': CodigoEstadoCalculado.POR_CONFIRMAR,
        'etiqueta': 'Estado por confirmar',
        'clase_css': 'estado-atencion',
        'explicacion': 'Información pendiente de verificación oficial.',
        'fecha_referencia': convocatoria.estado_verificado_en,
        'requiere_atencion': True,
    }


def evaluar_vigencia_instrumento(instrumento: Instrumento, reference_time=None, max_dias_instrumento=None):
    """
    Regla 9: Si los datos generales del instrumento están desactualizados (> 90 días),
    mostrar "Información de referencia: requiere actualización" y no presentar su monto como oferta actual.
    """
    if max_dias_instrumento is None:
        try:
            config = ConfiguracionGlobal.get_solo()
            max_dias_instrumento = config.dias_revision_instrumento
        except Exception:
            max_dias_instrumento = 90

    if reference_time is None:
        reference_time = timezone.now()

    # Evaluar la fecha más reciente entre requisitos, montos y cobertura
    fechas = [
        f for f in [
            instrumento.requisitos_verificado_en,
            instrumento.montos_verificado_en,
            instrumento.cobertura_verificado_en
        ] if f is not None
    ]

    if not fechas:
        return {
            'desactualizado': True,
            'dias': None,
            'mensaje': 'Información de referencia: requiere actualización',
            'monto_confiable': False,
        }

    ultima_fecha = max(fechas)
    ref_date = reference_time.date() if isinstance(reference_time, datetime) else reference_time
    dias = (ref_date - ultima_fecha.date()).days

    if dias > max_dias_instrumento:
        return {
            'desactualizado': True,
            'dias': dias,
            'mensaje': f'Información de referencia: requiere actualización (última revisión hace {dias} días)',
            'monto_confiable': False,
        }

    return {
        'desactualizado': False,
        'dias': dias,
        'mensaje': f'Datos de referencia verificados el {ultima_fecha.strftime("%d-%m-%Y")}',
        'monto_confiable': True,
    }
