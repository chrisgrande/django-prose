from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from prose.content import (
    cleanup_attachments_for_instance,
    sync_attachments_for_instance,
)
from prose.fields import RichTextField


def _rich_text_field_names(model):
    return [
        f.name
        for f in model._meta.local_concrete_fields
        if isinstance(f, RichTextField)
    ]


@receiver(pre_save)
def capture_previous_rich_text_html(sender, instance, **kwargs):
    if sender._meta.app_label == "prose" and sender.__name__ in (
        "Attachment",
        "RichTextAttachment",
    ):
        return
    if not instance.pk:
        return
    field_names = _rich_text_field_names(sender)
    if not field_names:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._prose_previous_html = {
        field_name: getattr(previous, field_name) for field_name in field_names
    }


@receiver(post_save)
def sync_rich_text_attachments(sender, instance, **kwargs):
    from prose.middleware import get_abandoned_sgids_for_field

    if sender._meta.app_label == "prose" and sender.__name__ == "Attachment":
        return
    field_names = _rich_text_field_names(sender)
    if not field_names:
        return
    previous_by_field = getattr(instance, "_prose_previous_html", {})
    for field_name in field_names:
        html = getattr(instance, field_name, None)
        sync_attachments_for_instance(
            instance,
            field_name,
            html,
            previous_html=previous_by_field.get(field_name),
            abandoned_sgids=get_abandoned_sgids_for_field(field_name),
        )


@receiver(pre_delete)
def cleanup_rich_text_attachments(sender, instance, **kwargs):
    if sender._meta.app_label == "prose" and sender.__name__ in (
        "Attachment",
        "RichTextAttachment",
    ):
        return
    field_names = _rich_text_field_names(sender)
    if not field_names:
        return
    for field_name in field_names:
        cleanup_attachments_for_instance(instance, field_name=field_name)
