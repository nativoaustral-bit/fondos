"""
Comando para crear y activar la Versión 2 del Formulario Oficial Humm Financiamiento.
Implementa el cuestionario oficial de 5 preguntas de la Sección 4 del documento de revisión.
"""

from django.core.management.base import BaseCommand
from orientador.models import FormularioConfig, PreguntaConfig, OpcionConfig, TipoPregunta


class Command(BaseCommand):
    help = 'Crea y activa la versión 2 del formulario oficial Humm'

    def handle(self, *args, **options):
        self.stdout.write("Creando Versión 2 del Formulario Humm...")

        form_v2, created = FormularioConfig.objects.get_or_create(
            version=2,
            defaults={
                'nombre': 'Formulario Oficial Humm v2 (Objetivo, Necesidades, Situación SII, Región, Rubro)',
                'descripcion': 'Formulario de 5 preguntas optimizado con orientación por objetivo y precisión ante el SII.',
                'es_activa': True,
            }
        )
        if not created:
            form_v2.nombre = 'Formulario Oficial Humm v2 (Objetivo, Necesidades, Situación SII, Región, Rubro)'
            form_v2.descripcion = 'Formulario de 5 preguntas optimizado con orientación por objetivo y precisión ante el SII.'
            form_v2.es_activa = True
            form_v2.save()

        # Limpiar preguntas previas de la versión 2 si existían
        form_v2.preguntas.all().delete()

        # ----------------------------------------------------
        # Pregunta 1: Objetivo del financiamiento
        # ----------------------------------------------------
        p1 = PreguntaConfig.objects.create(
            formulario=form_v2,
            clave='objetivo_financiamiento',
            titulo='¿Qué quieres lograr con este financiamiento?',
            ayuda='Elige tu objetivo principal.',
            tipo=TipoPregunta.RADIO,
            limite_seleccion=1,
            orden=1,
            activa=True
        )
        opciones_p1 = [
            ('iniciar_negocio', 'Iniciar y poner en marcha un negocio', 'Dar los primeros pasos para comenzar a operar.'),
            ('fortalecer_negocio', 'Fortalecer o aumentar la capacidad de mi negocio', 'Producir más, mejorar calidad o hacer más eficiente el trabajo.'),
            ('vender_digitalizar', 'Vender más, digitalizar o llegar a nuevos mercados', 'Mejorar ventas, canales comerciales o gestión digital.'),
            ('desarrollar_innovacion', 'Desarrollar y probar una solución nueva o mejorada', 'Crear un producto, servicio o proceso con una diferencia relevante frente a las alternativas existentes.'),
            ('sostenibilidad', 'Reducir el impacto ambiental de mi negocio', 'Ahorrar energía o agua, reducir residuos o reutilizar materiales.'),
            ('proyecto_cultural', 'Crear o desarrollar un proyecto artístico o cultural', 'Producir obras, contenidos o actividades culturales.'),
            ('por_definir', 'Aún no lo tengo claro', 'Recibir orientación a partir de mi situación y necesidades.'),
        ]
        for idx, (cod, etq, desc) in enumerate(opciones_p1, start=1):
            OpcionConfig.objects.create(
                pregunta=p1,
                codigo=cod,
                etiqueta=etq,
                descripcion_auxiliar=desc,
                orden=idx,
                activa=True
            )

        # ----------------------------------------------------
        # Pregunta 2: Necesidad que se financiará
        # ----------------------------------------------------
        p2 = PreguntaConfig.objects.create(
            formulario=form_v2,
            clave='necesidades',
            titulo='¿Qué necesitas financiar para lograrlo?',
            ayuda='Elige hasta dos necesidades principales.',
            tipo=TipoPregunta.CHECKBOX_LIMIT,
            limite_seleccion=2,
            orden=2,
            activa=True
        )
        opciones_p2 = [
            ('equipamiento', 'Equipos y herramientas', 'Maquinaria, herramientas, equipos tecnológicos o mobiliario.'),
            ('capital_trabajo', 'Insumos y capital de trabajo', 'Materias primas, mercadería y gastos operativos que permitan las bases.'),
            ('ventas_digital', 'Ventas, difusión y herramientas digitales', 'Marketing, sitio web, comercio electrónico o software para el negocio.'),
            ('prototipo', 'Desarrollo, prototipo y validación', 'Diseño, pruebas técnicas, pilotaje o validación comercial.'),
            ('infraestructura', 'Habilitación e infraestructura', 'Adecuación de local, taller, instalaciones o espacio productivo.'),
            ('asistencia_tecnica', 'Asesorías, capacitación o certificaciones', 'Servicios especializados, formación o certificaciones.'),
            ('produccion_cultural', 'Creación y producción de obras o contenidos', 'Producción artística, audiovisual, musical, editorial u otra actividad creativa.'),
            ('por_definir', 'Aún no tengo definida la inversión', 'Orientación general sin descartar por tipo de gasto.'),
        ]
        for idx, (cod, etq, desc) in enumerate(opciones_p2, start=1):
            OpcionConfig.objects.create(
                pregunta=p2,
                codigo=cod,
                etiqueta=etq,
                descripcion_auxiliar=desc,
                orden=idx,
                activa=True
            )

        # ----------------------------------------------------
        # Pregunta 3: Situación ante el SII y ventas
        # ----------------------------------------------------
        p3 = PreguntaConfig.objects.create(
            formulario=form_v2,
            clave='estado_actividad',
            titulo='¿Cuál es la situación actual de tu negocio?',
            ayuda='Nos referimos al inicio de actividades en primera categoría ante el SII. Si no estás seguro, puedes indicarlo.',
            tipo=TipoPregunta.RADIO,
            limite_seleccion=1,
            orden=3,
            activa=True
        )
        opciones_p3 = [
            ('sin_primera_sin_ventas', 'Aún no vendo y no tengo inicio de actividades en primera categoría', 'Primera categoría: no. Ventas declaradas: no.'),
            ('sin_primera_con_ventas', 'Ya vendo, pero no tengo inicio de actividades en primera categoría', 'Primera categoría: no. Ventas declaradas: sí.'),
            ('con_primera_sin_ventas', 'Tengo inicio de actividades en primera categoría, pero todavía no vendo', 'Primera categoría: sí. Ventas declaradas: no.'),
            ('con_primera_con_ventas', 'Tengo inicio de actividades en primera categoría y ya vendo', 'Primera categoría: sí. Ventas declaradas: sí.'),
            ('por_confirmar', 'No estoy seguro de mi situación ante el SII', 'Condición tributaria pendiente de verificar.'),
        ]
        for idx, (cod, etq, desc) in enumerate(opciones_p3, start=1):
            OpcionConfig.objects.create(
                pregunta=p3,
                codigo=cod,
                etiqueta=etq,
                descripcion_auxiliar=desc,
                orden=idx,
                activa=True
            )

        # ----------------------------------------------------
        # Pregunta 4: Región del proyecto
        # ----------------------------------------------------
        p4 = PreguntaConfig.objects.create(
            formulario=form_v2,
            clave='region',
            titulo='¿En qué región desarrollarás el proyecto?',
            ayuda='Consideraremos instrumentos nacionales y de tu región. Algunos llamados exigen una comuna o localidad específica.',
            tipo=TipoPregunta.SELECT,
            limite_seleccion=1,
            orden=4,
            activa=True
        )
        regiones_chile = [
            ('CL-AP', 'Arica y Parinacota'),
            ('CL-TA', 'Tarapacá'),
            ('CL-AN', 'Antofagasta'),
            ('CL-AT', 'Atacama'),
            ('CL-CO', 'Coquimbo'),
            ('CL-VA', 'Valparaíso'),
            ('CL-RM', 'Metropolitana de Santiago'),
            ('CL-OH', "O'Higgins"),
            ('CL-ML', 'Maule'),
            ('CL-NB', 'Ñuble'),
            ('CL-BI', 'Biobío'),
            ('CL-AR', 'La Araucanía'),
            ('CL-LR', 'Los Ríos'),
            ('CL-LL', 'Los Lagos'),
            ('CL-AI', 'Aysén'),
            ('CL-MA', 'Magallanes'),
        ]
        for idx, (cod, etq) in enumerate(regiones_chile, start=1):
            OpcionConfig.objects.create(
                pregunta=p4,
                codigo=cod,
                etiqueta=etq,
                orden=idx,
                activa=True
            )

        # ----------------------------------------------------
        # Pregunta 5: Rubro principal
        # ----------------------------------------------------
        p5 = PreguntaConfig.objects.create(
            formulario=form_v2,
            clave='rubro',
            titulo='¿Cuál es la actividad principal de tu emprendimiento?',
            ayuda='Selecciona el sector que mejor describe tu actividad principal.',
            tipo=TipoPregunta.RADIO,
            limite_seleccion=1,
            orden=5,
            activa=True
        )
        opciones_p5 = [
            ('alimentos', 'Alimentos y elaboración', 'Producción de alimentos, panaderías, repostería, conservas o elaborados.'),
            ('comercio', 'Comercio', 'Almacenes de barrio, minimarkets, tiendas minoristas y distribución.'),
            ('servicios', 'Servicios', 'Servicios profesionales, técnicos, personales o a empresas.'),
            ('turismo', 'Turismo', 'Alojamiento, gastronomía, tour operadores y experiencias turísticas.'),
            ('agropecuario', 'Agricultura, ganadería o actividad forestal', 'Producción agrícola, pecuaria o silvícola.'),
            ('pesca', 'Pesca o acuicultura', 'Pesca artesanal, recolección de orilla y cultivos acuícolas.'),
            ('cultura', 'Cultura, artesanía e industrias creativas', 'Música, artes visuales, audiovisual, libros, artes escénicas, diseño y artesanía.'),
            ('tecnologia', 'Tecnología y servicios digitales', 'Desarrollo de software, plataformas web, apps o servicios digitales.'),
            ('otro', 'Otro rubro o actividad aún por definir', 'Actividades multisectoriales o sin sector definido.'),
        ]
        for idx, (cod, etq, desc) in enumerate(opciones_p5, start=1):
            OpcionConfig.objects.create(
                pregunta=p5,
                codigo=cod,
                etiqueta=etq,
                descripcion_auxiliar=desc,
                orden=idx,
                activa=True
            )

        # Desactivar otras versiones
        FormularioConfig.objects.exclude(pk=form_v2.pk).update(es_activa=False)

        self.stdout.write(self.style.SUCCESS("✅ Formulario v2 creado y activado exitosamente con 5 preguntas en una sola página."))
