from django.apps import AppConfig


class UsuarisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuaris'

    def ready(self):
        import usuaris.signals  # noqa: F401
