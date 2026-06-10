from django.conf import settings
from django.db import models

from prose.attachables import AttachableMixin
from prose.fields import RichTextField
from prose.models import Document


class Contributor(AttachableMixin, models.Model):
    """Mentionable person for @-prompts in comment rich text."""

    attachment_name = "mention"
    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.initials:
            parts = self.name.split()
            self.initials = "".join(part[0].upper() for part in parts[:2] if part)
        super().save(*args, **kwargs)

    def attachment_search_text(self):
        return f"{self.name} {self.initials}".strip()

    def render_attachment_html(self, *, context="display"):
        from prose.template_utils import render_attachable_template

        template = (
            "blog/prompts/mention_editor.html"
            if context == "editor"
            else "blog/prompts/mention_display.html"
        )
        return render_attachable_template(
            template,
            {"contributor": self, "attachable": self},
        )


class Article(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    excerpt = RichTextField(blank=True, default="")
    body = models.OneToOneField(Document, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} by {self.author.username}: {self.body}"


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    body = RichTextField(blank=True, default="")
