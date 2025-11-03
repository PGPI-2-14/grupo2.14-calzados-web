from django.apps import AppConfig
import os
from django.conf import settings

class ShopConfig(AppConfig):
    name = 'shop'

    def ready(self):
        # Activar mock DB en desarrollo si USE_MOCKDB=1
        if getattr(settings, 'DEBUG', False) and os.environ.get('USE_MOCKDB') == '1':
            try:
                from tests.mockdb.patcher import MockDB
                MockDB().apply()
                print('[mockdb] MockDB aplicada (managers parcheados desde JSON)')
            except Exception as e:
                # No romper el arranque si hay algún problema
                print(f'[mockdb] No se pudo aplicar MockDB: {e}')