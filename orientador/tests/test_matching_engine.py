from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from orientador.models import (
    Entidad, Instrumento, Convocatoria, EstadoEditorial,
    NoReembolsableConfirmado, FormalizacionRequerida, Moneda,
    CoberturaTerritorial, AporteBase
)
from orientador.services.matching_engine import evaluar_perfil_financiamiento


class MatchingEngineTestCase(TestCase):
    def setUp(self):
        self.entidad = Entidad.objects.create(
            entidad_id='ENT-CORFO',
            nombre='Corfo',
            url_oficial='https://www.corfo.gob.cl',
            estado_editorial=EstadoEditorial.PUBLICADO
        )
        self.entidad_sercotec = Entidad.objects.create(
            entidad_id='ENT-SERCOTEC',
            nombre='Sercotec',
            url_oficial='https://www.sercotec.cl',
            estado_editorial=EstadoEditorial.PUBLICADO
        )

        # 1. Fondo para formalizados
        self.fondo_crece = Instrumento.objects.create(
            instrumento_id='INS-CRECE',
            entidad=self.entidad_sercotec,
            nombre='Crece Microempresas',
            estado_editorial=EstadoEditorial.PUBLICADO,
            no_reembolsable_confirmado=NoReembolsableConfirmado.SI,
            formalizacion_requerida=FormalizacionRequerida.CON_INICIO_PRIMERA,
            necesidades='equipamiento;capital_trabajo',
            situaciones='ventas_formales',
            rubros='todos',
            cobertura=CoberturaTerritorial.NACIONAL,
            regiones='todos',
            monto_max=Decimal('5000000'),
            moneda=Moneda.CLP
        )

        # 2. Fondo exclusivo para personas sin inicio de actividades
        self.fondo_semilla = Instrumento.objects.create(
            instrumento_id='INS-SEMILLA',
            entidad=self.entidad_sercotec,
            nombre='Capital Semilla Emprende',
            estado_editorial=EstadoEditorial.PUBLICADO,
            no_reembolsable_confirmado=NoReembolsableConfirmado.SI,
            formalizacion_requerida=FormalizacionRequerida.SIN_INICIO_PRIMERA,
            necesidades='equipamiento;ventas_digital',
            situaciones='idea;ventas_informales',
            rubros='todos',
            cobertura=CoberturaTerritorial.NACIONAL,
            regiones='todos',
            monto_max=Decimal('3500000'),
            moneda=Moneda.CLP,
            aporte_pct=Decimal('3.00'),
            aporte_base=AporteBase.SUBSIDIO
        )

        # 3. Fondo regional Los Ríos
        self.fondo_regional = Instrumento.objects.create(
            instrumento_id='INS-REGIONAL',
            entidad=self.entidad,
            nombre='Fondo Innovación Los Ríos',
            estado_editorial=EstadoEditorial.PUBLICADO,
            no_reembolsable_confirmado=NoReembolsableConfirmado.SI,
            formalizacion_requerida=FormalizacionRequerida.CUALQUIERA,
            necesidades='prototipo',
            situaciones='todos',
            rubros='turismo;alimentos',
            cobertura=CoberturaTerritorial.REGIONAL,
            regiones='CL-LR',
            monto_max=Decimal('15000000'),
            moneda=Moneda.CLP
        )

    def test_negocio_informal_vs_fondo_formalizado_clasifica_proxima_etapa(self):
        """Negocio no formalizado y fondo para empresa formalizada -> va a 'Para una próxima etapa'."""
        respuestas = {
            'necesidades': ['equipamiento'],
            'situacion': 'ventas_informales',
            'region': 'CL-RM',
            'monto_buscado': 'de_1m_a_3_5m',
            'rubro': 'comercio'
        }
        res = evaluar_perfil_financiamiento(respuestas)

        ids_pertinentes = [p['instrumento'].instrumento_id for p in res['pertinentes']]
        ids_proxima = [p['instrumento'].instrumento_id for p in res['proxima_etapa']]

        self.assertNotIn('INS-CRECE', ids_pertinentes)
        self.assertIn('INS-CRECE', ids_proxima)
        self.assertIn('INS-SEMILLA', ids_pertinentes)

    def test_exclusion_territorial_regional(self):
        """Un fondo exclusivo de Los Ríos no debe aparecer en los resultados principales de Magallanes."""
        respuestas = {
            'necesidades': ['prototipo'],
            'situacion': 'idea',
            'region': 'CL-MA',  # Magallanes
            'monto_buscado': 'mas_10m_a_20m',
            'rubro': 'turismo'
        }
        res = evaluar_perfil_financiamiento(respuestas)
        ids_pertinentes = [p['instrumento'].instrumento_id for p in res['pertinentes']]
        self.assertNotIn('INS-REGIONAL', ids_pertinentes)

    def test_coincidencia_territorial_en_su_region(self):
        """El fondo de Los Ríos sí aparece cuando el usuario es de Los Ríos."""
        respuestas = {
            'necesidades': ['prototipo'],
            'situacion': 'idea',
            'region': 'CL-LR',  # Los Ríos
            'monto_buscado': 'mas_10m_a_20m',
            'rubro': 'turismo'
        }
        res = evaluar_perfil_financiamiento(respuestas)
        ids_pertinentes = [p['instrumento'].instrumento_id for p in res['pertinentes']]
        self.assertIn('INS-REGIONAL', ids_pertinentes)

    def test_conservacion_aporte_porcentaje_sobre_subsidio(self):
        """Aporte del 3% del subsidio se conserva con su base de cálculo."""
        respuestas = {
            'necesidades': ['equipamiento'],
            'situacion': 'idea',
            'region': 'CL-RM',
            'monto_buscado': 'de_1m_a_3_5m',
            'rubro': 'comercio'
        }
        res = evaluar_perfil_financiamiento(respuestas)
        item_semilla = next(p for p in res['pertinentes'] if p['instrumento'].instrumento_id == 'INS-SEMILLA')
        self.assertEqual(item_semilla['instrumento'].aporte_pct, Decimal('3.00'))
        self.assertEqual(item_semilla['instrumento'].aporte_base, AporteBase.SUBSIDIO)

    def test_monto_desconocido_no_rompe_ni_excluye(self):
        """Monto 'no_se' funciona normalmente y no bloquea resultados."""
        respuestas = {
            'necesidades': ['equipamiento'],
            'situacion': 'idea',
            'region': 'CL-RM',
            'monto_buscado': 'no_se',
            'rubro': 'otro'
        }
        res = evaluar_perfil_financiamiento(respuestas)
        self.assertFalse(res['estado_vacio'])
        self.assertGreater(len(res['pertinentes']), 0)
