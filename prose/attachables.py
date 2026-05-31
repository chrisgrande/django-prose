from django.apps import apps
from django.conf import settings
from django.core import signing
from django.utils.functional import cached_property
from django.utils.html import escape

ATTACHABLE_SALT = "prose.attachable"


def attachment_content_type_namespace():
    return getattr(settings, "PROSE_ATTACHMENT_CONTENT_TYPE_NAMESPACE", "prose")


def vendor_content_type(name):
    return f"application/vnd.{attachment_content_type_namespace()}.{name}"


def sign_attachable(obj):
    content_type = getattr(obj, "attachment_content_type", None)
    if content_type is None and hasattr(obj, "get_attachment_content_type"):
        content_type = obj.get_attachment_content_type()
    if content_type is None:
        content_type = getattr(obj, "content_type", "") or ""

    payload = {
        "app": obj._meta.app_label,
        "model": obj._meta.model_name,
        "pk": str(obj.pk),
        "ct": content_type,
    }
    return signing.dumps(payload, salt=ATTACHABLE_SALT, compress=True)


def resolve_attachable(sgid):
    if not sgid:
        return None
    try:
        payload = signing.loads(sgid, salt=ATTACHABLE_SALT)
    except signing.BadSignature:
        return None

    try:
        model = apps.get_model(payload["app"], payload["model"])
    except LookupError:
        return None

    try:
        return model.objects.get(pk=payload["pk"])
    except (model.DoesNotExist, ValueError, TypeError):
        return None


class AttachableRegistry:
    def __init__(self):
        self._by_content_type = {}

    def register(self, content_type, model):
        self._by_content_type[content_type] = model

    def get_model(self, content_type):
        return self._by_content_type.get(content_type)

    def content_types(self):
        return list(self._by_content_type.keys())

    def resolve(self, sgid):
        obj = resolve_attachable(sgid)
        if obj is None:
            return None
        expected_ct = getattr(obj, "attachment_content_type", None)
        if expected_ct:
            registered = self._by_content_type.get(expected_ct)
            if registered and not isinstance(obj, registered):
                return None
        return obj


registry = AttachableRegistry()


class AttachableMixin:
    """
    Mixin for models embedded in rich text via <prose-attachment> (mentions, etc.).
    """

    attachment_name = None

    @classmethod
    def get_attachment_content_type(cls):
        name = cls.attachment_name or cls._meta.model_name
        return vendor_content_type(name)

    @cached_property
    def attachment_content_type(self):
        return self.get_attachment_content_type()

    @property
    def attachable_sgid(self):
        return sign_attachable(self)

    def to_attachment_attributes(self):
        return {
            "sgid": self.attachable_sgid,
            "content-type": self.attachment_content_type,
        }

    def render_attachment_html(self, *, context="display"):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement render_attachment_html()"
        )

    def attachment_search_text(self):
        return str(self)

    @classmethod
    def attachment_menu_template(cls):
        return getattr(cls, "attachment_menu_template_path", None)

    @classmethod
    def attachment_editor_template(cls):
        return getattr(cls, "attachment_editor_template_path", None)

    def render_prompt_menu_html(self):
        template_name = self.attachment_menu_template()
        if template_name:
            from prose.template_utils import render_attachable_template

            return render_attachable_template(
                template_name,
                {self._meta.model_name: self, "attachable": self},
            )
        return escape(str(self))

    def render_prompt_editor_html(self):
        template_name = self.attachment_editor_template()
        if template_name:
            from prose.template_utils import render_attachable_template

            return render_attachable_template(
                template_name,
                {self._meta.model_name: self, "attachable": self},
            )
        return self.render_attachment_html(context="editor")

    @property
    def attachment_editor_html(self):
        """Editor representation for use in prompt item templates."""
        return self.render_attachment_html(context="editor")
