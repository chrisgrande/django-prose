import json
import os
from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils.module_loading import import_string
from django.views.decorators.http import require_http_methods

from prose.attachables import resolve_attachable
from prose.attachment_types import (
    YOUTUBE_CONTENT_TYPE,
    content_type_allowed,
    normalize_upload_content_type,
)
from prose.embeds import match_embed_provider
from prose.models import Attachment

ALLOWED_FILE_SIZE = getattr(settings, "PROSE_ATTACHMENT_ALLOWED_FILE_SIZE", 5)


def _upload_permission_check(request):
    dotted = getattr(settings, "PROSE_UPLOAD_PERMISSION", None)
    if not dotted:
        return True
    checker = import_string(dotted)
    return checker(request)


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


def _storage_key(original_name):
    attachment_dir = datetime.now().strftime("%Y/%m/%d")
    attachment_id = uuid4()
    if "." in original_name:
        attachment_extension = original_name.rsplit(".", 1)[-1]
    else:
        attachment_extension = "bin"
    key = f"{attachment_dir}/{attachment_id}.{attachment_extension}"
    return f"prose/{key}"


@require_http_methods(["POST"])
def upload_attachment(request):
    if not _upload_permission_check(request):
        return JsonResponse({"error": "Permission denied."}, status=403)

    if "file" not in request.FILES:
        return JsonResponse({"error": "No file provided."}, status=400)

    uploaded = request.FILES["file"]
    if not validate_file(uploaded):
        return JsonResponse(
            {"error": f"Files must be {ALLOWED_FILE_SIZE}MB or smaller."},
            status=400,
        )

    original_name = _safe_filename(uploaded.name)
    content_type = normalize_upload_content_type(
        getattr(uploaded, "content_type", "") or "",
        original_name,
    )
    if not content_type_allowed(content_type, original_name):
        return JsonResponse(
            {"error": "This file type is not allowed."},
            status=400,
        )
    path = _storage_key(original_name)
    path = default_storage.save(path, uploaded)

    attachment = Attachment.objects.create(
        file=path,
        content_type=content_type or "application/octet-stream",
        filename=original_name,
        byte_size=uploaded.size,
        metadata={"original_filename": original_name},
    )

    payload = attachment.to_lexxy_json()
    payload["download_url"] = _download_url_for(payload["url"])
    return JsonResponse(payload, status=201)


@require_http_methods(["POST"])
def update_attachment_caption(request):
    if not _upload_permission_check(request):
        return JsonResponse({"error": "Permission denied."}, status=403)

    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    sgid = (body.get("sgid") or "").strip()
    caption = (body.get("caption") or "").strip()
    if not sgid:
        return JsonResponse({"error": "No sgid provided."}, status=400)

    attachment = resolve_attachable(sgid)
    if attachment is None or not isinstance(attachment, Attachment):
        return JsonResponse({"error": "Attachment not found."}, status=404)

    metadata = dict(attachment.metadata or {})
    if attachment.content_type == YOUTUBE_CONTENT_TYPE:
        metadata["title"] = caption
        attachment.metadata = metadata
        attachment.filename = caption
        attachment.save(update_fields=["metadata", "filename"])
    elif attachment.kind == "file":
        if "original_filename" not in metadata:
            metadata["original_filename"] = attachment.filename
        metadata["title"] = caption
        attachment.metadata = metadata
        attachment.filename = caption or metadata.get("original_filename", "")
        attachment.save(update_fields=["metadata", "filename"])
    else:
        return JsonResponse({"error": "Attachment not found."}, status=404)

    return JsonResponse(
        {
            "sgid": attachment.attachable_sgid,
            "caption": caption,
            "filename": attachment.filename,
        },
        status=200,
    )


@require_http_methods(["GET"])
def embed_check(request):
    if not _upload_permission_check(request):
        return JsonResponse({"error": "Permission denied."}, status=403)

    url = (request.GET.get("url") or "").strip()
    if not url:
        return JsonResponse({"embeddable": False})

    return JsonResponse({"embeddable": match_embed_provider(url) is not None})


@require_http_methods(["POST"])
def embed_url(request):
    if not _upload_permission_check(request):
        return JsonResponse({"error": "Permission denied."}, status=403)

    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    url = (body.get("url") or "").strip()
    if not url:
        return JsonResponse({"error": "No URL provided."}, status=400)

    provider = match_embed_provider(url)
    if provider is None:
        return JsonResponse(
            {"error": "URL is not supported for embedding."}, status=400
        )

    attachment = provider.create_attachment(url)
    if attachment is None:
        return JsonResponse({"error": "Could not create embed."}, status=400)

    from prose.content import editor_embed_html

    html = provider.render_html(attachment)
    editor_html = editor_embed_html(attachment)
    return JsonResponse(
        {
            "sgid": attachment.attachable_sgid,
            "html": html,
            "editor_html": editor_html,
            "attributes": attachment.to_attachment_attributes(),
            **attachment.to_lexxy_json(),
        },
        status=201,
    )
