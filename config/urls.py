from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from core.views import AccessDeniedView

handler403 = AccessDeniedView.as_view()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('allauth.urls')),
    path('agenda/', include(('agenda.urls', 'agenda'), namespace='agenda')),
    path('persones/', include(('persones.urls', 'persones'), namespace='persones')),
    path('entitats/', include(('entitats.urls', 'entitats'), namespace='entitats')),
    path('reunions/', include(('reunions.urls', 'reunions'), namespace='reunions')),
    path('material/', include(('material.urls', 'material'), namespace='material')),
    path('usuaris/', include(('usuaris.urls', 'usuaris'), namespace='usuaris')),
    path('llista-electoral/', include(('llistaelectoral.urls', 'llistaelectoral'), namespace='llistaelectoral')),
    path('', include(('core.urls', 'core'), namespace='core')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
