import os
from django.core.management.base import BaseCommand
from orientador.services.legacy_converter import convertir_base_inicial


class Command(BaseCommand):
    help = 'Convierte y normaliza la base legacy Base_fondos_no_reembolsables_Chile_MVP-2.xlsx al modelo canónico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Base_fondos_no_reembolsables_Chile_MVP-2.xlsx',
            help='Ruta del archivo Excel legacy'
        )
        parser.add_argument(
            '--publicar',
            action='store_true',
            help='Cargar los registros directamente como publicados en lugar de borrador'
        )

    def handle(self, *args, **options):
        filepath = options['file']
        publicar = options['publicar']

        if not os.path.exists(filepath):
            self.stderr.write(self.style.ERROR(f"No se encontró el archivo: {filepath}"))
            return

        self.stdout.write(self.style.NOTICE(f"Iniciando conversión de {filepath}..."))
        reporte = convertir_base_inicial(filepath, publicar_directo=publicar)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Conversión completada exitosamente:\n"
            f"  - Entidades creadas: {reporte['entidades_creadas']} (existentes: {reporte['entidades_existentes']})\n"
            f"  - Instrumentos creados: {reporte['instrumentos_creados']} (existentes: {reporte['instrumentos_existentes']})\n"
            f"  - Convocatorias creadas: {reporte['convocatorias_creadas']} (existentes: {reporte['convocatorias_existentes']})\n"
            f"  - Estado editorial asignado: {'publicado' if publicar else 'borrador'}\n"
        ))

        if reporte['advertencias']:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Advertencias ({len(reporte['advertencias'])}):"))
            for adv in reporte['advertencias'][:10]:
                self.stdout.write(f"  - {adv}")
