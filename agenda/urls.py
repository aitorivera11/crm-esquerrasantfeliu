from django.urls import path

from .views import (
    ActeCreateView,
    ActeDetailView,
    ActeIcsView,
    ActeListView,
    ActeUpdateView,
    ConvertImportedActeToOwnedView,
    ElsMeusActesView,
    ImportCityEventsCronView,
    InstagramActeImportView,
    MarcarAssistenciaView,
    ParticiparActeView,
    ParticipantsListView,
    SyncImportedEventsView,
)

urlpatterns = [
    path('', ActeListView.as_view(), name='acte_list'),
    path('meus/', ElsMeusActesView.as_view(), name='els_meus_actes'),
    path('nou/', ActeCreateView.as_view(), name='acte_create'),
    path('nou/importar-instagram/', InstagramActeImportView.as_view(), name='acte_import_instagram'),
    path('cron/import-city-events/', ImportCityEventsCronView.as_view(), name='import_city_events_cron'),
    path('import-city-events/sync/', SyncImportedEventsView.as_view(), name='sync_imported_events'),
    path('<int:pk>/', ActeDetailView.as_view(), name='acte_detail'),
    path('<int:pk>/calendar.ics', ActeIcsView.as_view(), name='acte_ics'),
    path('<int:pk>/editar/', ActeUpdateView.as_view(), name='acte_update'),
    path('<int:pk>/convertir-a-propi/', ConvertImportedActeToOwnedView.as_view(), name='acte_convert_to_owned'),
    path('<int:pk>/participar/', ParticiparActeView.as_view(), name='participar_acte'),
    path('<int:pk>/participants/', ParticipantsListView.as_view(), name='participants_list'),
    path('<int:pk>/participants/<int:participant_pk>/assistencia/', MarcarAssistenciaView.as_view(), name='marcar_assistencia'),
]
