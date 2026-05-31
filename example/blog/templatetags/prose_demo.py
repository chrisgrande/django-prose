"""Demo template helpers for per-field RichTextEditor customization."""

from django import template
from django.utils.safestring import mark_safe

from prose.editor_settings import resolve_editor_field_lexxy, resolve_editor_field_theme
from prose.widgets import RichTextEditor

register = template.Library()


@register.simple_tag
def prose_field(bound_field, attachments=True, theme=None, lexxy=None):
    """
    Render a bound RichTextEditor field with optional Lexxy and theme overrides.

    Used by the blog edit template to demonstrate per-field customization:

    * ``attachments=False`` — disable uploads, embeds, and @ prompts.
    * ``theme="excerpt"`` — look up ``PROSE_EDITOR_FIELD_THEMES["excerpt"]``.
    * ``lexxy="excerpt"`` — look up ``PROSE_EDITOR_FIELD_LEXXY["excerpt"]``.
    """
    base = bound_field.field.widget
    if not isinstance(base, RichTextEditor):
        return bound_field.as_widget()

    base_lexxy = dict(getattr(base, "_lexxy_override", None) or {})
    theme_override = resolve_editor_field_theme(theme)
    if theme_override is None:
        theme_override = getattr(base, "_theme_override", None)
    lexxy_override = resolve_editor_field_lexxy(lexxy)

    if (
        attachments
        and not base_lexxy
        and theme_override is None
        and lexxy_override is None
    ):
        return bound_field.as_widget()

    lexxy = {**base_lexxy, **(lexxy_override or {}), "attachments": bool(attachments)}
    widget = RichTextEditor(
        attrs=base.attrs,
        theme=theme_override,
        lexxy=lexxy,
        prompts=getattr(base, "_prompts", None) if attachments else None,
    )
    return mark_safe(bound_field.as_widget(widget=widget))
