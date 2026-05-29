import os
from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse

ALLOWED_FILE_SIZE = getattr(settings, "PROSE_ATTACHMENT_ALLOWED_FILE_SIZE", 5)


def validate_file(file):
    file_size = file.size / 1024 / 1024
    return file_size <= ALLOWED_FILE_SIZE


def _safe_filename(name):
    base = os.path.basename(name or "")
    return base.replace("\x00", "")[:255] or "attachment"


def _download_url_for(media_url):
    if "?" in media_url:
        return f"{media_url}&content-disposition=attachment"
    return f"{media_url}?content-disposition=attachment"


def _classify_attachment(content_type):
    """
    Return (kind, previewable) where kind is 'image' or 'file'.
    SVG is never treated as an inline image (XSS risk in <img src>).
    """
    ct = (content_type or "").lower()
    if ct.startswith("image/") and ct != "image/svg+xml":
        return "image", True
    return "file", False


def _content_type_allowed(content_type):
    # Read at call time so tests and runtime can change settings.
    allowed_list = getattr(settings, "PROSE_ATTACHMENT_ALLOWED_CONTENT_TYPES", None)
    if not allowed_list:
        return True
    ct = (content_type or "").lower()
    allowed = {x.lower() for x in allowed_list if x}
    return ct in allowed


def upload_attachment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    if "file" not in request.FILES:
        return JsonResponse({"error": "No file provided."}, status=400)

    attachment = request.FILES["file"]
    if not validate_file(attachment):
        return JsonResponse(
            {"error": f"Files must be {ALLOWED_FILE_SIZE}MB or smaller."},
            status=400,
        )

    content_type = getattr(attachment, "content_type", "") or ""
    if not _content_type_allowed(content_type):
        return JsonResponse(
            {"error": "This file type is not allowed."},
            status=400,
        )

    attachment_dir = datetime.now().strftime("%Y/%m/%d")
    attachment_id = uuid4()
    original_name = _safe_filename(attachment.name)
    if "." in original_name:
        attachment_extension = original_name.rsplit(".", 1)[-1]
    else:
        attachment_extension = "bin"
    key = f"{attachment_dir}/{attachment_id}.{attachment_extension}"
    path = f"prose/{key}"
    default_storage.save(path, attachment)

    media_url = default_storage.url(path)
    kind, previewable = _classify_attachment(content_type)

    payload = {
        "url": media_url,
        "download_url": _download_url_for(media_url),
        "filename": original_name,
        "content_type": content_type or "application/octet-stream",
        "size": attachment.size,
        "kind": kind,
        "previewable": previewable,
    }
    return JsonResponse(payload, status=201)
