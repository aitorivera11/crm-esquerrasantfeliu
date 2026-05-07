from django.apps import AppConfig


class ReunionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reunions'
    verbose_name = 'Reunions i tasques'

    def ready(self):
        import reunions.signals  # noqa: F401
