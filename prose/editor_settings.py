"""Editor chrome (CSS variables) and Lexxy configuration from Django settings."""

import json
import re

from django.conf import settings
from django.utils.html import json_script

# Map PROSE_EDITOR_THEME keys (snake_case) to Lexxy CSS custom properties on the host.
# See https://github.com/basecamp/lexxy (dist/stylesheets/lexxy-variables.css).
THEME_VARIABLE_MAP = {
    # Aliases (common names)
    "background": "--lexxy-color-canvas",
    "border": "--lexxy-color-ink-lighter",
    "content_background": "--lexxy-color-canvas",
    "toolbar_background": "--lexxy-color-ink-lightest",
    "icon": "--lexxy-color-ink-medium",
    "text": "--lexxy-color-text",
    "text_subtle": "--lexxy-color-text-subtle",
    "accent": "--lexxy-color-accent-dark",
    "focus": "--lexxy-focus-ring-color",
    "selected": "--lexxy-color-selected",
    "link": "--lexxy-color-link",
    # Ink scale
    "ink": "--lexxy-color-ink",
    "ink_medium": "--lexxy-color-ink-medium",
    "ink_light": "--lexxy-color-ink-light",
    "ink_lighter": "--lexxy-color-ink-lighter",
    "ink_lightest": "--lexxy-color-ink-lightest",
    "ink_inverted": "--lexxy-color-ink-inverted",
    # Accent scale
    "accent_dark": "--lexxy-color-accent-dark",
    "accent_medium": "--lexxy-color-accent-medium",
    "accent_light": "--lexxy-color-accent-light",
    "accent_lightest": "--lexxy-color-accent-lightest",
    # Semantic colors
    "red": "--lexxy-color-red",
    "green": "--lexxy-color-green",
    "blue": "--lexxy-color-blue",
    "purple": "--lexxy-color-purple",
    "canvas": "--lexxy-color-canvas",
    "selected_hover": "--lexxy-color-selected-hover",
    "selected_dark": "--lexxy-color-selected-dark",
    "selected_50": "--lexxy-color-selected-50",
    "code_bg": "--lexxy-color-code-bg",
    # Code syntax token colors
    "code_token_att": "--lexxy-color-code-token-att",
    "code_token_comment": "--lexxy-color-code-token-comment",
    "code_token_function": "--lexxy-color-code-token-function",
    "code_token_operator": "--lexxy-color-code-token-operator",
    "code_token_property": "--lexxy-color-code-token-property",
    "code_token_punctuation": "--lexxy-color-code-token-punctuation",
    "code_token_selector": "--lexxy-color-code-token-selector",
    "code_token_variable": "--lexxy-color-code-token-variable",
    # Text highlights (1–9)
    **{f"highlight_{n}": f"--highlight-{n}" for n in range(1, 10)},
    **{f"highlight_bg_{n}": f"--highlight-bg-{n}" for n in range(1, 10)},
    # Tables
    "table_header_bg": "--lexxy-color-table-header-bg",
    "table_cell_border": "--lexxy-color-table-cell-border",
    "table_cell_selected": "--lexxy-color-table-cell-selected",
    "table_cell_selected_border": "--lexxy-color-table-cell-selected-border",
    "table_cell_selected_bg": "--lexxy-color-table-cell-selected-bg",
    "table_cell_add": "--lexxy-color-table-cell-add",
    "table_cell_toggle": "--lexxy-color-table-cell-toggle",
    "table_cell_remove": "--lexxy-color-table-cell-remove",
    "table_cell_add_size": "--lexxy-table-cell-add-size",
    # Typography & layout
    "font_base": "--lexxy-font-base",
    "font_mono": "--lexxy-font-mono",
    "text_small": "--lexxy-text-small",
    "content_margin": "--lexxy-content-margin",
    "editor_padding": "--lexxy-editor-padding",
    "editor_rows": "--lexxy-editor-rows",
    # Focus ring
    "focus_ring_color": "--lexxy-focus-ring-color",
    "focus_ring_offset": "--lexxy-focus-ring-offset",
    "focus_ring_size": "--lexxy-focus-ring-size",
    "focus_bg_color": "--lexxy-focus-bg-color",
    # Toolbar & chrome (lexxy-editor.css)
    "toolbar_button_size": "--lexxy-toolbar-button-size",
    "toolbar_gap": "--lexxy-toolbar-gap",
    "toolbar_icon_size": "--lexxy-toolbar-icon-size",
    "toolbar_spacing": "--lexxy-toolbar-spacing",
    "attachment_gap": "--lexxy-attachment-gap",
    "attachment_gallery_gap": "--lexxy-attachment-gallery-gap",
    # Prompts
    "prompt_avatar_size": "--lexxy-prompt-avatar-size",
    "prompt_offset_x": "--lexxy-prompt-offset-x",
    "prompt_offset_y": "--lexxy-prompt-offset-y",
    "prompt_padding": "--lexxy-prompt-padding",
    # Misc
    "radius": "--lexxy-radius",
    "shadow": "--lexxy-shadow",
    "z_popup": "--lexxy-z-popup",
}

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
    "preset": "preset",
    "placeholder": "placeholder",
}
# Attachment MIME allowlist: PROSE_PERMITTED_ATTACHMENT_TYPES → data-permitted-attachment-types
# on the widget (editor + upload endpoint both use get_permitted_attachment_types()).

# Not Lexxy preset keys; handled by django-prose.
EDITABLE_ATTRIBUTE = "data-prose-editable"


def theme_css_variable(key):
    """Resolve a PROSE_EDITOR_THEME key to a CSS custom property name."""
    if key in THEME_VARIABLE_MAP:
        return THEME_VARIABLE_MAP[key]
    if key.startswith("--"):
        return key
    if key.startswith("lexxy_"):
        return "--" + key.replace("_", "-")
    return None


def _snake_to_camel(name):
    if "_" not in name:
        return name
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


def camelize_lexxy_keys(value):
    """Recursively convert dict keys from snake_case to camelCase for Lexxy.configure."""
    if isinstance(value, dict):
        return {_snake_to_camel(k): camelize_lexxy_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [camelize_lexxy_keys(item) for item in value]
    return value


def get_editor_theme(override=None):
    """Theme from PROSE_EDITOR_THEME, optionally merged with override dict."""
    theme = dict(getattr(settings, "PROSE_EDITOR_THEME", None) or {})
    if override:
        theme.update(override)
    return {k: v for k, v in theme.items() if v not in (None, "")}


def resolve_editor_field_theme(theme_spec):
    """
    Resolve a per-field theme for RichTextEditor / {% prose_field %}.

    * ``None`` / ``""`` — no field-level override (use global PROSE_EDITOR_THEME).
    * ``dict`` — merged over the global theme for that widget.
    * ``str`` — key into ``PROSE_EDITOR_FIELD_THEMES`` in Django settings.
    """
    if not theme_spec:
        return None
    if isinstance(theme_spec, dict):
        return theme_spec
    if isinstance(theme_spec, str):
        field_themes = getattr(settings, "PROSE_EDITOR_FIELD_THEMES", None) or {}
        return field_themes.get(theme_spec)
    return None


def resolve_editor_field_lexxy(lexxy_spec):
    """
    Resolve per-field Lexxy options for RichTextEditor / {% prose_field %}.

    * ``None`` / ``""`` — no field-level override (use global PROSE_LEXXY_EDITOR).
    * ``dict`` — merged over global Lexxy options for that widget.
    * ``str`` — key into ``PROSE_EDITOR_FIELD_LEXXY`` in Django settings.
    """
    if not lexxy_spec:
        return None
    if isinstance(lexxy_spec, dict):
        return lexxy_spec
    if isinstance(lexxy_spec, str):
        field_lexxy = getattr(settings, "PROSE_EDITOR_FIELD_LEXXY", None) or {}
        return field_lexxy.get(lexxy_spec)
    return None


def theme_host_class_for_id(editor_id):
    """Stable host class so each editor's theme CSS scopes to one instance."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", editor_id or "prose-editor").strip("-")
    return f"django-prose-theme-host--{slug or 'prose-editor'}"


def build_theme_host_selector(theme_host_class):
    return f".django-prose-editor-container.{theme_host_class}"


def build_editor_theme_css(theme=None, host_selector=".django-prose-lexxy-host"):
    """Return scoped CSS that overrides Lexxy variables for the editor wrapper."""
    theme = theme if theme is not None else get_editor_theme()
    if not theme:
        return ""

    css_vars = {}
    icon_color = None
    toolbar_bg = None
    for key, value in theme.items():
        if key == "icon":
            icon_color = value
        if key == "toolbar_background":
            toolbar_bg = value
        var_name = theme_css_variable(key)
        if var_name:
            css_vars[var_name] = value

    lines = [f"{host_selector} {{"]
    for var_name, value in css_vars.items():
        lines.append(f"  {var_name}: {value};")
    lines.append("}")

    toolbar_rules = {}
    if icon_color:
        toolbar_rules["color"] = icon_color
    if toolbar_bg:
        toolbar_rules["background"] = toolbar_bg
    if toolbar_rules:
        lines.append("")
        lines.append(f"{host_selector} lexxy-toolbar {{")
        for prop, val in toolbar_rules.items():
            lines.append(f"  {prop}: {val};")
        if toolbar_bg:
            lines.append(
                "  border-start-start-radius: calc(var(--lexxy-radius) + var(--lexxy-toolbar-gap, 2px));"
            )
            lines.append(
                "  border-start-end-radius: calc(var(--lexxy-radius) + var(--lexxy-toolbar-gap, 2px));"
            )
        lines.append("}")

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


def get_lexxy_configure(override=None):
    """
    Lexxy.configure() payload from PROSE_LEXXY_CONFIGURE.

    Use snake_case keys in settings; they are converted to camelCase for Lexxy.
    Supported top-level keys: ``global``, ``default``, and custom preset names.
    """
    config = dict(getattr(settings, "PROSE_LEXXY_CONFIGURE", None) or {})
    if override:
        config.update(override)
    return config


def build_lexxy_configure_script(override=None):
    """JSON script element for Lexxy.configure() overrides (camelCase values)."""
    config = get_lexxy_configure(override)
    if not config:
        return ""
    return json_script(camelize_lexxy_keys(config), "prose-lexxy-configure")


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
