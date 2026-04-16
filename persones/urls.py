from django.urls import path

from .views import PersonaCreateView, PersonaDetailView, PersonaListView, PersonaUpdateView

urlpatterns = [
    path('', PersonaListView.as_view(), name='persona_list'),
    path('nova/', PersonaCreateView.as_view(), name='persona_create'),
    path('<int:pk>/', PersonaDetailView.as_view(), name='persona_detail'),
    path('<int:pk>/editar/', PersonaUpdateView.as_view(), name='persona_update'),
]
