from django.urls import path

from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Estructura / Blocs
    path('estructura/', views.estructura_view, name='estructura'),
    path('estructura/nou/', views.bloc_nou, name='bloc_nou'),
    path('estructura/<int:pk>/editar/', views.bloc_editar, name='bloc_editar'),
    path('estructura/<int:pk>/eliminar/', views.bloc_eliminar, name='bloc_eliminar'),

    # Propostes
    path('propostes/', views.proposta_list, name='proposta_list'),
    path('propostes/nova/', views.proposta_nou, name='proposta_nou'),
    path('propostes/<int:pk>/', views.proposta_detail, name='proposta_detail'),
    path('propostes/<int:pk>/editar/', views.proposta_editar, name='proposta_editar'),
    path('propostes/<int:pk>/canviar-estat/', views.proposta_canviar_estat, name='proposta_canviar_estat'),
    path('propostes/<int:pk>/comentar/', views.proposta_comentar, name='proposta_comentar'),

    # Idees (pluja d'idees)
    path('idees/', views.idea_list, name='idea_list'),
    path('idees/nova/', views.idea_nou, name='idea_nou'),
    path('idees/<int:pk>/', views.idea_detail, name='idea_detail'),
    path('idees/<int:pk>/convertir/', views.idea_convertir, name='idea_convertir'),

    # Idees públiques (gestió interna)
    path('idees-publiques/', views.idees_publiques_list, name='idees_publiques_list'),
    path('idees-publiques/<int:pk>/processar/', views.idea_publica_processar, name='idea_publica_processar'),

    # Formulari públic (sense autenticació)
    path('formulari/', views.formulari_public, name='formulari_public'),
    path('formulari/cerca-persona/', views.formulari_cerca_persona, name='formulari_cerca_persona'),
]
