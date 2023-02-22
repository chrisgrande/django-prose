from django.core.files.storage import default_storage
from django.http import JsonResponse

from django.conf import settings
from prose.models import Attachment

import filetype


def validate_file(file):
    if hasattr(settings, "PROSE_ATTACHMENT_ALLOWED_FILE_TYPES"):
        allowed_file_types = settings.PROSE_ATTACHMENT_ALLOWED_FILE_TYPES
    else:
        allowed_file_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
        ]
    if hasattr(settings, "PROSE_ATTACHMENT_ALLOWED_FILE_SIZE"):
        allowed_file_size = settings.PROSE_ATTACHMENT_ALLOWED_FILE_SIZE
    else:
        allowed_file_size = 5
    file_type = filetype.guess(file).mime
    file_size = file.size / 1024 / 1024
    if file_type in allowed_file_types and file_size <= allowed_file_size:
        return True
    return False


def upload_attachment(request):
    if request.method == "POST":
        file = request.FILES["file"]
        if not validate_file(file):
            return JsonResponse({"error": "File type or size not allowed"}, status=400)
        # Create Attachment object
        attachment = Attachment.objects.create(with_file=file)
        path = attachment.file.name
        payload = {
            "url": default_storage.url(path),
        }
        return JsonResponse(payload, status=201)
