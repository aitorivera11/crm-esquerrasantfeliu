from django.urls import path

from .views import LlistaElectoralView, assignar_posicio, crear_integrant, editar_integrant

app_name = 'llistaelectoral'

urlpatterns = [
    path('', LlistaElectoralView.as_view(), name='dashboard'),
    path('api/integrants/crear/', crear_integrant, name='crear_integrant'),
    path('api/integrants/<int:pk>/editar/', editar_integrant, name='editar_integrant'),
    path('api/posicions/assignar/', assignar_posicio, name='assignar_posicio'),
]
