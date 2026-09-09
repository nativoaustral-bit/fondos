from django.core.management.base import BaseCommand
from orientador.models import (
    ConfiguracionGlobal, FormularioConfig, PreguntaConfig, OpcionConfig, TipoPregunta
)


class Command(BaseCommand):
    help = 'Inicializa la configuración global y el cuestionario oficial de 5 preguntas'

    def handle(self, *args, **options):
        # 1. Configuración global
        config = ConfiguracionGlobal.get_solo()
        config.nombre_plataforma = 'Humm Financiamiento'
        config.url_retorno_comunidad = 'https://comunidad.humm.cl/herramientas'
        config.dias_revision_abierta = 7
        config.dias_revision_instrumento = 90
        config.save()
        self.stdout.write(self.style.SUCCESS("Configuración global inicializada."))

        # 2. Formulario oficial v1
        form, _ = FormularioConfig.objects.get_or_create(
            version=1,
            defaults={
                'nombre': 'Cuestionario Oficial Humm Fondos v1.0',
                'es_activa': True,
                'descripcion': '5 preguntas oficiales según especificación de septiembre 2026'
            }
        )
        form.es_activa = True
        form.save()

        # Pregunta 1: Necesidades
        p1, _ = PreguntaConfig.objects.get_or_create(
            formulario=form,
            clave='necesidades',
            defaults={
                'titulo': '¿Qué necesitas financiar?',
                'ayuda': 'Elige hasta dos necesidades principales.',
                'tipo': TipoPregunta.CHECKBOX_LIMIT,
                'limite_seleccion': 2,
                'orden': 1,
                'activa': True,
            }
        )
        opciones_p1 = [
            ('equipamiento', 'Equipos y herramientas', 'Maquinaria, herramientas de trabajo, equipos tecnológicos o mobiliario.', 1),
            ('capital_trabajo', 'Insumos y capital de trabajo', 'Materias primas, mercadería, insumos de producción y costos operativos.', 2),
            ('ventas_digital', 'Ventas y digitalización', 'Marketing, comercio electrónico, desarrollo web, branding y publicidad.', 3),
            ('prototipo', 'Prototipo o validación de una idea', 'Diseño de prototipos, pruebas técnicas, pilotaje y validación comercial.', 4),
            ('infraestructura', 'Habilitación o infraestructura', 'Adecuación de local, taller, habilitación sanitaria o mejoras de espacio.', 5),
            ('asistencia_tecnica', 'Asesorías, capacitación o certificaciones', 'Consultorías especializadas, certificaciones de calidad y formación técnica.', 6),
        ]
        for cod, etq, desc, ordn in opciones_p1:
            OpcionConfig.objects.update_or_create(
                pregunta=p1, codigo=cod,
                defaults={'etiqueta': etq, 'descripcion_auxiliar': desc, 'orden': ordn, 'activa': True}
            )

        # Pregunta 2: Situación
        p2, _ = PreguntaConfig.objects.get_or_create(
            formulario=form,
            clave='situacion',
            defaults={
                'titulo': '¿En qué situación está tu emprendimiento?',
                'ayuda': 'Selecciona la opción que mejor describa tu momento actual.',
                'tipo': TipoPregunta.RADIO,
                'limite_seleccion': 1,
                'orden': 2,
                'activa': True,
            }
        )
        opciones_p2 = [
            ('idea', 'Tengo una idea y todavía no vendo', 'Proyecto en fase conceptual o inicial.', 1),
            ('prototipo', 'Estoy desarrollando o probando un prototipo', 'Tengo un modelo o versión preliminar en pruebas.', 2),
            ('ventas_informales', 'Ya vendo, pero mi negocio no está formalizado', 'Actividad comercial activa sin inicio de actividades ante el SII.', 3),
            ('ventas_formales', 'Tengo un negocio formalizado y ventas a pequeña escala', 'Empresa con inicio de actividades en 1ª categoría ante el SII.', 4),
        ]
        for cod, etq, desc, ordn in opciones_p2:
            OpcionConfig.objects.update_or_create(
                pregunta=p2, codigo=cod,
                defaults={'etiqueta': etq, 'descripcion_auxiliar': desc, 'orden': ordn, 'activa': True}
            )

        # Pregunta 3: Región
        p3, _ = PreguntaConfig.objects.get_or_create(
            formulario=form,
            clave='region',
            defaults={
                'titulo': '¿En qué región desarrollarás el proyecto?',
                'ayuda': 'Filtraremos fondos de cobertura nacional y fondos exclusivos de tu territorio.',
                'tipo': TipoPregunta.SELECT,
                'limite_seleccion': 1,
                'orden': 3,
                'activa': True,
            }
        )
        regiones = [
            ('CL-AP', 'Arica y Parinacota', 1),
            ('CL-TA', 'Tarapacá', 2),
            ('CL-AN', 'Antofagasta', 3),
            ('CL-AT', 'Atacama', 4),
            ('CL-CO', 'Coquimbo', 5),
            ('CL-VA', 'Valparaíso', 6),
            ('CL-RM', 'Metropolitana de Santiago', 7),
            ('CL-OH', "O'Higgins", 8),
            ('CL-ML', 'Maule', 9),
            ('CL-NB', 'Ñuble', 10),
            ('CL-BI', 'Biobío', 11),
            ('CL-AR', 'La Araucanía', 12),
            ('CL-LR', 'Los Ríos', 13),
            ('CL-LL', 'Los Lagos', 14),
            ('CL-AI', 'Aysén', 15),
            ('CL-MA', 'Magallanes y de la Antártica Chilena', 16),
        ]
        for cod, etq, ordn in regiones:
            OpcionConfig.objects.update_or_create(
                pregunta=p3, codigo=cod,
                defaults={'etiqueta': etq, 'orden': ordn, 'activa': True}
            )

        # Pregunta 4: Monto buscado
        p4, _ = PreguntaConfig.objects.get_or_create(
            formulario=form,
            clave='monto_buscado',
            defaults={
                'titulo': '¿Cuánto financiamiento buscas aproximadamente?',
                'ayuda': 'Referencia para ordenar opciones. No excluye fondos que cubran parte de tu meta.',
                'tipo': TipoPregunta.RADIO,
                'limite_seleccion': 1,
                'orden': 4,
                'activa': True,
            }
        )
        opciones_p4 = [
            ('menor_1m', 'Menos de $1 millón', 'Para compras iniciales o insumos específicos.', 1),
            ('de_1m_a_3_5m', 'Entre $1 y $3,5 millones', 'Rango habitual de fondos semilla básicos.', 2),
            ('mas_3_5m_a_10m', 'Más de $3,5 y hasta $10 millones', 'Equipamiento o ampliación productiva.', 3),
            ('mas_10m_a_20m', 'Más de $10 y hasta $20 millones', 'Proyectos de escalamiento o innovación.', 4),
            ('mas_20m', 'Más de $20 millones', 'Inversión de mayor envergadura.', 5),
            ('no_se', 'Aún no lo sé', 'Ver todas las opciones disponibles sin filtro de monto.', 6),
        ]
        for cod, etq, desc, ordn in opciones_p4:
            OpcionConfig.objects.update_or_create(
                pregunta=p4, codigo=cod,
                defaults={'etiqueta': etq, 'descripcion_auxiliar': desc, 'orden': ordn, 'activa': True}
            )

        # Pregunta 5: Rubro
        p5, _ = PreguntaConfig.objects.get_or_create(
            formulario=form,
            clave='rubro',
            defaults={
                'titulo': '¿Cuál es el rubro principal de tu emprendimiento?',
                'ayuda': 'Identifica programas multisectoriales o fondos específicos para tu industria.',
                'tipo': TipoPregunta.RADIO,
                'limite_seleccion': 1,
                'orden': 5,
                'activa': True,
            }
        )
        opciones_p5 = [
            ('alimentos', 'Alimentos y elaboración', 'Producción de alimentos, repostería, conservas y gastronomía.', 1),
            ('comercio', 'Comercio', 'Venta minorista, almacenes, tiendas físicas u online.', 2),
            ('servicios', 'Servicios', 'Servicios profesionales, técnicos, personales o a empresas.', 3),
            ('turismo', 'Turismo', 'Alojamiento, gastronomía turística, excursiones y actividades.', 4),
            ('agro_rural', 'Agricultura o actividad rural', 'Producción agrícola, ganadería, huertos y mundo rural.', 5),
            ('pesca', 'Pesca o acuicultura', 'Pesca artesanal, recolección y cultivos acuícolas.', 6),
            ('cultura_artesania', 'Cultura o artesanía', 'Creación artística, artesanía tradicional o industrias creativas.', 7),
            ('tecnologia', 'Tecnología', 'Desarrollo de software, plataformas digitales y hardware.', 8),
            ('otro', 'Otro rubro', 'Cualquier otra actividad no clasificada anteriormente.', 9),
        ]
        for cod, etq, desc, ordn in opciones_p5:
            OpcionConfig.objects.update_or_create(
                pregunta=p5, codigo=cod,
                defaults={'etiqueta': etq, 'descripcion_auxiliar': desc, 'orden': ordn, 'activa': True}
            )

        self.stdout.write(self.style.SUCCESS("✅ Cuestionario de 5 preguntas configurado exitosamente."))
