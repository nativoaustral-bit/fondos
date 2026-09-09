"""
Conversor de Base Inicial — Humm Financiamiento
Lee el inventario histórico (Base_fondos_no_reembolsables_Chile_MVP-2.xlsx) y genera
la base canónica normalizada en estado 'borrador' preservando fechas históricas de verificación.
"""

import io
import openpyxl
from datetime import datetime, date, time
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.utils import timezone
from ..models import (
    Entidad, Instrumento, Convocatoria, EstadoEditorial,
    TipoEntidad, CoberturaTerritorial, FormalizacionRequerida,
    TipoBeneficio, NoReembolsableConfirmado, ModalidadEntrega,
    Moneda, AporteBase, EstadoFuente, CierreModalidad
)

MAPA_REGIONES = {
    'nacional': 'todos',
    'todo chile': 'todos',
    'arica y parinacota': 'CL-AP',
    'tarapacá': 'CL-TA',
    'antofagasta': 'CL-AN',
    'atacama': 'CL-AT',
    'coquimbo': 'CL-CO',
    'valparaíso': 'CL-VA',
    'metropolitana': 'CL-RM',
    'santiago': 'CL-RM',
    "o'higgins": 'CL-OH',
    'maule': 'CL-ML',
    'ñuble': 'CL-NB',
    'biobío': 'CL-BI',
    'la araucanía': 'CL-AR',
    'los ríos': 'CL-LR',
    'los lagos': 'CL-LL',
    'aysén': 'CL-AI',
    'magallanes': 'CL-MA',
}

MAPA_SITUACIONES = {
    'idea': 'idea',
    'prototipo': 'prototipo',
    'ventas informales': 'ventas_informales',
    'ventas formales': 'ventas_formales',
    'ventas formales baja escala': 'ventas_formales',
    'microempresa': 'ventas_formales',
    'formalizado': 'ventas_formales',
}

MAPA_NECESIDADES_KEYWORDS = {
    'equipamiento': ['equipo', 'herramienta', 'maquinaria', 'activo fijo', 'tecnología', 'mobiliario'],
    'capital_trabajo': ['insumo', 'materia prima', 'capital de trabajo', 'mercadería', 'inventario', 'operación'],
    'ventas_digital': ['digital', 'marketing', 'comercial', 'difusión', 'web', 'ventas', 'ecommerce'],
    'prototipo': ['prototipo', 'validación', 'i+d', 'pilotaje', 'empaque tecnológico', 'laboratorio'],
    'infraestructura': ['habilitación', 'infraestructura', 'espacio', 'local', 'adecuación'],
    'asistencia_tecnica': ['asesoría', 'capacitación', 'asistencia técnica', 'mentoría', 'certificación'],
}


def deducir_necesidades_desde_texto(texto: str) -> str:
    if not texto:
        return 'todos'
    t = texto.lower()
    coincidencias = []
    for codigo, palabras in MAPA_NECESIDADES_KEYWORDS.items():
        if any(p in t for p in palabras):
            coincidencias.append(codigo)
    return ';'.join(coincidencias) if coincidencias else 'todos'


def mapear_etapas(etapas_str: str) -> str:
    if not etapas_str:
        return 'todos'
    t = etapas_str.lower()
    matches = set()
    for k, v in MAPA_SITUACIONES.items():
        if k in t:
            matches.add(v)
    return ';'.join(sorted(matches)) if matches else 'todos'


def mapear_formalizacion(form_str: str) -> str:
    if not form_str:
        return FormalizacionRequerida.CUALQUIERA
    t = form_str.lower()
    if 'sin inicio' in t or 'sin exigencia' in t:
        if 'sin inicio de actividades en 1ª' in t:
            return FormalizacionRequerida.SIN_INICIO_PRIMERA
        return FormalizacionRequerida.CUALQUIERA
    if 'inicio de actividades' in t or 'formal' in t:
        return FormalizacionRequerida.CON_INICIO_PRIMERA
    return FormalizacionRequerida.CUALQUIERA


def mapear_territorio(terr_str: str) -> str:
    if not terr_str:
        return 'todos'
    t = terr_str.lower().strip()
    return MAPA_REGIONES.get(t, 'todos')


def parse_date_safe(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    try:
        return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(str(val).strip(), "%d-%m-%Y").date()
        except Exception:
            return None


def convertir_base_inicial(filepath: str, publicar_directo: bool = False) -> dict:
    """
    Lee Base_fondos_no_reembolsables_Chile_MVP-2.xlsx y carga la base en Django.
    Todos los registros se cargan por defecto en 'borrador' (o 'publicado' si se solicita).
    Retorna un reporte detallado con conteos y campos no mapeados.
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    reporte = {
        'entidades_creadas': 0,
        'instrumentos_creados': 0,
        'convocatorias_creadas': 0,
        'entidades_existentes': 0,
        'instrumentos_existentes': 0,
        'convocatorias_existentes': 0,
        'advertencias': [],
        'no_mapeados': [],
    }

    estado_destino = EstadoEditorial.PUBLICADO if publicar_directo else EstadoEditorial.BORRADOR

    # 1. Mapeo de Entidades
    mapa_entidades_nombre_a_id = {}
    if 'Entidades' in wb.sheetnames:
        ws_ent = wb['Entidades']
        rows = list(ws_ent.iter_rows(values_only=True))
        if len(rows) >= 5:
            # Fila 4 tiene encabezados reales
            headers = [str(c).strip() if c else '' for c in rows[3]]
            for row in rows[4:]:
                if not any(row):
                    continue
                rd = dict(zip(headers, row))
                eid = str(rd.get('Entidad ID') or '').strip()
                nombre = str(rd.get('Entidad') or '').strip()
                if not eid or not nombre:
                    continue

                mapa_entidades_nombre_a_id[nombre.lower()] = eid
                # Mapear nombres cortos comunes
                if 'fosis' in nombre.lower():
                    mapa_entidades_nombre_a_id['fosis'] = eid
                if 'sercotec' in nombre.lower():
                    mapa_entidades_nombre_a_id['sercotec'] = eid
                if 'corfo' in nombre.lower():
                    mapa_entidades_nombre_a_id['corfo'] = eid
                if 'start-up chile' in nombre.lower():
                    mapa_entidades_nombre_a_id['start-up chile'] = eid

                ent, created = Entidad.objects.get_or_create(
                    entidad_id=eid,
                    defaults={
                        'nombre': nombre,
                        'tipo': TipoEntidad.PUBLICA,
                        'url_oficial': str(rd.get('URL oficial') or 'https://www.chileatiende.gob.cl').strip(),
                        'estado_editorial': estado_destino,
                        'poblacion_foco': str(rd.get('Población foco') or '').strip(),
                        'notas': str(rd.get('Notas') or '').strip(),
                    }
                )
                if created:
                    reporte['entidades_creadas'] += 1
                else:
                    reporte['entidades_existentes'] += 1

    # 2. Mapeo de Instrumentos
    if 'Instrumentos' in wb.sheetnames:
        ws_inst = wb['Instrumentos']
        rows = list(ws_inst.iter_rows(values_only=True))
        if len(rows) >= 5:
            headers = [str(c).strip() if c else '' for c in rows[3]]
            for row in rows[4:]:
                if not any(row):
                    continue
                rd = dict(zip(headers, row))
                iid = str(rd.get('Instrumento ID') or '').strip()
                nombre = str(rd.get('Instrumento') or '').strip()
                ent_nombre = str(rd.get('Entidad') or '').strip()
                if not iid or not nombre:
                    continue

                # Resolver entidad_id
                eid = mapa_entidades_nombre_a_id.get(ent_nombre.lower())
                if not eid:
                    # Buscar coincidencia parcial
                    for k, v in mapa_entidades_nombre_a_id.items():
                        if k in ent_nombre.lower():
                            eid = v
                            break
                if not eid:
                    eid = 'ENT-001'  # Fallback a entidad pública base
                    reporte['advertencias'].append(f"Instrumento {iid}: no se encontró entidad para '{ent_nombre}'. Asignada entidad ENT-001.")

                # Deducir criterios
                etapas = mapear_etapas(str(rd.get('Etapas Humm') or ''))
                formalizacion = mapear_formalizacion(str(rd.get('Formalización objetivo') or ''))
                que_fin = str(rd.get('Qué financia') or '').strip()
                necesidades = deducir_necesidades_desde_texto(que_fin)

                monto_max_raw = rd.get('Monto máx. CLP')
                monto_max = None
                if monto_max_raw:
                    try:
                        monto_max = Decimal(str(monto_max_raw))
                    except Exception:
                        pass

                # Fecha histórica de verificación en el archivo (2026-08-28)
                verif_raw = rd.get('Verificado')
                verif_dt = None
                verif_date = parse_date_safe(verif_raw)
                if verif_date:
                    verif_dt = timezone.make_aware(datetime.combine(verif_date, time.min), ZoneInfo('America/Santiago'))
                else:
                    # Fecha histórica de la base legacy
                    verif_dt = timezone.make_aware(datetime(2026, 8, 28, 0, 0), ZoneInfo('America/Santiago'))

                inst, created = Instrumento.objects.get_or_create(
                    instrumento_id=iid,
                    defaults={
                        'entidad_id': eid,
                        'nombre': nombre,
                        'estado_editorial': estado_destino,
                        'resumen': str(rd.get('Compatible cuando') or '').strip(),
                        'dirigido_a': str(rd.get('Perfil postulante') or '').strip(),
                        'que_financia': que_fin,
                        'que_no_financia': str(rd.get('Exclusiones/alertas') or '').strip(),
                        'requisitos_principales': str(rd.get('Requisitos clave') or '').strip(),
                        'siguiente_paso': str(rd.get('Siguiente paso') or '').strip(),
                        'necesidades': necesidades,
                        'situaciones': etapas,
                        'rubros': 'todos',
                        'cobertura': CoberturaTerritorial.NACIONAL if 'nacional' in str(rd.get('Alcance') or '').lower() else CoberturaTerritorial.REGIONAL,
                        'regiones': 'todos',
                        'formalizacion_requerida': formalizacion,
                        'tipo_beneficio': TipoBeneficio.SUBSIDIO if 'subsidio' in str(rd.get('Tipo apoyo') or '').lower() else TipoBeneficio.VOUCHER,
                        'no_reembolsable_confirmado': NoReembolsableConfirmado.SI if 'sí' in str(rd.get('No reembolsable') or '').lower() or 'si' in str(rd.get('No reembolsable') or '').lower() else NoReembolsableConfirmado.POR_CONFIRMAR,
                        'modalidad_entrega': ModalidadEntrega.ANTICIPO,
                        'monto_min': Decimal('0'),
                        'monto_max': monto_max,
                        'moneda': Moneda.CLP,
                        'monto_condiciones': str(rd.get('Aporte postulante') or '').strip(),
                        'url_programa': str(rd.get('URL oficial') or '').strip(),
                        'requisitos_verificado_en': verif_dt,
                        'montos_verificado_en': verif_dt,
                        'cobertura_verificado_en': verif_dt,
                        'evidencia_verificacion': f"Importado desde inventario legacy. Frecuencia: {rd.get('Periodicidad') or 'Semanal'}. Prioridad: {rd.get('Prioridad MVP') or 'Alta'}.",
                    }
                )
                if created:
                    reporte['instrumentos_creados'] += 1
                else:
                    reporte['instrumentos_existentes'] += 1

    # 3. Mapeo de Convocatorias
    if 'Convocatorias' in wb.sheetnames:
        ws_conv = wb['Convocatorias']
        rows = list(ws_conv.iter_rows(values_only=True))
        if len(rows) >= 5:
            headers = [str(c).strip() if c else '' for c in rows[3]]
            for row in rows[4:]:
                if not any(row):
                    continue
                rd = dict(zip(headers, row))
                cid = str(rd.get('Convocatoria ID') or '').strip()
                iid = str(rd.get('Instrumento ID') or '').strip()
                nombre = str(rd.get('Convocatoria') or '').strip()
                if not cid or not iid or not nombre:
                    continue

                if not Instrumento.objects.filter(instrumento_id=iid).exists():
                    reporte['advertencias'].append(f"Convocatoria {cid}: Instrumento {iid} no existe. Omitida.")
                    continue

                f_aper = parse_date_safe(rd.get('Apertura'))
                f_cierre = parse_date_safe(rd.get('Cierre'))
                estado_txt = str(rd.get('Estado') or '').lower().strip()
                estado_fuente = EstadoFuente.POR_CONFIRMAR
                if 'abierta' in estado_txt:
                    estado_fuente = EstadoFuente.ABIERTA
                elif 'cerrada' in estado_txt:
                    estado_fuente = EstadoFuente.CERRADA
                elif 'anunciada' in estado_txt:
                    estado_fuente = EstadoFuente.ANUNCIADA

                terr = mapear_territorio(str(rd.get('Territorio') or ''))

                monto_max_raw = rd.get('Monto máx. CLP')
                monto_max = None
                if monto_max_raw:
                    try:
                        monto_max = Decimal(str(monto_max_raw))
                    except Exception:
                        pass

                verif_raw = rd.get('Verificado')
                verif_date = parse_date_safe(verif_raw)
                if verif_date:
                    verif_dt = timezone.make_aware(datetime.combine(verif_date, time.min), ZoneInfo('America/Santiago'))
                else:
                    verif_dt = timezone.make_aware(datetime(2026, 8, 28, 0, 0), ZoneInfo('America/Santiago'))

                conv, created = Convocatoria.objects.get_or_create(
                    convocatoria_id=cid,
                    defaults={
                        'instrumento_id': iid,
                        'nombre': nombre,
                        'estado_editorial': estado_destino,
                        'dirigido_a': 'HEREDAR',
                        'que_financia': 'HEREDAR',
                        'que_no_financia': 'HEREDAR',
                        'requisitos_principales': str(rd.get('Elegibilidad clave') or 'HEREDAR').strip(),
                        'necesidades': 'HEREDAR',
                        'situaciones': 'HEREDAR',
                        'rubros': 'HEREDAR',
                        'cobertura': 'nacional' if terr == 'todos' else 'regional',
                        'regiones': terr,
                        'formalizacion_requerida': 'HEREDAR',
                        'modalidad_entrega': 'HEREDAR',
                        'monto_max': monto_max,
                        'moneda': Moneda.CLP,
                        'monto_condiciones': str(rd.get('Aporte') or '').strip(),
                        'fecha_apertura': f_aper,
                        'fecha_cierre': f_cierre,
                        'zona_horaria': 'America/Santiago' if terr != 'CL-MA' else 'America/Punta_Arenas',
                        'cierre_modalidad': CierreModalidad.FECHA_DEFINIDA if f_cierre else CierreModalidad.SIN_CONFIRMAR,
                        'estado_fuente': estado_fuente,
                        'url_convocatoria': str(rd.get('URL oficial') or '').strip(),
                        'requisitos_verificado_en': verif_dt,
                        'montos_verificado_en': verif_dt,
                        'cobertura_verificado_en': verif_dt,
                        'fechas_verificado_en': verif_dt,
                        'estado_verificado_en': verif_dt,
                        'evidencia_verificacion': f"Alerta: {rd.get('Alerta excluyente') or 'Ninguna'}. Días restantes reportados: {rd.get('Días restantes') or 'N/A'}.",
                    }
                )
                if created:
                    reporte['convocatorias_creadas'] += 1
                else:
                    reporte['convocatorias_existentes'] += 1

    return reporte
