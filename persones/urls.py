from django.urls import path

from .views import PersonaCreateView, PersonaListView, PersonaUpdateView

urlpatterns = [
    path('', PersonaListView.as_view(), name='persona_list'),
    path('nova/', PersonaCreateView.as_view(), name='persona_create'),
    path('<int:pk>/editar/', PersonaUpdateView.as_view(), name='persona_update'),
]
