from django.urls import path

from .views import (
    ActeCreateView,
    ActeDetailView,
    ActeListView,
    ActeUpdateView,
    ElsMeusActesView,
    MarcarAssistenciaView,
    ParticiparActeView,
    ParticipantsListView,
)

urlpatterns = [
    path('', ActeListView.as_view(), name='acte_list'),
    path('meus/', ElsMeusActesView.as_view(), name='els_meus_actes'),
    path('nou/', ActeCreateView.as_view(), name='acte_create'),
    path('<int:pk>/', ActeDetailView.as_view(), name='acte_detail'),
    path('<int:pk>/editar/', ActeUpdateView.as_view(), name='acte_update'),
    path('<int:pk>/participar/', ParticiparActeView.as_view(), name='participar_acte'),
    path('<int:pk>/participants/', ParticipantsListView.as_view(), name='participants_list'),
    path('<int:pk>/participants/<int:participant_pk>/assistencia/', MarcarAssistenciaView.as_view(), name='marcar_assistencia'),
]
