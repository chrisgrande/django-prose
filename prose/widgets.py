import json

from django.conf import settings
from django.forms.widgets import Textarea

from prose.attachment_types import get_permitted_attachment_types
from prose.content import hydrate_editor_attachments
from prose.editor_settings import (
    build_editor_theme_css,
    build_lexxy_configure_script,
    build_lexxy_editor_attributes,
    build_theme_host_selector,
    get_editor_theme,
    get_lexxy_editor_options,
    prose_editable_from_options,
    theme_host_class_for_id,
)

# Vendored under prose/static/prose/lexxy/ (see prose/static/prose/lexxy/VERSION and `yarn vendor:lexxy`).
LEXXY_STYLESHEETS = (
    "prose/lexxy/stylesheets/lexxy-variables.css",
    "prose/lexxy/stylesheets/lexxy-content.css",
    "prose/lexxy/stylesheets/lexxy-editor.css",
)


class RichTextEditor(Textarea):
    template_name = "prose/forms/widgets/editor.html"

    def __init__(self, attrs=None, theme=None, lexxy=None, prompts=None):
        """
        theme: optional dict merged over PROSE_EDITOR_THEME for this widget.
        lexxy: optional dict merged over PROSE_LEXXY_EDITOR (attachments, rich_text,
               multi_line, markdown, editable, toolbar, …).
        prompts: optional HTML (SafeString) rendered inside <lexxy-editor> as inline
                 <lexxy-prompt> items — use prose.prompts.InlineAttachablePrompt or
                 the {% lexxy_prompt %} template tags.
        """
        super().__init__(attrs)
        self._theme_override = theme
        self._lexxy_override = lexxy
        self._prompts = prompts

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
        context["widget"]["prose_editable"] = prose_editable_from_options(lexxy_options)
        theme_host_class = theme_host_class_for_id(editor_id)
        theme = get_editor_theme(self._theme_override)
        context["widget"]["theme_host_class"] = theme_host_class
        context["widget"]["editor_theme_css"] = build_editor_theme_css(
            theme,
            host_selector=build_theme_host_selector(theme_host_class),
        )
        context["widget"]["lexxy_configure_script"] = build_lexxy_configure_script()
        context["widget"]["max_upload_size_mb"] = getattr(
            settings, "PROSE_ATTACHMENT_ALLOWED_FILE_SIZE", 5
        )
        context["widget"]["prompts"] = self._prompts
        return context

    class Media:
        css = {
            "all": (
                *LEXXY_STYLESHEETS,
                "prose/editor.css",
            ),
        }
        js = ("prose/lexxy-loader.js",)
