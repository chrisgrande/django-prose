"""MIME allowlists and labels for prose attachments (editor + upload validation)."""

from django.conf import settings

from prose.attachables import registry, vendor_content_type

YOUTUBE_CONTENT_TYPE = vendor_content_type("youtube")

# Editor drag/drop + picker (wildcards supported in JS; exact + wildcard here).
DEFAULT_PERMITTED_ATTACHMENT_TYPES = [
    "image/*",
    "video/*",
    "application/pdf",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/*",
    YOUTUBE_CONTENT_TYPE,
]

EXTENSION_TO_MIME = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

MIME_LABELS = {
    "application/pdf": "PDF",
    "application/msword": "Word document",
    "application/vnd.ms-excel": "Excel spreadsheet",
    "application/vnd.ms-powerpoint": "PowerPoint presentation",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel spreadsheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint presentation",
}


def get_permitted_attachment_types():
    """
    MIME patterns allowed for attachments (editor + upload validation).

    PROSE_PERMITTED_ATTACHMENT_TYPES replaces the built-in defaults entirely
    when set; it is not merged. Wildcards such as image/* are supported.

    Registered attachable content types (mentions, etc.) are always appended so
    Lexxy prompts stay active even when a custom allowlist is configured.
    """
    custom = getattr(settings, "PROSE_PERMITTED_ATTACHMENT_TYPES", None)
    if custom is not None:
        types = [t for t in custom if t]
    else:
        types = list(DEFAULT_PERMITTED_ATTACHMENT_TYPES)

    for content_type in registry.content_types():
        if content_type not in types:
            types.append(content_type)
    return types


def mime_from_filename(filename):
    if not filename or "." not in filename:
        return ""
    ext = filename.rsplit(".", 1)[-1].lower()
    return EXTENSION_TO_MIME.get(ext, "")


def content_type_label(content_type, filename=""):
    ct = (content_type or "").lower()
    if ct in MIME_LABELS:
        return MIME_LABELS[ct]
    inferred = mime_from_filename(filename)
    if inferred and inferred in MIME_LABELS:
        return MIME_LABELS[inferred]
    if ct == YOUTUBE_CONTENT_TYPE:
        return "YouTube video"
    if ct.startswith("image/"):
        return "Image"
    if ct.startswith("video/"):
        return "Video"
    if ct.startswith("application/"):
        subtype = ct.split("/", 1)[-1]
        if subtype.endswith("+xml") and "document" in subtype:
            return "Office document"
        return subtype.replace(".", " ").replace("_", " ").title() or "Document"
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].upper() + " file"
    return "File"


def _pattern_matches(content_type, pattern):
    pattern = (pattern or "").lower()
    ct = (content_type or "").lower()
    if not pattern:
        return False
    if pattern == ct:
        return True
    if pattern.endswith("/*"):
        prefix = pattern[:-1]
        return ct.startswith(prefix)
    return False


def matches_permitted_type(content_type, filename, permitted_types):
    """Return True if content_type or filename extension matches any permitted pattern."""
    if not permitted_types:
        return True
    ct = (content_type or "").lower()
    if ct and any(_pattern_matches(ct, p) for p in permitted_types):
        return True
    inferred = mime_from_filename(filename)
    if inferred and any(_pattern_matches(inferred, p) for p in permitted_types):
        return True
    if not ct and not inferred:
        return any(
            p in ("application/*", "*/*")
            for p in permitted_types
        )
    return False


def normalize_upload_content_type(content_type, filename):
    """
    Browsers often send application/zip or an empty type for Office files; prefer
  the extension when the declared type is missing or generic.
    """
    ct = (content_type or "").lower().strip()
    inferred = mime_from_filename(filename)
    if not inferred:
        return ct
    if not ct or ct in ("application/octet-stream", "application/zip", "binary/octet-stream"):
        return inferred
    return ct


def content_type_allowed(content_type, filename="", permitted_types=None):
    if permitted_types is None:
        permitted_types = get_permitted_attachment_types()
    normalized = normalize_upload_content_type(content_type, filename)
    return matches_permitted_type(normalized, filename, permitted_types)
