from django.urls import path

from .views import (
    LlistaElectoralView,
    assignar_posicio,
    crear_integrant,
    eliminar_integrant,
    editar_integrant,
    exportar_pdf,
    exportar_txt,
    treure_de_posicio,
)

app_name = 'llistaelectoral'

urlpatterns = [
    path('', LlistaElectoralView.as_view(), name='dashboard'),
    path('api/integrants/crear/', crear_integrant, name='crear_integrant'),
    path('api/integrants/eliminar/', eliminar_integrant, name='eliminar_integrant'),
    path('api/integrants/<int:pk>/editar/', editar_integrant, name='editar_integrant'),
    path('api/posicions/assignar/', assignar_posicio, name='assignar_posicio'),
    path('api/posicions/treure/', treure_de_posicio, name='treure_de_posicio'),
    path('exportar/txt/', exportar_txt, name='exportar_txt'),
    path('exportar/pdf/', exportar_pdf, name='exportar_pdf'),
]
