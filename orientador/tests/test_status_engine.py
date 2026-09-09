from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.utils import timezone

from orientador.models import (
    Entidad, Instrumento, Convocatoria, EstadoEditorial,
    EstadoFuente, CierreModalidad, Moneda, ConfiguracionGlobal
)
from orientador.services.status_engine import (
    calcular_estado_convocatoria, evaluar_vigencia_instrumento, CodigoEstadoCalculado
)


class StatusEngineTestCase(TestCase):
    def setUp(self):
        self.config = ConfiguracionGlobal.get_solo()
        self.config.dias_revision_abierta = 7
        self.config.dias_revision_instrumento = 90
        self.config.save()

        self.entidad = Entidad.objects.create(
            entidad_id='ENT-TEST',
            nombre='Entidad de Prueba',
            url_oficial='https://example.com',
            estado_editorial=EstadoEditorial.PUBLICADO
        )
        self.instrumento = Instrumento.objects.create(
            instrumento_id='INS-TEST',
            entidad=self.entidad,
            nombre='Instrumento Test',
            estado_editorial=EstadoEditorial.PUBLICADO,
            requisitos_verificado_en=timezone.now() - timedelta(days=10)
        )

    def test_cierre_vencido_deja_de_mostrarse_abierto(self):
        """Regla 2: Un cierre informado ya vencido deja de mostrarse como abierto."""
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-VENCIDA',
            instrumento=self.instrumento,
            nombre='Convocatoria Vencida',
            estado_editorial=EstadoEditorial.PUBLICADO,
            estado_fuente=EstadoFuente.ABIERTA,
            fecha_cierre=date(2026, 8, 1),
            estado_verificado_en=timezone.make_aware(datetime(2026, 7, 25, 10, 0), ZoneInfo('America/Santiago'))
        )
        ref_time = timezone.make_aware(datetime(2026, 8, 15, 12, 0), ZoneInfo('America/Santiago'))
        res = calcular_estado_convocatoria(conv, reference_time=ref_time)
        self.assertEqual(res['codigo'], CodigoEstadoCalculado.PLAZO_FINALIZADO)
        self.assertEqual(res['etiqueta'], 'Plazo informado finalizado')

    def test_cierra_hoy_sin_hora_muestra_confirmar_hora(self):
        """Regla 7: Si solo se conoce el día de cierre, al llegar ese día mostrar 'Cierra hoy: confirmar hora'."""
        hoy = date(2026, 9, 8)
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-HOY',
            instrumento=self.instrumento,
            nombre='Convocatoria Cierra Hoy',
            estado_editorial=EstadoEditorial.PUBLICADO,
            estado_fuente=EstadoFuente.ABIERTA,
            fecha_cierre=hoy,
            hora_cierre=None,  # No se sabe la hora
            estado_verificado_en=timezone.make_aware(datetime(2026, 9, 5, 10, 0), ZoneInfo('America/Santiago'))
        )
        ref_time = timezone.make_aware(datetime(2026, 9, 8, 14, 0), ZoneInfo('America/Santiago'))
        res = calcular_estado_convocatoria(conv, reference_time=ref_time)
        self.assertEqual(res['codigo'], CodigoEstadoCalculado.CIERRA_HOY_CONFIRMAR_HORA)
        self.assertIn('confirmar hora', res['etiqueta'].lower())

    def test_apertura_prevista_alcanzada_requiere_verificacion(self):
        """Regla 3: Llegar a la fecha de apertura no basta para afirmar apertura sin comprobación oficial."""
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-APERTURA-FUTURA',
            instrumento=self.instrumento,
            nombre='Convocatoria Apertura Test',
            estado_editorial=EstadoEditorial.PUBLICADO,
            estado_fuente=EstadoFuente.ANUNCIADA,
            fecha_apertura=date(2026, 9, 1),
            fecha_cierre=date(2026, 9, 30),
            estado_verificado_en=timezone.make_aware(datetime(2026, 8, 10, 10, 0), ZoneInfo('America/Santiago'))  # Verificado antes de abrir
        )
        ref_time = timezone.make_aware(datetime(2026, 9, 5, 12, 0), ZoneInfo('America/Santiago'))
        res = calcular_estado_convocatoria(conv, reference_time=ref_time)
        self.assertEqual(res['codigo'], CodigoEstadoCalculado.APERTURA_PREVISTA)
        self.assertIn('Apertura prevista', res['etiqueta'])

    def test_suspension_prevalece_sobre_fechas(self):
        """Regla 1: Una suspensión o cancelación verificada prevalece sobre un calendario anterior."""
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-SUSPENDIDA',
            instrumento=self.instrumento,
            nombre='Convocatoria Suspendida Test',
            estado_editorial=EstadoEditorial.PUBLICADO,
            estado_fuente=EstadoFuente.SUSPENDIDA,
            fecha_cierre=date(2026, 9, 30),
            estado_verificado_en=timezone.make_aware(datetime(2026, 9, 7, 10, 0), ZoneInfo('America/Santiago'))
        )
        ref_time = timezone.make_aware(datetime(2026, 9, 8, 10, 0), ZoneInfo('America/Santiago'))
        res = calcular_estado_convocatoria(conv, reference_time=ref_time)
        self.assertEqual(res['codigo'], CodigoEstadoCalculado.SUSPENDIDA)
        self.assertTrue(res['requiere_atencion'])

    def test_vigencia_envejecida_muestra_por_confirmar(self):
        """Regla 5: Si la revisión de apertura supera los 7 días, mostrar 'Vigencia por confirmar'."""
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-VIEJA',
            instrumento=self.instrumento,
            nombre='Convocatoria Vieja Test',
            estado_editorial=EstadoEditorial.PUBLICADO,
            estado_fuente=EstadoFuente.ABIERTA,
            fecha_cierre=date(2026, 9, 30),
            estado_verificado_en=timezone.make_aware(datetime(2026, 8, 20, 10, 0), ZoneInfo('America/Santiago'))  # Hace 19 días
        )
        ref_time = timezone.make_aware(datetime(2026, 9, 8, 10, 0), ZoneInfo('America/Santiago'))
        res = calcular_estado_convocatoria(conv, reference_time=ref_time, max_dias_abierta=7)
        self.assertEqual(res['codigo'], CodigoEstadoCalculado.VIGENCIA_POR_CONFIRMAR)
        self.assertIn('Vigencia por confirmar', res['etiqueta'])

    def test_instrumento_desactualizado_mayor_90_dias(self):
        """Regla 9: Si los datos generales del instrumento superan 90 días, mostrar requiere actualización."""
        self.instrumento.requisitos_verificado_en = timezone.now() - timedelta(days=120)
        self.instrumento.montos_verificado_en = timezone.now() - timedelta(days=120)
        self.instrumento.cobertura_verificado_en = timezone.now() - timedelta(days=120)
        self.instrumento.save()

        res = evaluar_vigencia_instrumento(self.instrumento, reference_time=timezone.now(), max_dias_instrumento=90)
        self.assertTrue(res['desactualizado'])
        self.assertFalse(res['monto_confiable'])
        self.assertIn('requiere actualización', res['mensaje'])
