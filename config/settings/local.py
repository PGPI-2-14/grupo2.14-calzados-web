"""Django settings for config project."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables desde ambos lugares para compatibilidad:
# 1) Raíz del repo (padre de 'config')
# 2) Carpeta 'config' (por compatibilidad con equipos que ya lo usaban)
_ROOT_DIR = Path(__file__).resolve().parents[2]
_CONFIG_DIR = Path(__file__).resolve().parent

# Cargar primero raíz y luego config con override=False (no pisa valores ya cargados)
load_dotenv(_ROOT_DIR / ".env", override=False)
load_dotenv(_CONFIG_DIR / ".env", override=False)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# PROJECT_DIR es la carpeta raíz del repo (padre de 'config')
PROJECT_DIR = os.path.dirname(BASE_DIR)

SECRET_KEY = '5yo93-8a^%idwkzxz@6gq67p2ml#sraf4=7#pqg+28mv)koo@m'

DEBUG = True

# Flag para indicar que se está usando la base de datos simulada (MockDB)
USE_MOCKDB = os.environ.get("USE_MOCKDB") in {"1", "true", "True", "YES", "yes", "on", "ON"}

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #third-party apps
    'crispy_forms',

    'accounts.apps.AccountsConfig',
    'shop.apps.ShopConfig',
    'cart.apps.CartConfig',
    'order.apps.OrderConfig',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_DIR, 'templates'),  # habilita la carpeta de plantillas a nivel de proyecto
            os.path.join(BASE_DIR, 'templates'),     # fallback por si existe config/templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# En desarrollo se usa MockDB (sin base de datos real).
# En despliegue, el cliente deberá definir su propia base de datos en production.py.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',  # evita que Django intente abrir SQLite
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


# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(PROJECT_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

MEDIA_ROOT = os.path.join(PROJECT_DIR, "media")
MEDIA_URL = '/media/'


#Crispy templates for form rendering
CRISPY_TEMPLATE_PACK = 'bootstrap4'

CART_SESSION_ID = 'cart'

# --- Modo MockDB: evitar uso de tablas de sesión ---
if USE_MOCKDB:
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    print("Sesiones almacenadas en cookies (sin usar tablas SQL).")

# Email (desarrollo): enviar a consola para pruebas
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@example.com'
