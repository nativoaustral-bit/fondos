import io
import openpyxl
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from orientador.models import (
    Entidad, Instrumento, Convocatoria, ConfiguracionGlobal,
    EstadoEditorial, TipoEntidad, CoberturaTerritorial,
    FormalizacionRequerida, NoReembolsableConfirmado, Moneda
)
from orientador.services.excel_contract import (
    generar_excel_catalogo, validar_y_previsualizar_excel,
    aplicar_actualizacion_excel, revertir_lote_importacion
)


class ExcelContractTestCase(TestCase):
    def setUp(self):
        self.config = ConfiguracionGlobal.get_solo()
        self.config.version_catalogo = 1
        self.config.save()

        self.entidad = Entidad.objects.create(
            entidad_id='ENT-CORFO-TEST',
            nombre='Corfo Test',
            tipo=TipoEntidad.PUBLICA,
            url_oficial='https://www.corfo.gob.cl',
            estado_editorial=EstadoEditorial.PUBLICADO
        )
        self.instrumento = Instrumento.objects.create(
            instrumento_id='INS-TEST-001',
            entidad=self.entidad,
            nombre='Semilla Inicia Test',
            estado_editorial=EstadoEditorial.PUBLICADO,
            no_reembolsable_confirmado=NoReembolsableConfirmado.SI,
            monto_max=Decimal('15000000'),
            moneda=Moneda.CLP,
            que_financia='Validación técnica y comercial'
        )

    def test_exportar_y_reimportar_sin_cambios(self):
        """Exportar y reimportar sin cambios no modifica datos ni genera errores."""
        buf = generar_excel_catalogo(incluir_datos=True)
        content = buf.getvalue()

        previa = validar_y_previsualizar_excel(content, 'test_export.xlsx')
        self.assertTrue(previa['valido'])
        self.assertEqual(len(previa['errores']), 0)
        self.assertEqual(previa['conteo']['instrumentos']['nuevos'], 0)
        self.assertEqual(previa['conteo']['instrumentos']['modificados'], 0)
        self.assertEqual(previa['conteo']['instrumentos']['sin_cambio'], 1)

    def test_actualizacion_modifica_campo_y_preserva_vacio(self):
        """Una celda vacía conserva el valor anterior; una modificación se detecta y aplica."""
        buf = generar_excel_catalogo(incluir_datos=True)
        wb = openpyxl.load_workbook(buf)
        ws_inst = wb['Instrumentos']

        # Modificar el nombre en la fila 2
        ws_inst.cell(row=2, column=3, value='Semilla Inicia Nombre Modificado')

        out_buf = io.BytesIO()
        wb.save(out_buf)
        content = out_buf.getvalue()

        previa = validar_y_previsualizar_excel(content, 'test_mod.xlsx')
        self.assertTrue(previa['valido'])
        self.assertEqual(len(previa['diferencias']['instrumentos_modificados']), 1)
        mod = previa['diferencias']['instrumentos_modificados'][0]
        self.assertIn('nombre', mod['cambios'])
        self.assertEqual(mod['cambios']['nombre']['propuesto'], 'Semilla Inicia Nombre Modificado')

        # Aplicar atómicamente
        lote = aplicar_actualizacion_excel(content, 'test_mod.xlsx', 'test_user')
        self.assertEqual(lote.version_base_nueva, 2)

        inst_actualizado = Instrumento.objects.get(instrumento_id='INS-TEST-001')
        self.assertEqual(inst_actualizado.nombre, 'Semilla Inicia Nombre Modificado')
        # El campo que_financia estaba vacío en la fila modificada o no tocado -> se preservó
        self.assertEqual(inst_actualizado.que_financia, 'Validación técnica y comercial')

    def test_borrar_expreso_elimina_campo_opcional(self):
        """El valor __BORRAR__ elimina expresamente el contenido de un campo opcional."""
        buf = generar_excel_catalogo(incluir_datos=True)
        wb = openpyxl.load_workbook(buf)
        ws_inst = wb['Instrumentos']

        # Encontrar columna 'que_financia' (columna 7)
        ws_inst.cell(row=2, column=7, value='__BORRAR__')

        out_buf = io.BytesIO()
        wb.save(out_buf)
        content = out_buf.getvalue()

        aplicar_actualizacion_excel(content, 'test_borrar.xlsx', 'test_user')
        inst = Instrumento.objects.get(instrumento_id='INS-TEST-001')
        self.assertEqual(inst.que_financia, '')

    def test_error_bloqueante_impide_escritura_parcial(self):
        """Un error como ID duplicado o entidad inexistente rechaza todo el lote."""
        buf = generar_excel_catalogo(incluir_datos=True)
        wb = openpyxl.load_workbook(buf)
        ws_inst = wb['Instrumentos']

        # Agregar instrumento con entidad inexistente
        nueva_fila = ['INS-CORRUPTO', 'ENT-FANTASMA', 'Invalido', 'borrador']
        ws_inst.append(nueva_fila)

        out_buf = io.BytesIO()
        wb.save(out_buf)
        content = out_buf.getvalue()

        previa = validar_y_previsualizar_excel(content, 'test_error.xlsx')
        self.assertFalse(previa['valido'])
        self.assertGreater(len(previa['errores']), 0)

        with self.assertRaises(ValueError):
            aplicar_actualizacion_excel(content, 'test_error.xlsx', 'test_user')

        self.assertFalse(Instrumento.objects.filter(instrumento_id='INS-CORRUPTO').exists())

    def test_revertir_lote_restaura_datos(self):
        """Revertir un lote restaura valores anteriores."""
        buf = generar_excel_catalogo(incluir_datos=True)
        wb = openpyxl.load_workbook(buf)
        ws_inst = wb['Instrumentos']
        ws_inst.cell(row=2, column=3, value='Nombre Temporal')

        out_buf = io.BytesIO()
        wb.save(out_buf)
        lote = aplicar_actualizacion_excel(out_buf.getvalue(), 'test_temp.xlsx', 'test_user')

        inst_mod = Instrumento.objects.get(instrumento_id='INS-TEST-001')
        self.assertEqual(inst_mod.nombre, 'Nombre Temporal')

        # Revertir
        revertir_lote_importacion(lote.lote_id, 'test_user')
        inst_restaurado = Instrumento.objects.get(instrumento_id='INS-TEST-001')
        self.assertEqual(inst_restaurado.nombre, 'Semilla Inicia Test')
