from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"

    def ready(self):
        from prose.attachables import registry

        from blog.models import Contributor

        registry.register(Contributor.get_attachment_content_type(), Contributor)
