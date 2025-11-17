from django.apps import AppConfig
import os
from django.conf import settings

class ShopConfig(AppConfig):
    name = 'shop'

    def ready(self):
        # Activar MockDB si:
        #  - USE_MOCKDB=1 (flag explícito) O
        #  - La BD usa el motor dummy (sin conexión real)
        use_flag = os.environ.get('USE_MOCKDB') == '1'
        is_dummy = False
        try:
            default_db = settings.DATABASES.get('default')
            is_dummy = default_db and default_db.get('ENGINE') == 'django.db.backends.dummy'
        except Exception:
            is_dummy = False

        if use_flag or is_dummy:
            try:
                from tests.mockdb.patcher import MockDB
                MockDB().apply()
                print('[mockdb] MockDB aplicada (managers parcheados desde JSON)')
            except Exception as e:
                print(f'[mockdb] No se pudo aplicar MockDB: {e}')