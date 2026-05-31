"""Demo template helpers for per-field RichTextEditor customization."""

from django import template
from django.utils.safestring import mark_safe

from prose.widgets import RichTextEditor

register = template.Library()


@register.simple_tag
def prose_field(bound_field, attachments=True):
    """
    Render a bound RichTextEditor field, optionally overriding Lexxy options.

    Used by the blog edit template to show how one field can disable uploads
    while others keep the full editor (see article_edit.html).
    """
    base = bound_field.field.widget
    if not isinstance(base, RichTextEditor):
        return bound_field.as_widget()

    base_lexxy = dict(getattr(base, "_lexxy_override", None) or {})
    if attachments and not base_lexxy:
        return bound_field.as_widget()

    lexxy = {**base_lexxy, "attachments": bool(attachments)}
    widget = RichTextEditor(
        attrs=base.attrs,
        theme=getattr(base, "_theme_override", None),
        lexxy=lexxy,
        prompts=getattr(base, "_prompts", None) if attachments else None,
    )
    return mark_safe(bound_field.as_widget(widget=widget))
