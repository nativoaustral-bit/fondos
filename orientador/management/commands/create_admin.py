import getpass
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea un administrador para Humm Financiamiento sin credenciales por defecto'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Nombre de usuario del administrador')
        parser.add_argument('--email', type=str, help='Correo del administrador')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']

        if not username:
            username = input("Nombre de usuario para el administrador: ").strip()
        if not email:
            email = input("Correo electrónico: ").strip()

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"El usuario '{username}' ya existe. Deseas actualizarlo a superusuario? (s/n)"))
            resp = input().strip().lower()
            if resp == 's':
                user = User.objects.get(username=username)
                user.is_staff = True
                user.is_superuser = True
                pwd = getpass.getpass("Nueva contraseña: ")
                if pwd:
                    user.set_password(pwd)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Usuario '{username}' actualizado como administrador."))
            return

        password = getpass.getpass("Contraseña segura: ")
        password_confirm = getpass.getpass("Confirma la contraseña: ")

        if password != password_confirm:
            self.stderr.write(self.style.ERROR("Las contraseñas no coinciden. Operación cancelada."))
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Administrador '{username}' creado exitosamente."))
