from django.contrib import admin

from prose.models import Attachment, Document


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "content_type", "byte_size", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "content_preview")

    @admin.display(description="Content")
    def content_preview(self, obj):
        plain_text = obj.get_plain_text_content().strip()
        if not plain_text:
            return "—"
        if len(plain_text) <= 32:
            return plain_text
        return f"{plain_text[:28]}..."
