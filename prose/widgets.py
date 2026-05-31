import json

from django.conf import settings
from django.forms.widgets import Textarea

from prose.attachment_types import get_permitted_attachment_types
from prose.content import hydrate_editor_attachments
from prose.editor_settings import (
    build_editor_theme_css,
    build_lexxy_configure_script,
    build_lexxy_editor_attributes,
    get_editor_theme,
    get_lexxy_editor_options,
    prose_editable_from_options,
)

LEXXY_VERSION = "0.9.14-beta"
LEXXY_STYLESHEETS_BASE = (
    f"https://unpkg.com/@37signals/lexxy@{LEXXY_VERSION}/dist/stylesheets"
)
# Load package sheets directly (lexxy.css only @imports siblings; admin CSS pipelines
# can break relative import URLs). Order matches the package bundle.
LEXXY_STYLESHEETS = (
    f"{LEXXY_STYLESHEETS_BASE}/lexxy-variables.css",
    f"{LEXXY_STYLESHEETS_BASE}/lexxy-content.css",
    f"{LEXXY_STYLESHEETS_BASE}/lexxy-editor.css",
)


class RichTextEditor(Textarea):
    template_name = "prose/forms/widgets/editor.html"

    def __init__(self, attrs=None, theme=None, lexxy=None):
        """
        theme: optional dict merged over PROSE_EDITOR_THEME for this widget.
        lexxy: optional dict merged over PROSE_LEXXY_EDITOR (attachments, rich_text,
               multi_line, markdown, editable, toolbar, …).
        """
        super().__init__(attrs)
        self._theme_override = theme
        self._lexxy_override = lexxy

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        editor_id = attrs.get("id") or f"id_{name}"
        context["widget"]["initial_script_id"] = f"{editor_id}_initial"
        if value:
            context["widget"]["value"] = hydrate_editor_attachments(value)

        lexxy_options = get_lexxy_editor_options(self._lexxy_override)
        context["widget"]["permitted_attachment_types_json"] = json.dumps(
            get_permitted_attachment_types()
        )
        context["widget"]["lexxy_attributes"] = build_lexxy_editor_attributes(
            lexxy_options
        )
        context["widget"]["prose_editable"] = prose_editable_from_options(
            lexxy_options
        )
        theme = get_editor_theme(self._theme_override)
        context["widget"]["editor_theme_css"] = build_editor_theme_css(theme)
        context["widget"]["lexxy_configure_script"] = build_lexxy_configure_script()
        context["widget"]["max_upload_size_mb"] = getattr(
            settings, "PROSE_ATTACHMENT_ALLOWED_FILE_SIZE", 5
        )
        return context

    class Media:
        css = {
            "all": (
                *LEXXY_STYLESHEETS,
                "prose/editor.css",
            ),
        }
        js = ("prose/lexxy-loader.js",)
