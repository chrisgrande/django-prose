from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.html import strip_tags

from prose.template_utils import render_prose_template

from prose.attachables import sign_attachable, vendor_content_type
from prose.attachment_types import content_type_label
from prose.fields import DocumentContentField


class Attachment(models.Model):
    file = models.FileField(upload_to="prose/%Y/%m/%d/", null=True, blank=True)
    content_type = models.CharField(max_length=255)
    filename = models.CharField(max_length=255, blank=True, default="")
    byte_size = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def attachable_sgid(self):
        return sign_attachable(self)

    @property
    def attachment_content_type(self):
        return self.content_type

    @property
    def url(self):
        if self.file:
            return self.file.url
        if self.content_type == vendor_content_type("youtube"):
            return self.metadata.get("embed_url") or self.metadata.get("url", "")
        return self.metadata.get("url", "")

    @property
    def original_filename(self):
        return (self.metadata or {}).get("original_filename") or self.filename

    @property
    def file_type_label(self):
        return content_type_label(self.content_type, self.original_filename)

    @property
    def download_url(self):
        url = self.url
        if not url:
            return ""
        if "?" in url:
            return f"{url}&content-disposition=attachment"
        return f"{url}?content-disposition=attachment"

    @property
    def kind(self):
        ct = (self.content_type or "").lower()
        if ct.startswith("image/") and ct != "image/svg+xml":
            return "image"
        if ct == vendor_content_type("youtube"):
            return "embed"
        return "file"

    @property
    def previewable(self):
        if self.kind == "image":
            return True
        if self.kind == "embed" and self.metadata.get("video_id"):
            return True
        return bool(self.metadata.get("previewable"))

    def to_attachment_attributes(self):
        attrs = {
            "sgid": self.attachable_sgid,
            "content-type": self.content_type,
            "url": self.url,
            "filename": self.filename,
            "filesize": self.byte_size,
            "previewable": self.previewable,
        }
        if self.kind == "embed":
            attrs["presentation"] = "gallery"
            caption = self.metadata.get("title") or self.filename
            if caption:
                attrs["caption"] = caption
        return attrs

    def to_lexxy_json(self):
        """Payload for upload/embed API responses."""
        return {
            "sgid": self.attachable_sgid,
            "url": self.url,
            "download_url": self.download_url,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size": self.byte_size,
            "kind": self.kind,
            "previewable": self.previewable,
        }

    def render_attachment_html(self, *, context="display"):
        template_name = self._attachment_template_name(context=context)
        return render_prose_template(
            template_name,
            {"attachment": self, "context": context},
        )

    def _attachment_template_name(self, context="display"):
        ct = self.content_type or ""
        if ct == vendor_content_type("youtube"):
            if context in ("editor", "paste"):
                return "prose/attachments/youtube_editor.html"
            return "prose/attachments/youtube.html"
        if self.kind == "image":
            return "prose/attachments/image.html"
        if self.kind == "embed":
            return "prose/attachments/embed.html"
        if context in ("editor", "paste"):
            return "prose/attachments/file_editor.html"
        return "prose/attachments/file.html"

    def __str__(self):
        return self.filename or f"Attachment {self.pk}"


class RichTextAttachment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    field_name = models.CharField(max_length=64)
    attachment = models.ForeignKey(
        Attachment, on_delete=models.CASCADE, related_name="rich_text_links"
    )

    class Meta:
        unique_together = [("content_type", "object_id", "field_name", "attachment")]

    def __str__(self):
        return f"{self.content_object}.{self.field_name} -> {self.attachment_id}"


class AbstractDocument(models.Model):
    content = DocumentContentField()

    def get_plain_text_content(self):
        return strip_tags(self.content)

    def __str__(self):
        plain_text = self.get_plain_text_content()

        if len(plain_text) < 32:
            return plain_text

        return f"{plain_text[:28]}..."

    class Meta:
        abstract = True


class Document(AbstractDocument):
    pass
