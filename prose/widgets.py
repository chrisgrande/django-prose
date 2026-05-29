import json

from django.conf import settings
from django.forms.widgets import Textarea

from prose.content import hydrate_editor_attachments

LEXXY_VERSION = "0.9.14-beta"
LEXXY_STYLESHEET_URL = (
    f"https://unpkg.com/@37signals/lexxy@{LEXXY_VERSION}/dist/stylesheets/lexxy.css"
)


class RichTextEditor(Textarea):
    template_name = "prose/forms/widgets/editor.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        editor_id = attrs.get("id") or f"id_{name}"
        context["widget"]["initial_script_id"] = f"{editor_id}_initial"
        if value:
            context["widget"]["value"] = hydrate_editor_attachments(value)
        permitted = getattr(settings, "PROSE_PERMITTED_ATTACHMENT_TYPES", None)
        context["widget"]["permitted_attachment_types_json"] = (
            json.dumps(permitted) if permitted else ""
        )
        return context

    class Media:
        css = {
            "all": (
                LEXXY_STYLESHEET_URL,
                "prose/editor.css",
            ),
        }
        js = ("prose/lexxy-loader.js",)
