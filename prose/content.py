import mimetypes
import os
import re
from html import escape, unescape
from urllib.parse import unquote, urlparse

from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage

from prose.attachables import AttachableMixin, resolve_attachable, vendor_content_type
from prose.attachment_types import normalize_upload_content_type

PROSE_ATTACHMENT_TAG = "prose-attachment"
YOUTUBE_CONTENT_TYPE = vendor_content_type("youtube")
_SGID_PATTERN = re.compile(
    rf"<{PROSE_ATTACHMENT_TAG}[^>]*\ssgid=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_LEGACY_FIGURE_PATTERN = re.compile(
    r'<figure[^>]*class="[^"]*django-prose-attachment[^"]*"[^>]*>.*?</figure>',
    re.IGNORECASE | re.DOTALL,
)
_LEXXY_ATTACHMENT_FIGURE_PATTERN = re.compile(
    r"<figure\b[^>]*\bclass=['\"][^'\"]*\battachment\b[^'\"]*['\"][^>]*>.*?</figure>",
    re.IGNORECASE | re.DOTALL,
)
_IMG_SRC_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_LINK_HREF_PATTERN = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
_SGID_DATA_PATTERN = re.compile(r'data-prose-sgid=["\']([^"\']+)["\']', re.IGNORECASE)
_EDITOR_YOUTUBE_FIGURE = re.compile(
    r'<figure\b[^>]*\bdata-prose-sgid=["\']([^"\']+)["\'][^>]*>.*?</figure>',
    re.IGNORECASE | re.DOTALL,
)
_YOUTUBE_EMBED_FIGURE = re.compile(
    r"<figure\b[^>]*>.*?</figure>",
    re.IGNORECASE | re.DOTALL,
)


def extract_attachment_sgids(html):
    if not html:
        return []
    sgids = _SGID_PATTERN.findall(html)
    sgids.extend(_SGID_DATA_PATTERN.findall(html))
    return list(dict.fromkeys(sgids))


def _storage_path_from_media_url(url):
    """Map a public media URL to the storage path used by prose uploads (prose/Y/M/D/file)."""
    from django.conf import settings

    if not url:
        return None

    cleaned = unquote((url or "").split("?")[0].strip())
    if not cleaned:
        return None

    path = urlparse(cleaned).path if "://" in cleaned else cleaned
    if not path.startswith("/"):
        path = f"/{path}"

    media_url = (settings.MEDIA_URL or "/media/").strip()
    if media_url.startswith("http"):
        base_path = urlparse(media_url).path.rstrip("/") + "/"
    else:
        base_path = media_url if media_url.endswith("/") else f"{media_url}/"
        if not base_path.startswith("/"):
            base_path = f"/{base_path}"

    candidates = []
    if path.startswith(base_path):
        candidates.append(path[len(base_path) :].lstrip("/"))

    stripped = path.lstrip("/")
    if stripped.startswith("prose/"):
        candidates.append(stripped)

    for relative in candidates:
        if relative.startswith("prose/"):
            return relative
    return None


def _filename_from_trix_figure(figure_html, storage_path):
    figcaption_match = re.search(
        r"<figcaption\b[^>]*>.*?<span[^>]*>([^<]+)</span>",
        figure_html,
        re.IGNORECASE | re.DOTALL,
    )
    if figcaption_match:
        name = _clean_caption_text(figcaption_match.group(1))
        if name:
            return name[:255]

    img_match = _IMG_SRC_PATTERN.search(figure_html)
    if img_match:
        alt_match = re.search(
            r'\balt=(["\'])(.*?)\1',
            img_match.group(0),
            re.IGNORECASE | re.DOTALL,
        )
        if alt_match:
            name = _clean_caption_text(alt_match.group(2))
            if name:
                return name[:255]

    link_match = _LINK_HREF_PATTERN.search(figure_html)
    if link_match:
        anchor_match = re.search(
            r"<a\b[^>]*>(.*?)</a>",
            figure_html,
            re.IGNORECASE | re.DOTALL,
        )
        if anchor_match:
            name = _clean_caption_text(anchor_match.group(1))
            if name:
                return name[:255]

    return os.path.basename(storage_path)


def _resolve_attachment_for_media_url(url, *, create=False, filename_hint=""):
    from prose.models import Attachment

    storage_path = _storage_path_from_media_url(url)
    if not storage_path:
        return None

    attachment = Attachment.objects.filter(file=storage_path).first()
    if attachment:
        return attachment

    basename = os.path.basename(storage_path)
    attachment = (
        Attachment.objects.filter(file__endswith=basename)
        .order_by("-created_at")
        .first()
    )
    if attachment:
        return attachment

    if not create or not default_storage.exists(storage_path):
        return None

    display_name = (filename_hint or basename)[:255]
    content_type = normalize_upload_content_type("", basename)
    if not content_type or content_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(basename)
        if guessed:
            content_type = guessed
    byte_size = default_storage.size(storage_path)
    metadata = {
        "original_filename": display_name,
        "migrated_from": "trix",
    }

    return Attachment.objects.create(
        file=storage_path,
        content_type=content_type or "application/octet-stream",
        filename=display_name,
        byte_size=byte_size,
        metadata=metadata,
    )


def _attachment_for_media_url(url):
    return _resolve_attachment_for_media_url(url, create=False)


def _get_or_create_attachment_for_media_url(url, *, filename_hint=""):
    return _resolve_attachment_for_media_url(
        url, create=True, filename_hint=filename_hint
    )


def _media_url_from_trix_figure(figure_html):
    img_match = _IMG_SRC_PATTERN.search(figure_html)
    if img_match:
        return img_match.group(1)
    link_match = _LINK_HREF_PATTERN.search(figure_html)
    if link_match:
        return link_match.group(1)
    return None


def _trix_figure_to_prose_attachment(figure_html, *, inner_context="display"):
    if _SGID_DATA_PATTERN.search(figure_html):
        return figure_html
    if _is_youtube_embed_figure(figure_html):
        return figure_html

    media_url = _media_url_from_trix_figure(figure_html)
    if not media_url:
        return figure_html

    attachment = _get_or_create_attachment_for_media_url(
        media_url,
        filename_hint=_filename_from_trix_figure(figure_html, _storage_path_from_media_url(media_url) or ""),
    )
    if not attachment:
        return figure_html

    return _prose_attachment_element(attachment, inner_context=inner_context)


def migrate_trix_attachments_in_html(html, *, inner_context="display"):
    """
    Convert Trix-era attachment figures (inline media URLs, no Attachment rows)
    into prose-attachment tags backed by database records.
    """
    if not html:
        return html

    def replace_trix_figure(match):
        return _trix_figure_to_prose_attachment(
            match.group(0),
            inner_context=inner_context,
        )

    html = _LEXXY_ATTACHMENT_FIGURE_PATTERN.sub(replace_trix_figure, html)

    if PROSE_ATTACHMENT_TAG in html:
        return html

    def replace_standalone_img(match):
        full_tag = match.group(0)
        url = match.group(1)
        if not _storage_path_from_media_url(url):
            return full_tag
        attachment = _get_or_create_attachment_for_media_url(url)
        if not attachment:
            return full_tag
        return _prose_attachment_element(attachment, inner_context=inner_context)

    return _IMG_SRC_PATTERN.sub(replace_standalone_img, html)


def _legacy_figure_to_prose_attachment(figure_html):
    return _trix_figure_to_prose_attachment(figure_html, inner_context="display")


def _prose_attachment_element(attachment, *, inner_context="display"):
    attrs = attachment.to_attachment_attributes()
    attr_str = " ".join(
        f'{key}="{escape(str(value))}"'
        for key, value in attrs.items()
        if value is not None and value != ""
    )
    # Stored/display HTML uses an empty wrapper; render_prose_attachments expands it.
    # Inline figures/iframes inside the tag are hoisted by Bleach and duplicate on save.
    if inner_context == "display":
        return f"<{PROSE_ATTACHMENT_TAG} {attr_str}></{PROSE_ATTACHMENT_TAG}>"
    inner = attachment.render_attachment_html(context=inner_context)
    return f"<{PROSE_ATTACHMENT_TAG} {attr_str}>{inner}</{PROSE_ATTACHMENT_TAG}>"


def editor_embed_html(attachment):
    """HTML to insert into Lexxy for a newly created embed attachment."""
    if _is_youtube_attachment(attachment):
        return _lexxy_editor_youtube_element(attachment)
    if _is_custom_attachable(attachment):
        return _lexxy_editor_custom_attachment_element(attachment)
    return _prose_attachment_element(attachment, inner_context="editor")


def _lexxy_editor_youtube_element(attachment):
    """
    Lexxy editor HTML for YouTube: prose-attachment with a content= attribute
    (CustomActionTextAttachmentNode) so the iframe survives load/save cycles.
    """
    inner = attachment.render_attachment_html(context="editor")
    attrs = attachment.to_attachment_attributes()
    attr_parts = [
        f'sgid="{escape(attrs["sgid"])}"',
        f'content-type="{escape(attrs["content-type"])}"',
        f'content="{escape(inner, quote=True)}"',
        f'url="{escape(str(attrs.get("url", "")), quote=True)}"',
        'filename="YouTube video"',
        f'filesize="{escape(str(attrs.get("filesize", 0)))}"',
        'previewable="true"',
    ]
    if attrs.get("presentation"):
        attr_parts.append(f'presentation="{escape(str(attrs["presentation"]))}"')
    # Caption lives in content= (figcaption textarea). A caption= attribute makes
    # Lexxy mirror it as document plain text below the embed.
    return f"<{PROSE_ATTACHMENT_TAG} {' '.join(attr_parts)}></{PROSE_ATTACHMENT_TAG}>"


def _is_custom_attachable(obj):
    return isinstance(obj, AttachableMixin)


def _lexxy_editor_custom_attachment_element(obj):
    """
    Lexxy editor HTML for attachables (mentions, etc.): prose-attachment with a
    content= attribute (CustomActionTextAttachmentNode). Inner HTML in the tag
    body is ignored by Lexxy on load.
    """
    inner = obj.render_attachment_html(context="editor")
    attrs = obj.to_attachment_attributes()
    attr_parts = [
        f'sgid="{escape(attrs["sgid"])}"',
        f'content-type="{escape(attrs["content-type"])}"',
        f'content="{escape(inner, quote=True)}"',
    ]
    return f"<{PROSE_ATTACHMENT_TAG} {' '.join(attr_parts)}></{PROSE_ATTACHMENT_TAG}>"


def _clean_caption_text(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text


def _youtube_caption_from_figure_html(html):
    if not html:
        return None
    data_caption_match = re.search(
        r'data-prose-caption=(["\'])(.*?)\1',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if data_caption_match:
        return _clean_caption_text(unescape(data_caption_match.group(2)))
    textarea_match = re.search(
        r"<textarea\b[^>]*>(.*?)</textarea>",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if textarea_match:
        return _clean_caption_text(textarea_match.group(1))
    span_match = re.search(
        r'class="[^"]*attachment__name[^"]*"[^>]*>(.*?)</',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if span_match:
        return _clean_caption_text(span_match.group(1))
    return None


def _sync_youtube_caption_metadata(attachment, html):
    caption = _youtube_caption_from_figure_html(html)
    if caption is None:
        return attachment
    metadata = dict(attachment.metadata or {})
    if metadata.get("title") == caption and attachment.filename == caption:
        return attachment
    metadata["title"] = caption
    attachment.metadata = metadata
    attachment.filename = caption
    attachment.save(update_fields=["metadata", "filename"])
    return attachment


def _is_youtube_attachment(obj):
    return getattr(obj, "content_type", None) == YOUTUBE_CONTENT_TYPE


def _youtube_prose_attachment_pattern():
    return re.compile(
        rf"<{PROSE_ATTACHMENT_TAG}\b([^>]*)>(.*?)</{PROSE_ATTACHMENT_TAG}>",
        re.IGNORECASE | re.DOTALL,
    )


def _attrs_content_type(attrs_str):
    match = re.search(
        r'\bcontent-type=["\']([^"\']+)["\']',
        attrs_str,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _attrs_sgid(attrs_str):
    match = re.search(
        r'(?:^|\s)sgid=["\']([^"\']+)["\']',
        attrs_str,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _attachment_from_attrs(attrs_str):
    sgid = _attrs_sgid(attrs_str)
    if sgid:
        return resolve_attachable(sgid)
    return None


def _youtube_attachment_from_attrs(attrs_str):
    obj = _attachment_from_attrs(attrs_str)
    if obj is not None and _is_youtube_attachment(obj):
        return obj

    content_match = re.search(
        r'\bcontent=(["\'])(.*?)\1',
        attrs_str,
        re.IGNORECASE | re.DOTALL,
    )
    if content_match:
        from html import unescape

        inner = unescape(content_match.group(2))
        for sgid in _SGID_DATA_PATTERN.findall(inner):
            obj = resolve_attachable(sgid)
            if obj is not None and _is_youtube_attachment(obj):
                return obj
    return None


_LEXXY_PROSE_ATTACHMENT_EXPORT = re.compile(
    rf"<{PROSE_ATTACHMENT_TAG}\b([^>]*\bcontent=[^>]+)>\s*</{PROSE_ATTACHMENT_TAG}>",
    re.IGNORECASE,
)
_PARAGRAPH_PATTERN = re.compile(r"<p\b[^>]*>.*?</p>", re.IGNORECASE | re.DOTALL)


def _youtube_titles_in_html(html):
    titles = set()
    for sgid in extract_attachment_sgids(html):
        obj = resolve_attachable(sgid)
        if obj is None or not _is_youtube_attachment(obj):
            continue
        for value in (obj.filename, (obj.metadata or {}).get("title")):
            if value and str(value).strip():
                titles.add(str(value).strip())
    return titles


def _youtube_duplicate_paragraph_texts(html):
    """Caption/title strings that may appear as stray paragraphs below embeds."""
    titles = _youtube_titles_in_html(html)
    for match in re.finditer(
        r'\bcaption=(["\'])(.*?)\1',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        text = _clean_caption_text(unescape(match.group(2)))
        if text:
            titles.add(text)
    for match in re.finditer(
        r"<textarea\b[^>]*>(.*?)</textarea>",
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        text = _clean_caption_text(match.group(1))
        if text:
            titles.add(text)
    for match in re.finditer(
        r'data-prose-caption=(["\'])(.*?)\1',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        text = _clean_caption_text(unescape(match.group(2)))
        if text:
            titles.add(text)
    return titles


def _paragraph_contains_youtube_embed(paragraph_html):
    lower = paragraph_html.lower()
    return (
        PROSE_ATTACHMENT_TAG in lower
        or "data-prose-sgid" in lower
        or "youtube-nocookie.com/embed" in lower
        or "attachment--youtube" in lower
        or "attachment--embed" in lower
    )


def _strip_duplicate_youtube_title_paragraphs(html):
    """Remove standalone paragraphs Lexxy adds from attachment plainText / captions."""
    titles = _youtube_duplicate_paragraph_texts(html)
    if not titles:
        return html

    def strip_paragraph(match):
        paragraph = match.group(0)
        if _paragraph_contains_youtube_embed(paragraph):
            return paragraph
        text = re.sub(r"<[^>]+>", "", paragraph)
        text = re.sub(r"\s+", " ", unescape(text)).strip()
        if text in titles:
            return ""
        return paragraph

    return _PARAGRAPH_PATTERN.sub(strip_paragraph, html)


def _strip_trailing_youtube_caption_in_embed_paragraphs(html, titles):
    """Remove caption text Lexxy places after </prose-attachment> inside the same <p>."""
    if not titles:
        return html

    def clean_paragraph(match):
        paragraph = match.group(0)
        if not _paragraph_contains_youtube_embed(paragraph):
            return paragraph
        cleaned = paragraph
        for title in sorted(titles, key=len, reverse=True):
            if not title:
                continue
            title_re = re.escape(title)
            cleaned = re.sub(
                rf"(</prose-attachment>)\s*"
                rf"(?:<(?:span|strong|em|b|i|br)\b[^>]*>\s*)?"
                rf"{title_re}\s*"
                rf"(?:</(?:span|strong|em|b|i)>\s*)?"
                rf"(?=</p>)",
                r"\1",
                cleaned,
                flags=re.IGNORECASE,
            )
        return cleaned

    return _PARAGRAPH_PATTERN.sub(clean_paragraph, html)


def _strip_duplicate_youtube_captions(html):
    """Remove duplicate YouTube caption text below embeds (standalone or same-paragraph)."""
    titles = _youtube_duplicate_paragraph_texts(html)
    if not titles:
        return html
    html = _strip_duplicate_youtube_title_paragraphs(html)
    return _strip_trailing_youtube_caption_in_embed_paragraphs(html, titles)


def canonicalize_youtube_for_storage(html):
    """Normalize YouTube embeds to prose-attachment for storage."""
    if not html:
        return html

    if "data-prose-sgid" in html:

        def wrap_figure(match):
            sgid = match.group(1)
            obj = resolve_attachable(sgid)
            if obj is None or not _is_youtube_attachment(obj):
                return match.group(0)
            obj = _sync_youtube_caption_metadata(obj, match.group(0))
            return _prose_attachment_element(obj, inner_context="display")

        html = _EDITOR_YOUTUBE_FIGURE.sub(wrap_figure, html)

    if PROSE_ATTACHMENT_TAG not in html:
        return html

    def normalize_youtube_tag(match):
        attrs_str = match.group(1)
        inner = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
        obj = _youtube_attachment_from_attrs(attrs_str)
        if obj is None:
            return match.group(0)
        if inner:
            obj = _sync_youtube_caption_metadata(obj, inner)
        else:
            content_match = re.search(
                r'\bcontent=(["\'])(.*?)\1',
                attrs_str,
                re.IGNORECASE | re.DOTALL,
            )
            if content_match:
                from html import unescape

                obj = _sync_youtube_caption_metadata(
                    obj, unescape(content_match.group(2))
                )
        return _prose_attachment_element(obj, inner_context="display")

    html = _youtube_prose_attachment_pattern().sub(normalize_youtube_tag, html)
    html = _LEXXY_PROSE_ATTACHMENT_EXPORT.sub(normalize_youtube_tag, html)
    return _strip_duplicate_youtube_captions(html)


def canonicalize_attachables_for_storage(html):
    """Normalize custom attachables to empty prose-attachment wrappers for storage."""
    if not html or PROSE_ATTACHMENT_TAG not in html:
        return html

    def normalize_attachable_tag(match):
        attrs_str = match.group(1)
        obj = _attachment_from_attrs(attrs_str)
        if obj is None or not _is_custom_attachable(obj):
            return match.group(0)
        return _prose_attachment_element(obj, inner_context="display")

    html = _youtube_prose_attachment_pattern().sub(normalize_attachable_tag, html)
    html = _LEXXY_PROSE_ATTACHMENT_EXPORT.sub(normalize_attachable_tag, html)
    return html


def canonicalize_legacy_attachments(html):
    """Migrate Trix / legacy inline attachments to stored prose-attachment tags."""
    if not html:
        return html

    html = migrate_trix_attachments_in_html(html, inner_context="display")

    if "django-prose-attachment" not in html:
        return html

    def replace_figure(match):
        return _legacy_figure_to_prose_attachment(match.group(0))

    return _LEGACY_FIGURE_PATTERN.sub(replace_figure, html)


def _attachment_ids_from_lexxy_figures(html):
    from prose.models import Attachment

    ids = set()
    for figure_html in _LEXXY_ATTACHMENT_FIGURE_PATTERN.findall(html or ""):
        for sgid in _SGID_DATA_PATTERN.findall(figure_html):
            obj = resolve_attachable(sgid)
            if isinstance(obj, Attachment):
                ids.add(obj.pk)
        img_match = _IMG_SRC_PATTERN.search(figure_html)
        if img_match:
            attachment = _attachment_for_media_url(img_match.group(1))
            if attachment:
                ids.add(attachment.pk)
    return ids


def attachment_ids_from_html(html):
    from prose.models import Attachment

    html = html or ""
    ids = set()
    for sgid in extract_attachment_sgids(html):
        obj = resolve_attachable(sgid)
        if isinstance(obj, Attachment):
            ids.add(obj.pk)

    ids.update(_attachment_ids_from_lexxy_figures(html))

    if "django-prose-attachment" in html:
        for figure_match in _LEGACY_FIGURE_PATTERN.finditer(html):
            figure_html = figure_match.group(0)
            media_url = _media_url_from_trix_figure(figure_html)
            if not media_url:
                continue
            attachment = _attachment_for_media_url(media_url)
            if attachment:
                ids.add(attachment.pk)

    return ids


def delete_unlinked_attachments(attachment_ids):
    """Delete attachment rows (and files) no longer referenced anywhere."""
    from prose.models import Attachment, RichTextAttachment

    for attachment_id in attachment_ids:
        if not attachment_id:
            continue
        if RichTextAttachment.objects.filter(attachment_id=attachment_id).exists():
            continue
        Attachment.objects.filter(pk=attachment_id).delete()


def abandoned_attachments_queryset(*, minimum_age=None):
    """
    Attachments with no RichTextAttachment links (uploaded but never saved, or
    removed from content without a successful sync).
    """
    from django.db.models import Exists, OuterRef
    from django.utils import timezone

    from prose.models import Attachment, RichTextAttachment

    links = RichTextAttachment.objects.filter(attachment_id=OuterRef("pk"))
    qs = Attachment.objects.annotate(_has_link=Exists(links)).filter(_has_link=False)
    if minimum_age is not None and minimum_age.total_seconds() > 0:
        qs = qs.filter(created_at__lte=timezone.now() - minimum_age)
    return qs.order_by("created_at")


def cleanup_abandoned_attachments(*, minimum_age=None, dry_run=False):
    """Delete abandoned attachments. Returns the targeted Attachment rows."""
    attachments = list(abandoned_attachments_queryset(minimum_age=minimum_age))
    if not dry_run and attachments:
        delete_unlinked_attachments([attachment.pk for attachment in attachments])
    return attachments


def cleanup_attachments_for_instance(instance, field_name=None):
    """
    Delete attachments linked to this object. Attachments still referenced
    elsewhere are kept.
    """
    from prose.models import RichTextAttachment

    ct = ContentType.objects.get_for_model(instance)
    links = RichTextAttachment.objects.filter(
        content_type=ct,
        object_id=instance.pk,
    )
    if field_name:
        links = links.filter(field_name=field_name)

    attachment_ids = list(links.values_list("attachment_id", flat=True).distinct())
    links.delete()
    delete_unlinked_attachments(attachment_ids)


def _attachment_ids_from_abandoned_sgids(abandoned_sgids, *, exclude_ids=None):
    from prose.models import Attachment

    exclude_ids = exclude_ids or set()
    ids = set()
    for sgid in abandoned_sgids or []:
        obj = resolve_attachable(sgid)
        if isinstance(obj, Attachment) and obj.pk not in exclude_ids:
            ids.add(obj.pk)
    return ids


def sync_attachments_for_instance(
    instance,
    field_name,
    html,
    *,
    previous_html=None,
    abandoned_sgids=None,
):
    from prose.models import RichTextAttachment

    if not instance.pk:
        return

    current_ids = attachment_ids_from_html(html)
    previous_ids = (
        attachment_ids_from_html(previous_html)
        if previous_html is not None
        else set()
    )
    abandoned_from_content = previous_ids - current_ids

    ct = ContentType.objects.get_for_model(instance)
    existing = RichTextAttachment.objects.filter(
        content_type=ct,
        object_id=instance.pk,
        field_name=field_name,
    )
    removed = existing.exclude(attachment_id__in=current_ids)
    removed_attachment_ids = set(
        removed.values_list("attachment_id", flat=True).distinct()
    )
    removed.delete()

    session_abandoned_ids = _attachment_ids_from_abandoned_sgids(
        abandoned_sgids,
        exclude_ids=current_ids,
    )
    delete_unlinked_attachments(
        list(
            abandoned_from_content
            | removed_attachment_ids
            | session_abandoned_ids
        )
    )

    linked = set(
        RichTextAttachment.objects.filter(
            content_type=ct,
            object_id=instance.pk,
            field_name=field_name,
        ).values_list("attachment_id", flat=True)
    )
    for attachment_id in current_ids:
        if attachment_id not in linked:
            RichTextAttachment.objects.create(
                content_type=ct,
                object_id=instance.pk,
                field_name=field_name,
                attachment_id=attachment_id,
            )


def hydrate_editor_attachments(html):
    """
    Prepare HTML for the Lexxy editor. YouTube and custom attachables (mentions,
    etc.) use prose-attachment with a content= attribute so Lexxy's
    CustomActionTextAttachmentNode can render them. File and image attachments
    keep hydrated inner HTML inside the tag wrapper.
    """
    if not html:
        return html

    html = migrate_trix_attachments_in_html(html, inner_context="editor")

    if "data-prose-sgid" in html:

        def replace_editor_figure(match):
            sgid = match.group(1)
            obj = resolve_attachable(sgid)
            if obj is None or not _is_youtube_attachment(obj):
                return match.group(0)
            return _lexxy_editor_youtube_element(obj)

        html = _EDITOR_YOUTUBE_FIGURE.sub(replace_editor_figure, html)

    if PROSE_ATTACHMENT_TAG not in html:
        return _strip_duplicate_youtube_captions(html)

    pattern = re.compile(
        rf"<{PROSE_ATTACHMENT_TAG}\b([^>]*)>(.*?)</{PROSE_ATTACHMENT_TAG}>",
        re.IGNORECASE | re.DOTALL,
    )

    def replace_tag(match):
        attrs_str = match.group(1)
        inner = match.group(2).strip()
        obj = _attachment_from_attrs(attrs_str)
        if obj is None or not hasattr(obj, "render_attachment_html"):
            return match.group(0)
        if _is_youtube_attachment(obj):
            return _lexxy_editor_youtube_element(obj)
        if _is_custom_attachable(obj):
            return _lexxy_editor_custom_attachment_element(obj)
        if inner and ("iframe" in inner or "<img" in inner):
            return match.group(0)
        rendered = obj.render_attachment_html(context="editor")
        return f"<{PROSE_ATTACHMENT_TAG}{attrs_str}>{rendered}</{PROSE_ATTACHMENT_TAG}>"

    def replace_lexxy_export(match):
        attrs_str = match.group(1)
        obj = _attachment_from_attrs(attrs_str)
        if obj is None:
            obj = _youtube_attachment_from_attrs(attrs_str)
        if obj is None:
            return match.group(0)
        if _is_youtube_attachment(obj):
            return _lexxy_editor_youtube_element(obj)
        if _is_custom_attachable(obj):
            return _lexxy_editor_custom_attachment_element(obj)
        return match.group(0)

    html = pattern.sub(replace_tag, html)
    html = _LEXXY_PROSE_ATTACHMENT_EXPORT.sub(replace_lexxy_export, html)
    return _strip_duplicate_youtube_captions(html)


def _is_youtube_embed_figure(html):
    lower = html.lower()
    return (
        "<iframe" in lower
        and "youtube-nocookie.com/embed" in lower
        and ("attachment--youtube" in lower or "attachment--embed" in lower)
    )


def _strip_stored_youtube_embed_figures(html):
    """
    Remove expanded YouTube figures from stored HTML before display render.

    Bleach may hoist block-level embed figures out of prose-attachment tags
    (especially inside <p>), leaving an empty wrapper plus a duplicate iframe.
    Inner iframes from older saves are stripped here too so each attachment
    renders exactly once.
    """
    if not html or PROSE_ATTACHMENT_TAG not in html:
        return html

    def drop_youtube_figure(match):
        if _is_youtube_embed_figure(match.group(0)):
            return ""
        return match.group(0)

    return _YOUTUBE_EMBED_FIGURE.sub(drop_youtube_figure, html)


def render_prose_attachments(html, *, context="display"):
    if not html or PROSE_ATTACHMENT_TAG not in html:
        return html

    html = _strip_stored_youtube_embed_figures(html)

    pattern = re.compile(
        rf"<{PROSE_ATTACHMENT_TAG}\b([^>]*)>(.*?)</{PROSE_ATTACHMENT_TAG}>",
        re.IGNORECASE | re.DOTALL,
    )

    def replace_tag(match):
        attrs_str = match.group(1)
        sgid = _attrs_sgid(attrs_str)
        if not sgid:
            return match.group(0)
        obj = resolve_attachable(sgid)
        if obj is None:
            from prose.template_utils import render_prose_template

            return render_prose_template(
                "prose/attachments/missing.html",
                {"sgid": sgid},
            )
        if hasattr(obj, "render_attachment_html"):
            return obj.render_attachment_html(context=context)
        return match.group(0)

    return pattern.sub(replace_tag, html)
