from django.urls import path

from .views import AccessDeniedView, DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('acces-denegat/', AccessDeniedView.as_view(), name='access_denied'),
]
