import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Configura WhiteNoise per servir la carpeta media
# 'root' ha de coincidir amb el teu MEDIA_ROOT (/app/media)
# 'prefix' ha de coincidir amb el teu MEDIA_URL (/media/)
application = WhiteNoise(application, root='/app/media', prefix='/media/')
