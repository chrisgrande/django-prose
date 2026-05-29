from django import template
from django.utils.safestring import mark_safe

from prose.attachables import sign_attachable
from prose.content import render_prose_attachments

register = template.Library()


@register.filter(name="prose_attachments")
def prose_attachments_filter(html, context="display"):
    if not html:
        return ""
    return mark_safe(render_prose_attachments(html, context=context))


@register.simple_tag
def attachable_sgid(obj):
    return sign_attachable(obj)
