import bleach
from bleach.css_sanitizer import CSSSanitizer
from django.db import models

from prose.widgets import RichTextEditor

PROSE_ATTACHMENT_TAG = "prose-attachment"

ALLOWED_TAGS = [
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "div",
    "span",
    "a",
    "blockquote",
    "pre",
    "figure",
    "figcaption",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "br",
    "hr",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "picture",
    "source",
    "img",
    "s",
    "del",
    "u",
    "mark",
    "textarea",
    "button",
    PROSE_ATTACHMENT_TAG,
    "iframe",
]

ALLOWED_ATTRIBUTES = {
    "*": [
        "class",
        "style",
        "data-content-type",
        "data-prose-sgid",
        "data-prose-filename",
        "data-prose-content-type",
        "data-prose-caption",
        "value",
        "download",
        "aria-hidden",
        "type",
        "aria-label",
        "title",
        "rows",
        "placeholder",
        "readonly",
    ],
    "a": ["href", "title", "target", "rel"],
    "img": ["alt", "src", "srcset", "width", "height"],
    "source": ["media", "src", "srcset", "type"],
    "video": ["controls", "src"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "iframe": [
        "src",
        "title",
        "allow",
        "allowfullscreen",
        "referrerpolicy",
        "loading",
        "width",
        "height",
        "frameborder",
    ],
    PROSE_ATTACHMENT_TAG: [
        "sgid",
        "content-type",
        "url",
        "href",
        "filename",
        "filesize",
        "previewable",
        "presentation",
        "width",
        "height",
        "caption",
        "alt",
    ],
}

ALLOWED_CSS_PROPERTIES = [
    "color",
    "background-color",
]

_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)


def _embed_iframe_src_ok(src):
    from django.conf import settings

    if not src:
        return False
    prefixes = getattr(
        settings,
        "PROSE_EMBED_IFRAME_SRC_PREFIXES",
        ["https://www.youtube-nocookie.com/embed/"],
    )
    return any(src.startswith(prefix) for prefix in prefixes)


def _bleach_attributes(tag, name, value):
    if tag == "iframe" and name == "src":
        return value if _embed_iframe_src_ok(value) else False
    tag_attrs = ALLOWED_ATTRIBUTES.get(tag, [])
    global_attrs = ALLOWED_ATTRIBUTES.get("*", [])
    if name in tag_attrs or name in global_attrs:
        return value
    return False


def sanitize_rich_text_html(raw_html):
    if not raw_html:
        return raw_html
    from prose.content import (
        canonicalize_legacy_attachments,
        canonicalize_youtube_for_storage,
    )

    canonical = canonicalize_legacy_attachments(raw_html)
    canonical = canonicalize_youtube_for_storage(canonical)
    return bleach.clean(
        canonical,
        tags=ALLOWED_TAGS,
        attributes=_bleach_attributes,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
    )


class RichTextField(models.TextField):
    def formfield(self, **kwargs):
        kwargs["widget"] = RichTextEditor
        return super().formfield(**kwargs)

    def pre_save(self, model_instance, add):
        from prose.content import sync_attachments_for_instance
        from prose.middleware import get_abandoned_sgids_for_field

        raw_html = getattr(model_instance, self.attname)
        if raw_html:
            sanitized = sanitize_rich_text_html(raw_html)
        else:
            sanitized = raw_html or ""

        if model_instance.pk:
            previous_html = None
            try:
                previous = model_instance.__class__.objects.only(self.attname).get(
                    pk=model_instance.pk
                )
                previous_html = getattr(previous, self.attname)
            except model_instance.__class__.DoesNotExist:
                pass
            sync_attachments_for_instance(
                model_instance,
                self.attname,
                sanitized,
                previous_html=previous_html,
                abandoned_sgids=get_abandoned_sgids_for_field(self.attname),
            )

        return sanitized


class DocumentContentField(RichTextField):
    pass
