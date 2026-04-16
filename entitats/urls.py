from django.urls import path

from .views import (
    EntitatCreateView,
    EntitatDetailView,
    EntitatListView,
    EntitatUpdateView,
    ImportEntitiesCronView,
    SyncImportedEntitiesView,
)

urlpatterns = [
    path('', EntitatListView.as_view(), name='entitat_list'),
    path('nova/', EntitatCreateView.as_view(), name='entitat_create'),
    path('cron/import/', ImportEntitiesCronView.as_view(), name='import_entitats_cron'),
    path('import/sync/', SyncImportedEntitiesView.as_view(), name='sync_imported_entities'),
    path('<int:pk>/', EntitatDetailView.as_view(), name='entitat_detail'),
    path('<int:pk>/editar/', EntitatUpdateView.as_view(), name='entitat_update'),
]
