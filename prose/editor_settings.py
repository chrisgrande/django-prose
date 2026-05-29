"""Editor chrome (CSS variables) and Lexxy configuration from Django settings."""

import json

from django.conf import settings

# Map PROSE_EDITOR_THEME keys to Lexxy CSS custom properties on the editor host.
THEME_VARIABLE_MAP = {
    "background": "--lexxy-color-canvas",
    "border": "--lexxy-color-ink-lighter",
    "text": "--lexxy-color-text",
    "text_subtle": "--lexxy-color-text-subtle",
    "icon": "--lexxy-color-ink-medium",
    "accent": "--lexxy-color-accent-dark",
    "focus": "--lexxy-focus-ring-color",
    "toolbar_background": "--lexxy-color-ink-lightest",
    "content_background": "--lexxy-color-canvas",
    "selected": "--lexxy-color-selected",
    "link": "--lexxy-color-link",
}

# Also supported (not in LEXXY_OPTION_ATTRIBUTES): single_line → single-line (presence).
# PROSE_LEXXY_EDITOR keys (snake_case) → lexxy-editor HTML attributes (kebab-case).
# Values map to Lexxy preset options (see Lexxy EditorConfiguration); booleans/JSON are
# serialized for attribute parsing in Lexxy.
LEXXY_OPTION_ATTRIBUTES = {
    "attachments": "attachments",
    "markdown": "markdown",
    "multi_line": "multi-line",
    "rich_text": "rich-text",
    "toolbar": "toolbar",
    "highlight": "highlight",
}
# Attachment MIME allowlist is always set on data-permitted-attachment-types via the
# widget (PROSE_PERMITTED_ATTACHMENT_TYPES), not duplicated here.

# Not a Lexxy preset key; handled by django-prose (lexxy-loader.js).
EDITABLE_ATTRIBUTE = "data-prose-editable"


def get_editor_theme(override=None):
    """Theme colors from PROSE_EDITOR_THEME, optionally merged with override dict."""
    theme = dict(getattr(settings, "PROSE_EDITOR_THEME", None) or {})
    if override:
        theme.update(override)
    return {k: v for k, v in theme.items() if v not in (None, "")}


def build_editor_theme_css(theme=None, host_selector=".django-prose-lexxy-host"):
    """Return scoped CSS that overrides Lexxy variables for the editor wrapper."""
    theme = theme if theme is not None else get_editor_theme()
    if not theme:
        return ""

    lines = [f"{host_selector} {{"]
    for key, value in theme.items():
        var_name = THEME_VARIABLE_MAP.get(key)
        if not var_name:
            continue
        lines.append(f"  {var_name}: {value};")
    lines.append("}")

    icon_color = theme.get("icon")
    if icon_color:
        lines.extend(
            [
                "",
                f"{host_selector} lexxy-toolbar {{",
                f"  color: {icon_color};",
                "}",
            ]
        )
    return "\n".join(lines)


def get_lexxy_editor_options(override=None):
    """
    Lexxy editor options from PROSE_LEXXY_EDITOR.

    Keys use snake_case in Django settings; they become kebab-case attributes on
    <lexxy-editor> (attachments, rich-text, multi-line, toolbar, …).
    """
    options = dict(getattr(settings, "PROSE_LEXXY_EDITOR", None) or {})
    if override:
        options.update(override)
    return options


def format_lexxy_attribute_value(value):
    if isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def build_lexxy_editor_attributes(options=None):
    """HTML attributes for <lexxy-editor> from merged Lexxy options."""
    options = options if options is not None else get_lexxy_editor_options()
    attrs = {}
    for key, attr_name in LEXXY_OPTION_ATTRIBUTES.items():
        if key not in options:
            continue
        value = options[key]
        if value is None:
            continue
        attrs[attr_name] = format_lexxy_attribute_value(value)

    if "editable" in options and options["editable"] is False:
        attrs[EDITABLE_ATTRIBUTE] = "false"

    if options.get("single_line"):
        attrs["single-line"] = ""

    return attrs


def prose_editable_from_options(options):
    """Whether the editor should accept input (default True)."""
    if not options:
        return True
    return options.get("editable", True) is not False
