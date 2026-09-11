import os
import pytest
from pathlib import Path
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.template.loader import render_to_string
from orientador.models import SolicitudApoyo, Instrumento


@pytest.mark.django_db
class TestOpenRedirectMitigation:
    """Validación permanente de mitigación de Open Redirect en admin_login_view."""

    def test_open_redirect_external_url_blocked(self, client):
        """Una URL externa maliciosa en ?next= debe ser rechazada y reemplazada por /gestion/."""
        malicious_urls = [
            'https://malicious-phishing-site.com',
            'http://evil.com/steal-creds',
            '//evil.com/test',
            'javascript:alert(1)',
        ]
        for bad_url in malicious_urls:
            response = client.get(f'/gestion/login/?next={bad_url}')
            assert response.status_code == 200
            # El formulario no debe contener la URL maliciosa como destino de redirección
            assert bad_url not in response.context['next_url']
            assert response.context['next_url'] == '/gestion/'

    def test_open_redirect_authenticated_user_redirects_safely(self, client):
        """Un usuario ya autenticado con next malicioso debe ir a /gestion/."""
        user = User.objects.create_superuser(username='staff_test', password='password123', email='staff@humm.cl')
        client.force_login(user)

        response = client.get('/gestion/login/?next=https://attacker.com')
        assert response.status_code == 302
        assert response.url == '/gestion/'

    def test_internal_next_url_is_allowed(self, client):
        """Una ruta interna legítima sí debe ser permitida."""
        response = client.get('/gestion/login/?next=/gestion/solicitudes/')
        assert response.status_code == 200
        assert response.context['next_url'] == '/gestion/solicitudes/'


@pytest.mark.django_db
class TestXSSMitigation:
    """Validación de neutralización de payloads XSS en formulario de apoyo."""

    def test_xss_payloads_neutralized_in_response(self, client):
        """Payloads XSS inyectados en el campo nombre deben ser sanitizados y no reflejados como HTML vivo."""
        payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert(1)>',
            '<svg/onload=alert(document.cookie)>',
            '"><script>document.location="http://evil.com"</script>',
        ]

        for payload in payloads:
            response = client.post(reverse('orientador:solicitar_apoyo'), {
                'nombre': payload,
                'canal_contacto': 'email',
                'contacto_valor': 'emprendedor@humm.cl',
                'mensaje': 'Consulta de prueba',
                'autorizacion_contacto': 'si',
            })
            assert response.status_code == 200
            data = response.json()
            assert data['ok'] is True
            # No debe contener el payload ejecutable en crudo
            assert '<script>' not in data['mensaje']
            assert '<img' not in data['mensaje']
            assert '<svg' not in data['mensaje']
            # Debe estar presente la versión sanitizada (HTML entity)
            assert '&lt;' in data['mensaje'] or 'alert' in data['mensaje']


@pytest.mark.django_db
class TestInputValidationLimits:
    """Validación server-side de longitud, canales y formatos (cero 500s)."""

    def test_empty_nombre_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': '',
            'canal_contacto': 'email',
            'contacto_valor': 'test@humm.cl',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False

    def test_oversized_nombre_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'A' * 151,
            'canal_contacto': 'email',
            'contacto_valor': 'test@humm.cl',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False
        assert '150' in response.json()['error']

    def test_invalid_canal_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'telegram',
            'contacto_valor': 'test@humm.cl',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False

    def test_invalid_email_format_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'email',
            'contacto_valor': 'correo-invalido-sin-arroba',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False
        assert 'correo' in response.json()['error'].lower()

    def test_invalid_whatsapp_format_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'whatsapp',
            'contacto_valor': 'no_es_un_telefono',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False

    def test_oversized_contacto_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'email',
            'contacto_valor': ('a' * 140) + '@example.com',
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False

    def test_oversized_mensaje_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'email',
            'contacto_valor': 'test@humm.cl',
            'mensaje': 'M' * 2001,
            'autorizacion_contacto': 'si',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False
        assert '2000' in response.json()['error']

    def test_missing_autorizacion_returns_400(self, client):
        response = client.post(reverse('orientador:solicitar_apoyo'), {
            'nombre': 'Juan Perez',
            'canal_contacto': 'email',
            'contacto_valor': 'test@humm.cl',
            'autorizacion_contacto': 'no',
        })
        assert response.status_code == 400
        assert response.json()['ok'] is False


@pytest.mark.django_db
class TestAdministrationAccessControl:
    """Verificación de que las rutas administrativas requieran autenticación obligatoria."""

    def test_unauthenticated_access_redirects_to_login(self, client):
        admin_routes = [
            '/gestion/',
            '/gestion/catalogo/',
            '/gestion/preguntas/',
            '/gestion/importar-exportar/',
            '/gestion/configuracion/',
        ]
        for route in admin_routes:
            response = client.get(route)
            assert response.status_code == 302, f"Ruta {route} no protegió el acceso anónimo."
            assert '/gestion/login/' in response.url


class TestErrorTemplatesAndHardening:
    """Verificación de plantillas de error y configuración perimetral."""

    def test_error_templates_exist_and_render_cleanly(self):
        """Las plantillas 404.html y 500.html deben existir y renderizar sin variables de traceback."""
        rendered_404 = render_to_string('404.html', {})
        rendered_500 = render_to_string('500.html', {})

        assert '404' in rendered_404
        assert 'Página no encontrada' in rendered_404
        assert 'Traceback' not in rendered_404

        assert '500' in rendered_500
        assert 'problema inesperado' in rendered_500
        assert 'Traceback' not in rendered_500

    def test_htaccess_blocks_sensitive_patterns(self):
        """El archivo .htaccess debe contener reglas explícitas de bloqueo perimetral."""
        htaccess_path = Path(settings.BASE_DIR) / '.htaccess'
        assert htaccess_path.exists(), ".htaccess debe existir en el proyecto."
        content = htaccess_path.read_text(encoding='utf-8')

        assert 'sqlite3' in content
        assert '.git' in content
        assert 'deploy' in content
        assert 'Require all denied' in content

    def test_database_not_tracked_in_git(self):
        """db.sqlite3 no debe estar rastreada por Git."""
        gitignore_path = Path(settings.BASE_DIR) / '.gitignore'
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding='utf-8')
        assert 'db.sqlite3' in content


@pytest.mark.django_db
class TestCatalogAndBusinessContinuity:
    """Verificación de que la lógica de negocio y catálogo continúan operativos tras la remediación."""

    def test_public_form_renders_successfully(self, client):
        response = client.get(reverse('orientador:formulario'))
        assert response.status_code == 200
        assert 'Humm Financiamiento' in response.content.decode('utf-8')
