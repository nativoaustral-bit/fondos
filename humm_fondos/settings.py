"""
Django settings for humm_fondos project.
Orientador de Financiamiento Humm (Humm Fondos)
"""

import json
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar configuración privada (fuera del DocumentRoot si existe)
def _load_private_config():
    candidates = [
        os.environ.get('FONDOS_CONFIG_FILE'),
        '/home1/paulocis/private/fondos_env.json',
        str(BASE_DIR.parent / 'private' / 'fondos_env.json'),
        str(BASE_DIR / 'fondos_env.json'),
        str(BASE_DIR / '.env'),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            try:
                if candidate.endswith('.json'):
                    with open(candidate, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for k, v in data.items():
                            if k not in os.environ and not k.startswith('_'):
                                os.environ[k] = str(v)
                else:
                    with open(candidate, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                k, v = line.split('=', 1)
                                k = k.strip()
                                v = v.strip().strip("'\"")
                                if k not in os.environ:
                                    os.environ[k] = v
                break
            except Exception:
                pass

_load_private_config()

# Producción por defecto: DEBUG siempre es False salvo indicación explícita
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

import sys

IS_TESTING = (
    'test' in sys.argv or
    any('pytest' in arg for arg in sys.argv) or
    'PYTEST_CURRENT_TEST' in os.environ or
    os.environ.get('DJANGO_TESTING') == '1'
)

# SECRET_KEY criptográfica: obligatoria en producción
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG or IS_TESTING:
        SECRET_KEY = 'test-runner-only-secret-key-local-suite-humm-fondos-2026'
    else:
        raise ImproperlyConfigured("SECRET_KEY no configurada en entorno de producción.")
elif not DEBUG and not IS_TESTING and (SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 40):
    raise ImproperlyConfigured("SECRET_KEY insegura detectada en entorno de producción.")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        'ALLOWED_HOSTS',
        'fondos.humm.cl,humm.cl,localhost,127.0.0.1,testserver'
    ).split(',')
    if h.strip()
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'orientador.apps.OrientadorConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'humm_fondos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'orientador' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orientador.context_processors.humm_global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'humm_fondos.wsgi.application'

# Database configuration: Dual SQLite / MySQL
# Defaults to SQLite with a 20s timeout (proven pattern on HostGator).
# If DB_ENGINE=mysql, connects to cPanel MySQL / MariaDB.
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite3').lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'humm_fondos'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DB_PATH = os.environ.get('DB_PATH')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(DB_PATH) if DB_PATH else (BASE_DIR / 'db.sqlite3'),
            'OPTIONS': {
                'timeout': 20,
            }
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization & Chile Santiago Timezone
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'orientador' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (for Excel imports and templates)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Upload limits (OWASP / Spec Section 17)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# CSRF Trusted Origins for HostGator deployment
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:8000,http://127.0.0.1:8000,https://*.humm.cl,http://*.humm.cl'
    ).split(',')
    if origin.strip()
]

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Security Cookies & Headers (OWASP / HostGator HTTPS)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

