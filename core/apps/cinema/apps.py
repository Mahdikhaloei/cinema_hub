from django.apps import AppConfig


class CinemaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cinema'

    def ready(self):
        import apps.cinema.receivers  # noqa
