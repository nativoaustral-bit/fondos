from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from orientador.models import (
    Entidad, Instrumento, Convocatoria, EstadoEditorial, EstadoFuente, NoReembolsableConfirmado,
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
        """El formulario inicial v2 carga con código 200 y contiene las 5 preguntas oficiales en una página."""
        resp = self.client.get(reverse('orientador:formulario'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '¿Qué quieres lograr con este financiamiento?')
        self.assertContains(resp, '¿Qué necesitas financiar para lograrlo?')
        self.assertContains(resp, '¿Cuál es la situación actual de tu negocio?')
        self.assertContains(resp, '¿En qué región desarrollarás el proyecto?')
        self.assertContains(resp, '¿Cuál es la actividad principal de tu emprendimiento?')

    def test_procesar_consulta_exito(self):
        """Enviar respuestas de Formulario v2 renderiza resultados con Directriz Inicial."""
        data = {
            'objetivo_financiamiento': 'iniciar_negocio',
            'necesidades': ['equipamiento', 'capital_trabajo'],
            'estado_actividad': 'sin_primera_sin_ventas',
            'region': 'CL-LR',
            'rubro': 'turismo'
        }
        resp = self.client.post(reverse('orientador:procesar_consulta'), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Directriz inicial')
        self.assertContains(resp, 'Tu búsqueda se orienta a la puesta en marcha del negocio')
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
        self.assertIn('/gestion/login/', resp.url)

    def test_catalogo_mantiene_conteos_entre_pestanas(self):
        """Los botones de selección de catálogo muestran los totales y no desaparecen."""
        user = User.objects.create_superuser('admin_catalog', 'admin@humm.cl', 'pass')
        self.client.force_login(user)

        for sec in ['instrumentos', 'convocatorias', 'entidades']:
            resp = self.client.get(reverse('orientador:admin_catalogo'), {'seccion': sec})
            self.assertEqual(resp.status_code, 200)
            self.assertIn('total_instrumentos', resp.context)
            self.assertIn('total_convocatorias', resp.context)
            self.assertIn('total_entidades', resp.context)
            content = resp.content.decode()
            self.assertIn(f"Instrumentos ({resp.context['total_instrumentos']})", content)
            self.assertIn(f"Convocatorias ({resp.context['total_convocatorias']})", content)
            self.assertIn(f"Entidades ({resp.context['total_entidades']})", content)

    def test_agregar_y_editar_entidad_manual(self):
        """Permite agregar una nueva entidad y editarla reemplazando datos sin duplicar."""
        user = User.objects.create_superuser('admin_entidades', 'admin2@humm.cl', 'pass')
        self.client.force_login(user)

        # 1. Crear entidad nueva
        url_guardar = reverse('orientador:admin_entidad_guardar')
        resp = self.client.post(url_guardar, {
            'modo': 'crear',
            'entidad_id': 'ENT-099',
            'nombre': 'Fundación de Prueba',
            'tipo': 'sociedad_civil',
            'url_oficial': 'https://www.fundacionprueba.cl',
            'estado_editorial': 'publicado'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        ent = Entidad.objects.get(entidad_id='ENT-099')
        self.assertEqual(ent.nombre, 'Fundación de Prueba')
        self.assertEqual(ent.tipo, 'sociedad_civil')
        self.assertEqual(ent.url_oficial, 'https://www.fundacionprueba.cl')

        # 2. Intentar duplicar mismo ID en modo crear debe ser rechazado
        resp_dup = self.client.post(url_guardar, {
            'modo': 'crear',
            'entidad_id': 'ENT-099',
            'nombre': 'Fundación Duplicada',
            'tipo': 'privada',
            'url_oficial': 'https://www.otrafundacion.cl',
        }, follow=True)
        self.assertEqual(resp_dup.status_code, 200)
        self.assertEqual(Entidad.objects.filter(entidad_id='ENT-099').count(), 1)

        # 3. Editar entidad existente reemplazando datos in-place
        resp_edit = self.client.post(url_guardar, {
            'modo': 'editar',
            'entidad_id': 'ENT-099',
            'nombre': 'Fundación de Prueba Editada',
            'tipo': 'privada',
            'url_oficial': 'https://www.fundacionactualizada.cl',
            'estado_editorial': 'borrador'
        }, follow=True)
        self.assertEqual(resp_edit.status_code, 200)

        # Verificar que NO se duplicó y los datos fueron reemplazados
        self.assertEqual(Entidad.objects.filter(entidad_id='ENT-099').count(), 1)
        ent.refresh_from_db()
        self.assertEqual(ent.nombre, 'Fundación de Prueba Editada')
        self.assertEqual(ent.tipo, 'privada')
        self.assertEqual(ent.url_oficial, 'https://www.fundacionactualizada.cl')
        self.assertEqual(ent.estado_editorial, 'borrador')

    def test_editar_estado_y_fechas_instrumento_con_convocatoria(self):
        """Permite editar estado y fechas de un instrumento con convocatoria existente in-place."""
        user = User.objects.create_superuser('admin_inst', 'admin_inst@humm.cl', 'pass')
        self.client.force_login(user)

        # Crear convocatoria previa para el instrumento
        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-001',
            instrumento=self.instrumento,
            nombre='Convocatoria 2026',
            estado_fuente=EstadoFuente.ABIERTA,
            estado_editorial=EstadoEditorial.PUBLICADO
        )

        url = reverse('orientador:admin_instrumento_guardar_estado')
        resp = self.client.post(url, {
            'instrumento_id': self.instrumento.instrumento_id,
            'estado_llamado': 'cerrada',
            'fecha_apertura': '2026-03-01',
            'fecha_cierre': '2026-04-15',
            'cierre_modalidad': 'fecha_definida',
            'estado_editorial': 'publicado'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Verificar que se actualizó in-place sin duplicar convocatoria
        self.assertEqual(Convocatoria.objects.filter(instrumento=self.instrumento).count(), 1)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_fuente, 'cerrada')
        self.assertEqual(str(conv.fecha_apertura), '2026-03-01')
        self.assertEqual(str(conv.fecha_cierre), '2026-04-15')

    def test_editar_estado_y_fechas_instrumento_sin_convocatoria_crea_llamado(self):
        """Si un instrumento no tiene convocatoria previa, editar estado crea la convocatoria automáticamente."""
        user = User.objects.create_superuser('admin_inst2', 'admin_inst2@humm.cl', 'pass')
        self.client.force_login(user)

        self.assertEqual(Convocatoria.objects.filter(instrumento=self.instrumento).count(), 0)

        url = reverse('orientador:admin_instrumento_guardar_estado')
        resp = self.client.post(url, {
            'instrumento_id': self.instrumento.instrumento_id,
            'estado_llamado': 'abierta',
            'fecha_apertura': '2026-05-10',
            'fecha_cierre': '2026-06-20',
            'cierre_modalidad': 'fecha_definida',
            'estado_editorial': 'publicado'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        conv = Convocatoria.objects.filter(instrumento=self.instrumento).first()
        self.assertIsNotNone(conv)
        self.assertEqual(conv.estado_fuente, 'abierta')
        self.assertEqual(str(conv.fecha_apertura), '2026-05-10')
        self.assertEqual(str(conv.fecha_cierre), '2026-06-20')

    def test_editar_convocatoria_directa(self):
        """Permite editar estado, fechas y nombre de una convocatoria directamente."""
        user = User.objects.create_superuser('admin_conv', 'admin_conv@humm.cl', 'pass')
        self.client.force_login(user)

        conv = Convocatoria.objects.create(
            convocatoria_id='CONV-002',
            instrumento=self.instrumento,
            nombre='Convocatoria Original',
            estado_fuente=EstadoFuente.ABIERTA,
            estado_editorial=EstadoEditorial.PUBLICADO
        )

        url = reverse('orientador:admin_convocatoria_guardar')
        resp = self.client.post(url, {
            'convocatoria_id': 'CONV-002',
            'nombre': 'Convocatoria Actualizada 2026',
            'estado_fuente': 'cerrada',
            'fecha_apertura': '2026-01-15',
            'fecha_cierre': '2026-02-28',
            'cierre_modalidad': 'fecha_definida',
            'estado_editorial': 'publicado'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # No se duplicó
        self.assertEqual(Convocatoria.objects.filter(convocatoria_id='CONV-002').count(), 1)
        conv.refresh_from_db()
        self.assertEqual(conv.nombre, 'Convocatoria Actualizada 2026')
        self.assertEqual(conv.estado_fuente, 'cerrada')
        self.assertEqual(str(conv.fecha_apertura), '2026-01-15')
        self.assertEqual(str(conv.fecha_cierre), '2026-02-28')

    def test_rutas_guardar_estado_protegidas_sin_auth(self):
        """Las rutas para guardar estado de instrumento y convocatoria exigen usuario staff."""
        resp1 = self.client.post(reverse('orientador:admin_instrumento_guardar_estado'), {})
        self.assertEqual(resp1.status_code, 302)
        self.assertIn('/gestion/login/', resp1.url)

        resp2 = self.client.post(reverse('orientador:admin_convocatoria_guardar'), {})
        self.assertEqual(resp2.status_code, 302)
        self.assertIn('/gestion/login/', resp2.url)

    def test_catalogo_renderiza_botones_y_modales_de_edicion(self):
        """Verifica que las tablas de instrumentos y convocatorias renderizan botones y diálogos de edición."""
        user = User.objects.create_superuser('admin_modals', 'admin_modals@humm.cl', 'pass')
        self.client.force_login(user)

        # 1. Pestaña Instrumentos
        resp_inst = self.client.get(reverse('orientador:admin_catalogo'), {'seccion': 'instrumentos'})
        self.assertEqual(resp_inst.status_code, 200)
        self.assertContains(resp_inst, 'id="modal-instrumento"')
        self.assertContains(resp_inst, 'abrirModalEditarInstrumento')
        self.assertContains(resp_inst, 'Estado Llamado')
        self.assertContains(resp_inst, 'Fechas (Apertura / Cierre)')

        # 2. Pestaña Convocatorias
        resp_conv = self.client.get(reverse('orientador:admin_catalogo'), {'seccion': 'convocatorias'})
        self.assertEqual(resp_conv.status_code, 200)
        self.assertContains(resp_conv, 'id="modal-convocatoria"')
        self.assertContains(resp_conv, 'abrirModalEditarConvocatoria')
        self.assertContains(resp_conv, 'Acciones')




