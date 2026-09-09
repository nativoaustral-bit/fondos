"""
Contrato Excel (.xlsx) — Humm Financiamiento
Generación de plantilla, exportador de catálogo, validación estricta,
previsualización de diferencias (diffs) y aplicación atómica con reversión.
"""

import io
import hashlib
from datetime import datetime, date, time
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.db import transaction
from django.utils import timezone
from zoneinfo import ZoneInfo

from ..models import (
    Entidad, Instrumento, Convocatoria, ConfiguracionGlobal,
    ImportacionLote, EstadoLote, EstadoEditorial, TipoEntidad,
    CoberturaTerritorial, FormalizacionRequerida, TipoBeneficio,
    NoReembolsableConfirmado, ModalidadEntrega, Moneda, AporteBase,
    EstadoFuente, CierreModalidad
)

SCHEMA_VERSION = "1.0"

COLUMNAS_CONTROL = ['schema_version', 'catalog_base_version', 'exported_at']

COLUMNAS_ENTIDADES = [
    'entidad_id', 'nombre', 'tipo', 'url_oficial', 'estado_editorial'
]

COLUMNAS_INSTRUMENTOS = [
    'instrumento_id', 'entidad_id', 'nombre', 'estado_editorial',
    'resumen', 'dirigido_a', 'que_financia', 'que_no_financia',
    'requisitos_principales', 'siguiente_paso',
    'necesidades', 'situaciones', 'rubros', 'cobertura', 'regiones', 'comunas',
    'formalizacion_requerida',
    'tipo_beneficio', 'no_reembolsable_confirmado', 'modalidad_entrega',
    'monto_min', 'monto_max', 'moneda', 'monto_condiciones',
    'aporte_pct', 'aporte_base', 'aporte_descripcion',
    'url_programa', 'requisitos_verificado_en', 'montos_verificado_en',
    'cobertura_verificado_en', 'evidencia_verificacion'
]

COLUMNAS_CONVOCATORIAS = [
    'convocatoria_id', 'instrumento_id', 'nombre', 'estado_editorial',
    'dirigido_a', 'que_financia', 'que_no_financia', 'requisitos_principales',
    'necesidades', 'situaciones', 'rubros', 'cobertura', 'regiones', 'comunas',
    'formalizacion_requerida',
    'modalidad_entrega', 'monto_min', 'monto_max', 'moneda', 'monto_condiciones',
    'aporte_pct', 'aporte_base', 'aporte_descripcion',
    'fecha_apertura', 'hora_apertura', 'fecha_cierre', 'hora_cierre',
    'zona_horaria', 'cierre_modalidad',
    'estado_fuente', 'url_convocatoria',
    'requisitos_verificado_en', 'montos_verificado_en', 'cobertura_verificado_en',
    'fechas_verificado_en', 'estado_verificado_en', 'evidencia_verificacion'
]


def format_iso_datetime(dt):
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.isoformat()
    if isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def parse_iso_datetime(val):
    if not val or val == '__BORRAR__':
        return None
    if isinstance(val, datetime):
        if timezone.is_naive(val):
            return timezone.make_aware(val, ZoneInfo('America/Santiago'))
        return val
    if isinstance(val, date):
        dt = datetime.combine(val, time.min)
        return timezone.make_aware(dt, ZoneInfo('America/Santiago'))

    s = str(val).strip()
    try:
        dt = datetime.fromisoformat(s)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, ZoneInfo('America/Santiago'))
        return dt
    except Exception:
        try:
            d = datetime.strptime(s, "%Y-%m-%d").date()
            dt = datetime.combine(d, time.min)
            return timezone.make_aware(dt, ZoneInfo('America/Santiago'))
        except Exception:
            return None


def parse_iso_date(val):
    if not val or val == '__BORRAR__':
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return None


def parse_time(val):
    if not val or val == '__BORRAR__':
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, datetime):
        return val.time()
    s = str(val).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            pass
    return None


def parse_decimal(val):
    if val is None or val == '' or val == '__BORRAR__':
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    s = str(val).strip().replace('$', '').replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except Exception:
        return None


def generar_excel_catalogo(incluir_datos=True):
    """
    Genera un archivo .xlsx canónico con las 5 hojas estándar:
    Control, Entidades, Instrumentos, Convocatorias y Diccionario.
    """
    wb = openpyxl.Workbook()
    # Eliminar hoja por defecto
    wb.remove(wb.active)

    config = ConfiguracionGlobal.get_solo()
    base_version = config.version_catalogo

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="245C50", end_color="245C50", fill_type="solid")  # Verde petróleo Humm
    control_fill = PatternFill(start_color="203B36", end_color="203B36", fill_type="solid")

    # 1. Hoja Control
    ws_ctrl = wb.create_sheet(title="Control")
    ws_ctrl.append(COLUMNAS_CONTROL)
    for cell in ws_ctrl[1]:
        cell.font = header_font
        cell.fill = control_fill
    ws_ctrl.append([SCHEMA_VERSION, base_version, timezone.now().isoformat()])

    # 2. Hoja Entidades
    ws_ent = wb.create_sheet(title="Entidades")
    ws_ent.append(COLUMNAS_ENTIDADES)
    for cell in ws_ent[1]:
        cell.font = header_font
        cell.fill = header_fill

    if incluir_datos:
        for ent in Entidad.objects.all().order_by('entidad_id'):
            ws_ent.append([
                ent.entidad_id, ent.nombre, ent.tipo, ent.url_oficial, ent.estado_editorial
            ])

    # 3. Hoja Instrumentos
    ws_inst = wb.create_sheet(title="Instrumentos")
    ws_inst.append(COLUMNAS_INSTRUMENTOS)
    for cell in ws_inst[1]:
        cell.font = header_font
        cell.fill = header_fill

    if incluir_datos:
        for inst in Instrumento.objects.all().select_related('entidad').order_by('instrumento_id'):
            ws_inst.append([
                inst.instrumento_id,
                inst.entidad_id,
                inst.nombre,
                inst.estado_editorial,
                inst.resumen,
                inst.dirigido_a,
                inst.que_financia,
                inst.que_no_financia,
                inst.requisitos_principales,
                inst.siguiente_paso,
                inst.necesidades,
                inst.situaciones,
                inst.rubros,
                inst.cobertura,
                inst.regiones,
                inst.comunas,
                inst.formalizacion_requerida,
                inst.tipo_beneficio,
                inst.no_reembolsable_confirmado,
                inst.modalidad_entrega,
                inst.monto_min,
                inst.monto_max,
                inst.moneda,
                inst.monto_condiciones,
                inst.aporte_pct,
                inst.aporte_base,
                inst.aporte_descripcion,
                inst.url_programa,
                format_iso_datetime(inst.requisitos_verificado_en),
                format_iso_datetime(inst.montos_verificado_en),
                format_iso_datetime(inst.cobertura_verificado_en),
                inst.evidencia_verificacion,
            ])

    # 4. Hoja Convocatorias
    ws_conv = wb.create_sheet(title="Convocatorias")
    ws_conv.append(COLUMNAS_CONVOCATORIAS)
    for cell in ws_conv[1]:
        cell.font = header_font
        cell.fill = header_fill

    if incluir_datos:
        for conv in Convocatoria.objects.all().select_related('instrumento').order_by('convocatoria_id'):
            ws_conv.append([
                conv.convocatoria_id,
                conv.instrumento_id,
                conv.nombre,
                conv.estado_editorial,
                conv.dirigido_a,
                conv.que_financia,
                conv.que_no_financia,
                conv.requisitos_principales,
                conv.necesidades,
                conv.situaciones,
                conv.rubros,
                conv.cobertura,
                conv.regiones,
                conv.comunas,
                conv.formalizacion_requerida,
                conv.modalidad_entrega,
                conv.monto_min,
                conv.monto_max,
                conv.moneda,
                conv.monto_condiciones,
                conv.aporte_pct,
                conv.aporte_base,
                conv.aporte_descripcion,
                format_iso_datetime(conv.fecha_apertura),
                conv.hora_apertura.strftime("%H:%M") if conv.hora_apertura else "",
                format_iso_datetime(conv.fecha_cierre),
                conv.hora_cierre.strftime("%H:%M") if conv.hora_cierre else "",
                conv.zona_horaria,
                conv.cierre_modalidad,
                conv.estado_fuente,
                conv.url_convocatoria,
                format_iso_datetime(conv.requisitos_verificado_en),
                format_iso_datetime(conv.montos_verificado_en),
                format_iso_datetime(conv.cobertura_verificado_en),
                format_iso_datetime(conv.fechas_verificado_en),
                format_iso_datetime(conv.estado_verificado_en),
                conv.evidencia_verificacion,
            ])

    # 5. Hoja Diccionario
    ws_dic = wb.create_sheet(title="Diccionario")
    ws_dic.append(['Hoja', 'Campo / Columna', 'Tipo', 'Obligatorio', 'Valores permitidos / Convenciones', 'Descripción'])
    for cell in ws_dic[1]:
        cell.font = header_font
        cell.fill = PatternFill(start_color="52665F", end_color="52665F", fill_type="solid")

    filas_diccionario = [
        ('General', 'HEREDAR', 'Texto clave', 'Opcional en Convocatoria', 'HEREDAR', 'Toma automáticamente el valor definido en el instrumento padre.'),
        ('General', '__BORRAR__', 'Texto clave', 'Opcional', '__BORRAR__', 'Elimina expresamente el valor de un campo opcional existente.'),
        ('General', 'Celda vacía', '-', '-', '-', 'En actualización conserva el valor anterior. En registro nuevo deja dato desconocido.'),
        ('Entidades', 'estado_editorial', 'Código', 'Sí', 'borrador, publicado, archivado', 'Solo publicado es visible al público.'),
        ('Instrumentos', 'no_reembolsable_confirmado', 'Código', 'Sí', 'si, no, por_confirmar', 'Solo "si" puede publicarse en el catálogo del MVP.'),
        ('Instrumentos', 'cobertura', 'Código', 'Sí', 'nacional, regional, comunal, por_confirmar', 'Alcance territorial del programa.'),
        ('Instrumentos', 'formalizacion_requerida', 'Código', 'Sí', 'cualquiera, formalizacion_declarada, sin_inicio_primera, con_inicio_primera, por_confirmar', 'Condición tributaria requerida.'),
        ('Convocatorias', 'estado_fuente', 'Código', 'Sí', 'anunciada, abierta, cerrada, suspendida, cancelada, por_confirmar', 'Estado observado en la fuente oficial.'),
        ('Convocatorias', 'cierre_modalidad', 'Código', 'Sí', 'fecha_definida, permanente, hasta_agotar, sin_confirmar', 'Modalidad de cierre del llamado.'),
        ('Fechas', '*_verificado_en', 'Fecha ISO', 'Opcional', 'YYYY-MM-DDTHH:MM:SSZ o YYYY-MM-DD', 'Fecha real de comprobación del grupo de datos.'),
    ]
    for r in filas_diccionario:
        ws_dic.append(list(r))

    # Autoajustar ancho de columnas
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def validar_y_previsualizar_excel(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Analiza un archivo Excel cargado contra la base de datos:
    - Comprueba versión de esquema y versión de catálogo base (detecta colisiones concurrentes).
    - Valida tipos, códigos, relaciones foráneas, coherencia de fechas y montos.
    - Genera previsualización de diferencias (diffs) por hoja y registro:
      nuevos, modificados (campo por campo), sin cambios, errores bloqueantes y advertencias.
    """
    archivo_hash = hashlib.sha256(file_content).hexdigest()
    wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)

    errores = []
    advertencias = []

    # Verificar hojas requeridas
    hojas_requeridas = ['Control', 'Entidades', 'Instrumentos', 'Convocatorias']
    for h in hojas_requeridas:
        if h not in wb.sheetnames:
            errores.append(f"Falta la hoja obligatoria '{h}' en el archivo.")

    if errores:
        return {
            'valido': False,
            'errores': errores,
            'advertencias': advertencias,
            'archivo_hash': archivo_hash,
            'archivo_nombre': filename,
        }

    # 1. Validar Control
    ws_ctrl = wb['Control']
    control_data = {}
    rows_ctrl = list(ws_ctrl.iter_rows(values_only=True))
    if len(rows_ctrl) >= 2:
        headers = [str(c).strip() for c in rows_ctrl[0] if c]
        values = rows_ctrl[1]
        for k, v in zip(headers, values):
            control_data[k] = v

    schema_ver = str(control_data.get('schema_version', '')).strip()
    if schema_ver != SCHEMA_VERSION:
        advertencias.append(f"Versión de esquema del archivo ({schema_ver}) difiere de la esperada ({SCHEMA_VERSION}).")

    config = ConfiguracionGlobal.get_solo()
    base_ver_archivo = control_data.get('catalog_base_version')
    try:
        base_ver_archivo = int(base_ver_archivo)
    except (ValueError, TypeError):
        base_ver_archivo = 0

    # Detección de colisión concurrente
    colision_version = False
    if base_ver_archivo != config.version_catalogo:
        colision_version = True
        advertencias.append(
            f"El archivo fue exportado desde la versión {base_ver_archivo}, pero la base actual está en la versión {config.version_catalogo}. "
            "Existen cambios intermedios que podrían sobrescribirse."
        )

    # 2. Procesar Entidades
    entidades_nuevas = []
    entidades_modificadas = []
    entidades_sin_cambio = 0
    ids_entidad_archivo = set()

    ws_ent = wb['Entidades']
    rows_ent = list(ws_ent.iter_rows(values_only=True))
    if len(rows_ent) >= 2:
        ent_headers = [str(c).strip() for c in rows_ent[0] if c]
        for row_idx, row in enumerate(rows_ent[1:], start=2):
            if not any(row):
                continue
            row_dict = dict(zip(ent_headers, row))
            ent_id = str(row_dict.get('entidad_id') or '').strip()
            if not ent_id:
                errores.append(f"Hoja Entidades, fila {row_idx}: 'entidad_id' no puede estar vacío.")
                continue

            if ent_id in ids_entidad_archivo:
                errores.append(f"Hoja Entidades, fila {row_idx}: ID duplicado '{ent_id}'.")
            ids_entidad_archivo.add(ent_id)

            nombre = str(row_dict.get('nombre') or '').strip()
            tipo = str(row_dict.get('tipo') or 'publica').strip().lower()
            url_oficial = str(row_dict.get('url_oficial') or '').strip()
            estado_ed = str(row_dict.get('estado_editorial') or 'borrador').strip().lower()

            # Verificar si existe en la BD
            try:
                ent_existente = Entidad.objects.get(entidad_id=ent_id)
                cambios = {}
                if nombre and nombre != '__BORRAR__' and nombre != ent_existente.nombre:
                    cambios['nombre'] = {'anterior': ent_existente.nombre, 'propuesto': nombre}
                if tipo and tipo != ent_existente.tipo:
                    cambios['tipo'] = {'anterior': ent_existente.tipo, 'propuesto': tipo}
                if url_oficial and url_oficial != ent_existente.url_oficial:
                    cambios['url_oficial'] = {'anterior': ent_existente.url_oficial, 'propuesto': url_oficial}
                if estado_ed and estado_ed != ent_existente.estado_editorial:
                    cambios['estado_editorial'] = {'anterior': ent_existente.estado_editorial, 'propuesto': estado_ed}

                if cambios:
                    entidades_modificadas.append({
                        'id': ent_id,
                        'nombre': ent_existente.nombre,
                        'cambios': cambios,
                        'fila': row_idx
                    })
                else:
                    entidades_sin_cambio += 1
            except Entidad.DoesNotExist:
                entidades_nuevas.append({
                    'id': ent_id,
                    'nombre': nombre,
                    'tipo': tipo,
                    'url_oficial': url_oficial,
                    'estado_editorial': estado_ed,
                    'fila': row_idx
                })

    # 3. Procesar Instrumentos
    instrumentos_nuevos = []
    instrumentos_modificados = []
    instrumentos_sin_cambio = 0
    ids_inst_archivo = set()

    ws_inst = wb['Instrumentos']
    rows_inst = list(ws_inst.iter_rows(values_only=True))
    if len(rows_inst) >= 2:
        inst_headers = [str(c).strip() for c in rows_inst[0] if c]
        for row_idx, row in enumerate(rows_inst[1:], start=2):
            if not any(row):
                continue
            row_dict = dict(zip(inst_headers, row))
            inst_id = str(row_dict.get('instrumento_id') or '').strip()
            if not inst_id:
                errores.append(f"Hoja Instrumentos, fila {row_idx}: 'instrumento_id' no puede estar vacío.")
                continue

            if inst_id in ids_inst_archivo:
                errores.append(f"Hoja Instrumentos, fila {row_idx}: ID duplicado '{inst_id}'.")
            ids_inst_archivo.add(inst_id)

            ent_id = str(row_dict.get('entidad_id') or '').strip()
            # Validar relación de entidad
            if ent_id not in ids_entidad_archivo and not Entidad.objects.filter(entidad_id=ent_id).exists():
                errores.append(f"Hoja Instrumentos, fila {row_idx} ({inst_id}): entidad '{ent_id}' no existe en la base ni en el archivo.")

            nombre = str(row_dict.get('nombre') or '').strip()
            estado_ed = str(row_dict.get('estado_editorial') or 'borrador').strip().lower()
            no_reemb = str(row_dict.get('no_reembolsable_confirmado') or 'por_confirmar').strip().lower()

            if estado_ed == 'publicado' and no_reemb != 'si':
                errores.append(f"Hoja Instrumentos, fila {row_idx} ({inst_id}): No se puede publicar un instrumento sin confirmación de naturaleza no reembolsable ('si').")

            # Comparar cambios
            try:
                inst_existente = Instrumento.objects.get(instrumento_id=inst_id)
                cambios = {}
                campos_a_revisar = [
                    ('nombre', nombre),
                    ('estado_editorial', estado_ed),
                    ('resumen', row_dict.get('resumen')),
                    ('dirigido_a', row_dict.get('dirigido_a')),
                    ('que_financia', row_dict.get('que_financia')),
                    ('que_no_financia', row_dict.get('que_no_financia')),
                    ('requisitos_principales', row_dict.get('requisitos_principales')),
                    ('necesidades', row_dict.get('necesidades')),
                    ('situaciones', row_dict.get('situaciones')),
                    ('rubros', row_dict.get('rubros')),
                    ('cobertura', row_dict.get('cobertura')),
                    ('regiones', row_dict.get('regiones')),
                    ('formalizacion_requerida', row_dict.get('formalizacion_requerida')),
                    ('no_reembolsable_confirmado', no_reemb),
                    ('monto_min', parse_decimal(row_dict.get('monto_min'))),
                    ('monto_max', parse_decimal(row_dict.get('monto_max'))),
                    ('moneda', row_dict.get('moneda')),
                    ('aporte_pct', parse_decimal(row_dict.get('aporte_pct'))),
                ]
                for campo, valor_prop in campos_a_revisar:
                    if valor_prop is not None and valor_prop != '':
                        valor_ant = getattr(inst_existente, campo)
                        if valor_prop == '__BORRAR__':
                            if valor_ant:
                                cambios[campo] = {'anterior': str(valor_ant), 'propuesto': '(borrado)'}
                        elif valor_prop != valor_ant:
                            cambios[campo] = {'anterior': str(valor_ant), 'propuesto': str(valor_prop)}

                if cambios:
                    instrumentos_modificados.append({
                        'id': inst_id,
                        'nombre': inst_existente.nombre,
                        'cambios': cambios,
                        'fila': row_idx
                    })
                else:
                    instrumentos_sin_cambio += 1
            except Instrumento.DoesNotExist:
                instrumentos_nuevos.append({
                    'id': inst_id,
                    'nombre': nombre,
                    'entidad_id': ent_id,
                    'estado_editorial': estado_ed,
                    'fila': row_idx
                })

    # 4. Procesar Convocatorias
    convocatorias_nuevas = []
    convocatorias_modificadas = []
    convocatorias_sin_cambio = 0
    ids_conv_archivo = set()

    ws_conv = wb['Convocatorias']
    rows_conv = list(ws_conv.iter_rows(values_only=True))
    if len(rows_conv) >= 2:
        conv_headers = [str(c).strip() for c in rows_conv[0] if c]
        for row_idx, row in enumerate(rows_conv[1:], start=2):
            if not any(row):
                continue
            row_dict = dict(zip(conv_headers, row))
            conv_id = str(row_dict.get('convocatoria_id') or '').strip()
            if not conv_id:
                errores.append(f"Hoja Convocatorias, fila {row_idx}: 'convocatoria_id' no puede estar vacío.")
                continue

            if conv_id in ids_conv_archivo:
                errores.append(f"Hoja Convocatorias, fila {row_idx}: ID duplicado '{conv_id}'.")
            ids_conv_archivo.add(conv_id)

            inst_id = str(row_dict.get('instrumento_id') or '').strip()
            if inst_id not in ids_inst_archivo and not Instrumento.objects.filter(instrumento_id=inst_id).exists():
                errores.append(f"Hoja Convocatorias, fila {row_idx} ({conv_id}): instrumento '{inst_id}' no existe.")

            nombre = str(row_dict.get('nombre') or '').strip()
            f_apertura = parse_iso_date(row_dict.get('fecha_apertura'))
            f_cierre = parse_iso_date(row_dict.get('fecha_cierre'))

            if f_apertura and f_cierre and f_cierre < f_apertura:
                errores.append(f"Hoja Convocatorias, fila {row_idx} ({conv_id}): Fecha de cierre ({f_cierre}) anterior a fecha de apertura ({f_apertura}).")

            # Comparar cambios
            try:
                conv_existente = Convocatoria.objects.get(convocatoria_id=conv_id)
                cambios = {}
                campos_conv = [
                    ('nombre', nombre),
                    ('estado_editorial', row_dict.get('estado_editorial')),
                    ('estado_fuente', row_dict.get('estado_fuente')),
                    ('fecha_apertura', f_apertura),
                    ('fecha_cierre', f_cierre),
                    ('monto_max', parse_decimal(row_dict.get('monto_max'))),
                    ('moneda', row_dict.get('moneda')),
                    ('url_convocatoria', row_dict.get('url_convocatoria')),
                ]
                for campo, valor_prop in campos_conv:
                    if valor_prop is not None and valor_prop != '':
                        valor_ant = getattr(conv_existente, campo)
                        if valor_prop == '__BORRAR__':
                            if valor_ant:
                                cambios[campo] = {'anterior': str(valor_ant), 'propuesto': '(borrado)'}
                        elif valor_prop != valor_ant:
                            cambios[campo] = {'anterior': str(valor_ant), 'propuesto': str(valor_prop)}

                if cambios:
                    convocatorias_modificadas.append({
                        'id': conv_id,
                        'nombre': conv_existente.nombre,
                        'cambios': cambios,
                        'fila': row_idx
                    })
                else:
                    convocatorias_sin_cambio += 1
            except Convocatoria.DoesNotExist:
                convocatorias_nuevas.append({
                    'id': conv_id,
                    'nombre': nombre,
                    'instrumento_id': inst_id,
                    'fila': row_idx
                })

    es_valido = (len(errores) == 0)

    resumen = {
        'valido': es_valido,
        'errores': errores,
        'advertencias': advertencias,
        'colision_version': colision_version,
        'version_archivo': base_ver_archivo,
        'version_actual': config.version_catalogo,
        'archivo_hash': archivo_hash,
        'archivo_nombre': filename,
        'conteo': {
            'entidades': {
                'nuevas': len(entidades_nuevas),
                'modificadas': len(entidades_modificadas),
                'sin_cambio': entidades_sin_cambio,
            },
            'instrumentos': {
                'nuevos': len(instrumentos_nuevos),
                'modificados': len(instrumentos_modificados),
                'sin_cambio': instrumentos_sin_cambio,
            },
            'convocatorias': {
                'nuevas': len(convocatorias_nuevas),
                'modificadas': len(convocatorias_modificadas),
                'sin_cambio': convocatorias_sin_cambio,
            },
        },
        'diferencias': {
            'entidades_nuevas': entidades_nuevas,
            'entidades_modificadas': entidades_modificadas,
            'instrumentos_nuevos': instrumentos_nuevos,
            'instrumentos_modificados': instrumentos_modificados,
            'convocatorias_nuevas': convocatorias_nuevas,
            'convocatorias_modificadas': convocatorias_modificadas,
        }
    }

    return resumen


@transaction.atomic
def aplicar_actualizacion_excel(file_content: bytes, filename: str, usuario: str) -> ImportacionLote:
    """
    Aplica atómicamente todos los cambios del archivo validado.
    Incrementa la versión de catálogo y registra el lote de importación para auditoría/rollback.
    """
    previa = validar_y_previsualizar_excel(file_content, filename)
    if not previa['valido']:
        raise ValueError(f"No se puede aplicar: {'; '.join(previa['errores'])}")

    wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    config = ConfiguracionGlobal.get_solo()
    ver_anterior = config.version_catalogo
    ver_nueva = ver_anterior + 1

    # 1. Aplicar Entidades
    ws_ent = wb['Entidades']
    rows_ent = list(ws_ent.iter_rows(values_only=True))
    ent_headers = [str(c).strip() for c in rows_ent[0] if c]
    for row in rows_ent[1:]:
        if not any(row):
            continue
        rd = dict(zip(ent_headers, row))
        eid = str(rd.get('entidad_id') or '').strip()
        if not eid:
            continue

        ent, created = Entidad.objects.get_or_create(entidad_id=eid)
        if rd.get('nombre'):
            ent.nombre = str(rd['nombre']).strip()
        if rd.get('tipo'):
            ent.tipo = str(rd['tipo']).strip().lower()
        if rd.get('url_oficial'):
            ent.url_oficial = str(rd['url_oficial']).strip()
        if rd.get('estado_editorial'):
            ent.estado_editorial = str(rd['estado_editorial']).strip().lower()
        ent.save()

    # 2. Aplicar Instrumentos
    ws_inst = wb['Instrumentos']
    rows_inst = list(ws_inst.iter_rows(values_only=True))
    inst_headers = [str(c).strip() for c in rows_inst[0] if c]
    for row in rows_inst[1:]:
        if not any(row):
            continue
        rd = dict(zip(inst_headers, row))
        iid = str(rd.get('instrumento_id') or '').strip()
        if not iid:
            continue

        ent_id = str(rd.get('entidad_id') or '').strip()
        inst, created = Instrumento.objects.get_or_create(
            instrumento_id=iid,
            defaults={'entidad_id': ent_id, 'nombre': str(rd.get('nombre') or iid).strip()}
        )
        if ent_id:
            inst.entidad_id = ent_id
        if rd.get('nombre'):
            inst.nombre = str(rd['nombre']).strip()
        if rd.get('estado_editorial'):
            inst.estado_editorial = str(rd['estado_editorial']).strip().lower()

        # Textos descriptivos (respeta __BORRAR__)
        for fld in ['resumen', 'dirigido_a', 'que_financia', 'que_no_financia', 'requisitos_principales', 'siguiente_paso']:
            val = rd.get(fld)
            if val == '__BORRAR__':
                setattr(inst, fld, '')
            elif val is not None and val != '':
                setattr(inst, fld, str(val).strip())

        # Criterios
        for fld in ['necesidades', 'situaciones', 'rubros', 'cobertura', 'regiones', 'comunas', 'formalizacion_requerida']:
            val = rd.get(fld)
            if val == '__BORRAR__':
                setattr(inst, fld, 'todos' if fld in ['necesidades', 'situaciones', 'rubros', 'regiones'] else '')
            elif val is not None and val != '':
                setattr(inst, fld, str(val).strip())

        # Beneficio y montos
        if rd.get('tipo_beneficio'):
            inst.tipo_beneficio = str(rd['tipo_beneficio']).strip().lower()
        if rd.get('no_reembolsable_confirmado'):
            inst.no_reembolsable_confirmado = str(rd['no_reembolsable_confirmado']).strip().lower()
        if rd.get('modalidad_entrega'):
            inst.modalidad_entrega = str(rd['modalidad_entrega']).strip().lower()

        for fld in ['monto_min', 'monto_max', 'aporte_pct']:
            val = rd.get(fld)
            if val == '__BORRAR__':
                setattr(inst, fld, None)
            elif val is not None and val != '':
                setattr(inst, fld, parse_decimal(val))

        if rd.get('moneda'):
            inst.moneda = str(rd['moneda']).strip().upper()
        if rd.get('monto_condiciones'):
            inst.monto_condiciones = '' if rd['monto_condiciones'] == '__BORRAR__' else str(rd['monto_condiciones']).strip()
        if rd.get('aporte_base'):
            inst.aporte_base = str(rd['aporte_base']).strip().lower()
        if rd.get('aporte_descripcion'):
            inst.aporte_descripcion = '' if rd['aporte_descripcion'] == '__BORRAR__' else str(rd['aporte_descripcion']).strip()
        if rd.get('url_programa'):
            inst.url_programa = str(rd['url_programa']).strip()

        # Verificaciones
        for fld in ['requisitos_verificado_en', 'montos_verificado_en', 'cobertura_verificado_en']:
            val = rd.get(fld)
            if val is not None and val != '':
                parsed_dt = parse_iso_datetime(val)
                if parsed_dt:
                    setattr(inst, fld, parsed_dt)

        if rd.get('evidencia_verificacion'):
            inst.evidencia_verificacion = str(rd['evidencia_verificacion']).strip()

        inst.save()

    # 3. Aplicar Convocatorias
    ws_conv = wb['Convocatorias']
    rows_conv = list(ws_conv.iter_rows(values_only=True))
    conv_headers = [str(c).strip() for c in rows_conv[0] if c]
    for row in rows_conv[1:]:
        if not any(row):
            continue
        rd = dict(zip(conv_headers, row))
        cid = str(rd.get('convocatoria_id') or '').strip()
        if not cid:
            continue

        inst_id = str(rd.get('instrumento_id') or '').strip()
        conv, created = Convocatoria.objects.get_or_create(
            convocatoria_id=cid,
            defaults={'instrumento_id': inst_id, 'nombre': str(rd.get('nombre') or cid).strip()}
        )
        if inst_id:
            conv.instrumento_id = inst_id
        if rd.get('nombre'):
            conv.nombre = str(rd['nombre']).strip()
        if rd.get('estado_editorial'):
            conv.estado_editorial = str(rd['estado_editorial']).strip().lower()

        # Campos que admiten HEREDAR
        for fld in ['dirigido_a', 'que_financia', 'que_no_financia', 'requisitos_principales',
                    'necesidades', 'situaciones', 'rubros', 'cobertura', 'regiones', 'comunas',
                    'formalizacion_requerida', 'modalidad_entrega']:
            val = rd.get(fld)
            if val is not None and val != '':
                setattr(conv, fld, str(val).strip())

        for fld in ['monto_min', 'monto_max', 'aporte_pct']:
            val = rd.get(fld)
            if val == '__BORRAR__':
                setattr(conv, fld, None)
            elif val is not None and val != '':
                setattr(conv, fld, parse_decimal(val))

        if rd.get('moneda'):
            conv.moneda = str(rd['moneda']).strip().upper()
        if rd.get('monto_condiciones'):
            conv.monto_condiciones = str(rd['monto_condiciones']).strip()
        if rd.get('aporte_base'):
            conv.aporte_base = str(rd['aporte_base']).strip().lower()
        if rd.get('aporte_descripcion'):
            conv.aporte_descripcion = str(rd['aporte_descripcion']).strip()

        # Fechas y calendario
        f_aper = rd.get('fecha_apertura')
        if f_aper is not None and f_aper != '':
            conv.fecha_apertura = parse_iso_date(f_aper)

        h_aper = rd.get('hora_apertura')
        if h_aper is not None and h_aper != '':
            conv.hora_apertura = parse_time(h_aper)

        f_cierre = rd.get('fecha_cierre')
        if f_cierre is not None and f_cierre != '':
            conv.fecha_cierre = parse_iso_date(f_cierre)

        h_cierre = rd.get('hora_cierre')
        if h_cierre is not None and h_cierre != '':
            conv.hora_cierre = parse_time(h_cierre)

        if rd.get('zona_horaria'):
            conv.zona_horaria = str(rd['zona_horaria']).strip()
        if rd.get('cierre_modalidad'):
            conv.cierre_modalidad = str(rd['cierre_modalidad']).strip().lower()
        if rd.get('estado_fuente'):
            conv.estado_fuente = str(rd['estado_fuente']).strip().lower()
        if rd.get('url_convocatoria'):
            conv.url_convocatoria = str(rd['url_convocatoria']).strip()

        # Fechas de verificación
        for fld in ['requisitos_verificado_en', 'montos_verificado_en', 'cobertura_verificado_en',
                    'fechas_verificado_en', 'estado_verificado_en']:
            val = rd.get(fld)
            if val is not None and val != '':
                parsed_dt = parse_iso_datetime(val)
                if parsed_dt:
                    setattr(conv, fld, parsed_dt)

        if rd.get('evidencia_verificacion'):
            conv.evidencia_verificacion = str(rd['evidencia_verificacion']).strip()

        conv.save()

    # Actualizar versión de catálogo
    config.version_catalogo = ver_nueva
    config.save()

    conteo = previa['conteo']
    resumen_txt = (
        f"Actualización a catálogo v{ver_nueva}. "
        f"Entidades: +{conteo['entidades']['nuevas']}, mod {conteo['entidades']['modificadas']}. "
        f"Instrumentos: +{conteo['instrumentos']['nuevos']}, mod {conteo['instrumentos']['modificados']}. "
        f"Convocatorias: +{conteo['convocatorias']['nuevas']}, mod {conteo['convocatorias']['modificadas']}."
    )

    lote = ImportacionLote.objects.create(
        archivo_nombre=filename,
        archivo_hash=previa['archivo_hash'],
        usuario_responsable=usuario,
        version_base_anterior=ver_anterior,
        version_base_nueva=ver_nueva,
        resumen=resumen_txt,
        diferencias_json=previa['diferencias'],
        estado=EstadoLote.APLICADO,
    )

    return lote


@transaction.atomic
def revertir_lote_importacion(lote_id: str, usuario: str) -> Dict[str, Any]:
    """
    Revierte los cambios de un lote de importación previo si no existen colisiones posteriores.
    Restaura los valores anteriores registrados en el JSON de diferencias.
    """
    lote = ImportacionLote.objects.get(lote_id=lote_id)
    if lote.estado == EstadoLote.REVERTIDO:
        raise ValueError("Este lote ya fue revertido previamente.")

    diffs = lote.diferencias_json

    # Revertir Entidades modificadas
    for ent_mod in diffs.get('entidades_modificadas', []):
        try:
            ent = Entidad.objects.get(entidad_id=ent_mod['id'])
            for campo, vals in ent_mod['cambios'].items():
                setattr(ent, campo, vals['anterior'])
            ent.save()
        except Entidad.DoesNotExist:
            pass

    # Revertir Instrumentos modificados
    for inst_mod in diffs.get('instrumentos_modificadas', []) or diffs.get('instrumentos_modificados', []):
        try:
            inst = Instrumento.objects.get(instrumento_id=inst_mod['id'])
            for campo, vals in inst_mod['cambios'].items():
                val_ant = vals['anterior']
                if campo in ['monto_min', 'monto_max', 'aporte_pct']:
                    val_ant = parse_decimal(val_ant)
                setattr(inst, campo, val_ant)
            inst.save()
        except Instrumento.DoesNotExist:
            pass

    # Revertir Convocatorias modificadas
    for conv_mod in diffs.get('convocatorias_modificadas', []):
        try:
            conv = Convocatoria.objects.get(convocatoria_id=conv_mod['id'])
            for campo, vals in conv_mod['cambios'].items():
                val_ant = vals['anterior']
                if campo in ['fecha_apertura', 'fecha_cierre']:
                    val_ant = parse_iso_date(val_ant)
                elif campo in ['monto_min', 'monto_max', 'aporte_pct']:
                    val_ant = parse_decimal(val_ant)
                setattr(conv, campo, val_ant)
            conv.save()
        except Convocatoria.DoesNotExist:
            pass

    # Eliminar registros nuevos introducidos por el lote
    for conv_new in diffs.get('convocatorias_nuevas', []):
        Convocatoria.objects.filter(convocatoria_id=conv_new['id']).delete()

    for inst_new in diffs.get('instrumentos_nuevos', []):
        Instrumento.objects.filter(instrumento_id=inst_new['id']).delete()

    for ent_new in diffs.get('entidades_nuevas', []):
        Entidad.objects.filter(entidad_id=ent_new['id']).delete()

    lote.estado = EstadoLote.REVERTIDO
    lote.revertido_por = usuario
    lote.revertido_en = timezone.now()
    lote.save()

    config = ConfiguracionGlobal.get_solo()
    config.version_catalogo += 1
    config.save()

    return {
        'exito': True,
        'mensaje': f"Lote {lote.lote_id[:8]} revertido exitosamente. Se restauraron los valores anteriores."
    }
