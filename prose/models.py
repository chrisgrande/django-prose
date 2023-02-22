from datetime import datetime
import os
import uuid
from django.db import models
from django.utils.html import strip_tags

from prose.fields import DocumentContentField

import filetype


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


def upload_to(instance, filename):
    # Generate a random filename
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"

    # Organize the files by date
    now = datetime.now()
    folder_name = now.strftime("%Y/%m/%d")

    # Return the upload path
    return os.path.join("attachments", folder_name, filename)


class AttachmentManager(models.Manager):
    def create(self, with_file, for_document):
        # Create the attachment
        attachment = super().create(
            file=with_file,
            byte_size=with_file.size,
            filename=with_file.name,
            content_type=filetype.guess(with_file).mime,
            Document=for_document,
        )
        attachment.save()
        # Return the attachment
        return attachment


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=upload_to, editable=False)
    filename = models.CharField(max_length=120)
    content_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField()
    # metadata = models.TextField()
    # Document = models.ForeignKey(
    #     "Document", to_field="key", on_delete=models.CASCADE, related_name="attachments"
    # )

    def __str__(self):
        return self.filename

    objects = AttachmentManager()


class Document(AbstractDocument):
    pass
