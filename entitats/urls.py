from django.urls import path

from .views import EntitatCreateView, EntitatListView, EntitatUpdateView, ImportEntitiesCronView

urlpatterns = [
    path('', EntitatListView.as_view(), name='entitat_list'),
    path('nova/', EntitatCreateView.as_view(), name='entitat_create'),
    path('cron/import/', ImportEntitiesCronView.as_view(), name='import_entitats_cron'),
    path('<int:pk>/editar/', EntitatUpdateView.as_view(), name='entitat_update'),
]
