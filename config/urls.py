from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import AccessDeniedView

handler403 = AccessDeniedView.as_view()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('agenda/', include(('agenda.urls', 'agenda'), namespace='agenda')),
    path('persones/', include(('persones.urls', 'persones'), namespace='persones')),
    path('entitats/', include(('entitats.urls', 'entitats'), namespace='entitats')),
    path('reunions/', include(('reunions.urls', 'reunions'), namespace='reunions')),
    path('usuaris/', include(('usuaris.urls', 'usuaris'), namespace='usuaris')),
    path('', include(('core.urls', 'core'), namespace='core')),
]
