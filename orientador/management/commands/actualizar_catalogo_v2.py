"""
Comando de actualización y saneamiento de datos del catálogo — Humm Financiamiento
Aplica las correcciones del documento 'Revisión de orientaciones y formulario v2' (Septiembre 2026).
"""

from django.core.management.base import BaseCommand
from orientador.models import Entidad, Instrumento, Convocatoria, ConfiguracionGlobal


class Command(BaseCommand):
    help = 'Actualiza y sanea el catálogo inicial para alinearse con Formulario v2 y Esquema 1.1'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando saneamiento del catálogo Humm...")

        # 1. Corrección territorial de CONV-010 (Inicia tu Negocio Turismo Cisnes Litoral)
        try:
            c10 = Convocatoria.objects.get(convocatoria_id='CONV-010')
            c10.cobertura = 'comunal'
            c10.regiones = 'CL-AI'
            c10.comunas = 'Cisnes'
            c10.rubros = 'turismo'
            c10.objetivos = 'iniciar_negocio'
            c10.save()
            self.stdout.write(self.style.SUCCESS("✅ CONV-010 corregida: Cobertura comunal (Cisnes, Aysén CL-AI), rubro turismo."))
        except Convocatoria.DoesNotExist:
            self.stdout.write(self.style.WARNING("⚠️ CONV-010 no encontrada."))

        # 2. Restitución de tipos reales para Entidades ENT-014 a ENT-019
        tipos_entidades = {
            'ENT-014': ('Fundación Luksic', 'sociedad_civil'),
            'ENT-015': ('G100 / Nada Nos Detiene', 'sociedad_civil'),
            'ENT-016': ('Banco de Chile', 'privada'),
            'ENT-017': ('Santander Chile', 'privada'),
            'ENT-018': ('Caja Los Andes', 'privada'),
            'ENT-019': ('Fundación Copec-UC', 'sociedad_civil'),
        }
        for eid, (nombre, tipo) in tipos_entidades.items():
            ent = Entidad.objects.filter(entidad_id=eid).first()
            if ent:
                ent.tipo = tipo
                ent.save()
                self.stdout.write(f"  - {eid} ({nombre}): tipo actualizado a '{tipo}'")

        # 3. Restitución de ENT-003 (Corfo) para INS-019 a INS-022 e INS-026 a INS-028
        inst_corfo = ['INS-019', 'INS-020', 'INS-021', 'INS-022', 'INS-026', 'INS-027', 'INS-028']
        corfo_ent = Entidad.objects.filter(entidad_id='ENT-003').first()
        if corfo_ent:
            for iid in inst_corfo:
                inst = Instrumento.objects.filter(instrumento_id=iid).first()
                if inst:
                    inst.entidad = corfo_ent
                    inst.save()
            self.stdout.write(self.style.SUCCESS(f"✅ {len(inst_corfo)} instrumentos reasignados a ENT-003 (Corfo)."))

        # 4. Saneamiento de Sercotec Capital Semilla / Abeja (INS-005, INS-006)
        for iid in ['INS-005', 'INS-006']:
            inst = Instrumento.objects.filter(instrumento_id=iid).first()
            if inst:
                inst.formalizacion_requerida = 'sin_inicio_primera'
                inst.ventas_requeridas = 'no'
                inst.objetivos = 'iniciar_negocio'
                inst.save()
        self.stdout.write(self.style.SUCCESS("✅ INS-005 y INS-006 formalización actualizada a 'sin_inicio_primera', ventas 'no'."))

        # 5. Sercotec Crece (INS-008, INS-010) y Digitaliza tu Almacén (INS-011)
        crece = Instrumento.objects.filter(instrumento_id='INS-008').first()
        if crece:
            crece.formalizacion_requerida = 'con_inicio_primera'
            crece.ventas_requeridas = 'si'
            crece.objetivos = 'fortalecer_negocio'
            crece.save()

        crece_sos = Instrumento.objects.filter(instrumento_id='INS-010').first()
        if crece_sos:
            crece_sos.formalizacion_requerida = 'con_inicio_primera'
            crece_sos.ventas_requeridas = 'si'
            crece_sos.objetivos = 'fortalecer_negocio;sostenibilidad'
            crece_sos.save()

        almacen = Instrumento.objects.filter(instrumento_id='INS-011').first()
        if almacen:
            almacen.rubros = 'comercio;alimentos'
            almacen.objetivos = 'vender_digitalizar'
            almacen.formalizacion_requerida = 'con_inicio_primera'
            almacen.ventas_requeridas = 'si'
            almacen.save()
        self.stdout.write(self.style.SUCCESS("✅ Crece y Digitaliza tu Almacén actualizados con rubros y objetivos específicos."))

        # 6. Fondos Culturales (INS-053 a INS-059)
        culturales = Instrumento.objects.filter(instrumento_id__in=[f'INS-0{n:02d}' for n in range(53, 60)])
        for c_inst in culturales:
            c_inst.rubros = 'cultura'
            c_inst.objetivos = 'proyecto_cultural'
            if 'produccion_cultural' not in c_inst.necesidades:
                c_inst.necesidades = 'produccion_cultural'
            c_inst.save()
        self.stdout.write(self.style.SUCCESS(f"✅ {culturales.count()} fondos culturales asignados a rubro 'cultura', objetivo 'proyecto_cultural'."))

        # 7. Fondos FIA (INS-043 a INS-047) e INDAP (INS-036 a INS-042)
        fia_inst = Instrumento.objects.filter(entidad_id='ENT-009')
        for f in fia_inst:
            f.rubros = 'agropecuario'
            f.objetivos = 'desarrollar_innovacion'
            f.save()

        indap_inst = Instrumento.objects.filter(entidad_id='ENT-008')
        for ind in indap_inst:
            ind.rubros = 'agropecuario'
            ind.objetivos = 'iniciar_negocio;fortalecer_negocio'
            ind.save()
        self.stdout.write(self.style.SUCCESS(f"✅ Fondos FIA e INDAP sectorializados en 'agropecuario'."))

        # 8. Fondos INDESPA (INS-049 a INS-052)
        indespa_inst = Instrumento.objects.filter(entidad_id='ENT-010')
        for ind in indespa_inst:
            ind.rubros = 'pesca'
            ind.objetivos = 'iniciar_negocio;fortalecer_negocio'
            ind.save()
        self.stdout.write(self.style.SUCCESS(f"✅ Fondos INDESPA sectorializados en 'pesca'."))

        # 9. Startup Ciencia (INS-048), Súmate a Innovar (INS-026), Crea y Valida (INS-027), Semilla Inicia (INS-019, INS-020)
        sc = Instrumento.objects.filter(instrumento_id='INS-048').first()
        if sc:
            sc.rubros = 'tecnologia'
            sc.objetivos = 'desarrollar_innovacion'
            sc.formalizacion_requerida = 'con_inicio_primera'
            sc.ventas_requeridas = 'no'
            sc.save()

        si = Instrumento.objects.filter(instrumento_id='INS-026').first()
        if si:
            si.objetivos = 'desarrollar_innovacion'
            si.formalizacion_requerida = 'con_inicio_primera'
            si.ventas_requeridas = 'si'
            si.save()

        cyv = Instrumento.objects.filter(instrumento_id='INS-027').first()
        if cyv:
            cyv.objetivos = 'desarrollar_innovacion'
            cyv.formalizacion_requerida = 'con_inicio_primera'
            cyv.ventas_requeridas = 'si'
            cyv.save()

        for in_id in ['INS-019', 'INS-020']:
            sinicia = Instrumento.objects.filter(instrumento_id=in_id).first()
            if sinicia:
                sinicia.objetivos = 'desarrollar_innovacion'
                sinicia.ventas_requeridas = 'indiferente'
                sinicia.save()

        # 10. FOSIS Emprendamos (INS-001 a INS-004)
        for f_id in ['INS-001', 'INS-002', 'INS-003', 'INS-004']:
            finst = Instrumento.objects.filter(instrumento_id=f_id).first()
            if finst:
                finst.objetivos = 'iniciar_negocio' if f_id == 'INS-001' else 'fortalecer_negocio'
                finst.formalizacion_requerida = 'cualquiera'
                finst.ventas_requeridas = 'indiferente'
                finst.save()

        # 11. Incrementar versión de catálogo en configuración global
        config = ConfiguracionGlobal.get_solo()
        config.version_catalogo += 1
        config.save()

        self.stdout.write(self.style.SUCCESS(f"🚀 Saneamiento completado exitosamente. Catálogo actualizado a v{config.version_catalogo}."))
