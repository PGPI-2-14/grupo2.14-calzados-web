from .production import *  # noqa

import os

DEBUG = False

# Allow PythonAnywhere host; prefer explicit hostname via env for safety
PA_HOSTNAME = os.environ.get('PA_HOSTNAME')  # e.g. 'tuusuario.pythonanywhere.com'
if PA_HOSTNAME and PA_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(PA_HOSTNAME)
elif '.pythonanywhere.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.pythonanywhere.com')

# CSRF trusted origin for HTTPS on PythonAnywhere
if PA_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = [f'https://{PA_HOSTNAME}']

# Fallback to SQLite when DATABASE_URL is not defined
db_default = DATABASES.get('default') if 'DATABASES' in globals() else None
needs_fallback = False
if not db_default or not isinstance(db_default, dict):
    needs_fallback = True
else:
    engine = db_default.get('ENGINE')
    # dj_database_url.config() returns {} if not set, so ENGINE may be missing
    if not engine:
        needs_fallback = True

if needs_fallback:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }

# Ensure static settings are correct (inherited from production):
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATIC_URL = '/static/'
# STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

# Relax manifest requirement to avoid collectstatic failing on missing vendor assets referenced in CSS
# (e.g., jquery-ui theme images). WhiteNoise will still compress and serve static files.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# When forcing MockDB in production, avoid DB-backed sessions
if os.environ.get('USE_MOCKDB') == '1':
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
    # No se configura SMTP en este entorno; el envío real de correos queda deshabilitado.
