from django.apps import AppConfig


class ProseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prose"
    label = "prose"

    def ready(self):
        import prose.signals  # noqa: F401
