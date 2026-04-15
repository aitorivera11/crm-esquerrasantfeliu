import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

# Utilitzem la ruta absoluta per evitar confusions de BASE_DIR
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
media_path = os.path.join(base_path, 'media')

application = WhiteNoise(application, root=media_path, prefix='/media/', autorefresh=True)
application.add_files(media_path, prefix='/media/') # Força la lectura dels fitxers media
