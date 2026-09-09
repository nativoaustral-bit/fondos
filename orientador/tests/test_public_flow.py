from django.test import TestCase, Client
from django.urls import reverse
from orientador.models import (
    Entidad, Instrumento, EstadoEditorial, NoReembolsableConfirmado,
    FormalizacionRequerida, CoberturaTerritorial, Moneda,
    FormularioConfig, PreguntaConfig, OpcionConfig, TipoPregunta,
    SolicitudApoyo, EstadoSolicitud
)
from orientador.management.commands.setup_initial_data import Command as SetupCommand


class PublicFlowTestCase(TestCase):
    def setUp(self):
        # Inicializar cuestionario
        cmd = SetupCommand()
        cmd.handle()
        self.client = Client()

        self.entidad = Entidad.objects.create(
            entidad_id='ENT-SERCOTEC',
            nombre='Sercotec',
            url_oficial='https://www.sercotec.cl',
            estado_editorial=EstadoEditorial.PUBLICADO
        )
        self.instrumento = Instrumento.objects.create(
            instrumento_id='INS-SEMILLA',
            entidad=self.entidad,
            nombre='Capital Semilla Emprende',
            estado_editorial=EstadoEditorial.PUBLICADO,
            no_reembolsable_confirmado=NoReembolsableConfirmado.SI,
            formalizacion_requerida=FormalizacionRequerida.SIN_INICIO_PRIMERA,
            necesidades='equipamiento;capital_trabajo',
            situaciones='idea;ventas_informales',
            rubros='todos',
            cobertura=CoberturaTerritorial.NACIONAL,
            regiones='todos',
            moneda=Moneda.CLP
        )

    def test_formulario_muestra_cinco_preguntas(self):
        """El formulario inicial carga con código 200 y contiene las 5 preguntas."""
        resp = self.client.get(reverse('orientador:formulario'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '¿Qué necesitas financiar?')
        self.assertContains(resp, '¿En qué situación está tu emprendimiento?')
        self.assertContains(resp, '¿En qué región desarrollarás el proyecto?')
        self.assertContains(resp, '¿Cuánto financiamiento buscas aproximadamente?')
        self.assertContains(resp, '¿Cuál es el rubro principal de tu emprendimiento?')

    def test_procesar_consulta_exito(self):
        """Enviar respuestas válidas redirige o renderiza resultados."""
        data = {
            'necesidades': ['equipamiento', 'capital_trabajo'],
            'situacion': 'idea',
            'region': 'CL-LR',
            'monto_buscado': 'de_1m_a_3_5m',
            'rubro': 'turismo'
        }
        resp = self.client.post(reverse('orientador:procesar_consulta'), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Opciones para lo que necesitas financiar')
        self.assertContains(resp, 'Tu siguiente paso')

    def test_solicitud_apoyo_deduplicacion_doble_click(self):
        """Solicitud de apoyo con doble pulsación guarda un único registro."""
        data = {
            'nombre': 'Valeria Soto',
            'canal_contacto': 'whatsapp',
            'contacto_valor': '+56998765432',
            'mensaje': 'Quiero postular a Capital Abeja',
            'autorizacion_contacto': 'si',
            'adjuntar_perfil': 'si',
        }
        # Primer clic
        resp1 = self.client.post(reverse('orientador:solicitar_apoyo'), data)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertTrue(data1['ok'])

        # Segundo clic rápido (idéntico)
        resp2 = self.client.post(reverse('orientador:solicitar_apoyo'), data)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2['ok'])
        self.assertEqual(data1['id'], data2['id'])

        # Verificar en base de datos que existe exactamente 1
        self.assertEqual(SolicitudApoyo.objects.filter(nombre='Valeria Soto').count(), 1)

    def test_rutas_administrativas_protegidas_sin_login(self):
        """Acceso anónimo a rutas de gestión es rechazado con redirección."""
        resp = self.client.get(reverse('orientador:admin_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/login/', resp.url)
