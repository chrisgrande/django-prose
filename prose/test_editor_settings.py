from django.test import TestCase, override_settings

from prose.editor_settings import (
    build_editor_theme_css,
    build_lexxy_configure_script,
    build_lexxy_editor_attributes,
    camelize_lexxy_keys,
    format_lexxy_attribute_value,
    prose_editable_from_options,
    theme_css_variable,
)
from prose.widgets import RichTextEditor


class EditorThemeTests(TestCase):
    @override_settings(
        PROSE_EDITOR_THEME={
            "background": "#111111",
            "border": "#333333",
            "icon": "#eeeeee",
            "toolbar_background": "#222222",
            "toolbar_icon_size": "1.25em",
        }
    )
    def test_build_editor_theme_css(self):
        css = build_editor_theme_css()
        self.assertIn("--lexxy-color-canvas: #111111", css)
        self.assertIn("--lexxy-color-ink-lighter: #333333", css)
        self.assertIn("--lexxy-toolbar-icon-size: 1.25em", css)
        self.assertIn("lexxy-toolbar", css)
        self.assertIn("color: #eeeeee", css)
        self.assertIn("background: #222222", css)

    def test_empty_theme_returns_empty_css(self):
        self.assertEqual(build_editor_theme_css({}), "")

    def test_lexxy_prefixed_theme_key(self):
        css = build_editor_theme_css({"lexxy_z_popup": "2000"})
        self.assertIn("--lexxy-z-popup: 2000", css)

    def test_raw_css_variable_key(self):
        css = build_editor_theme_css({"--lexxy-shadow": "none"})
        self.assertIn("--lexxy-shadow: none", css)

    def test_theme_css_variable_map(self):
        self.assertEqual(
            theme_css_variable("toolbar_spacing"), "--lexxy-toolbar-spacing"
        )


class LexxyEditorOptionsTests(TestCase):
    def test_format_boolean_for_lexxy_attributes(self):
        self.assertEqual(format_lexxy_attribute_value(True), "true")
        self.assertEqual(format_lexxy_attribute_value(False), "false")

    @override_settings(
        PROSE_LEXXY_EDITOR={
            "attachments": False,
            "rich_text": True,
            "editable": False,
            "preset": "simple",
            "placeholder": "Write here…",
        }
    )
    def test_build_lexxy_editor_attributes(self):
        attrs = build_lexxy_editor_attributes()
        self.assertEqual(attrs["attachments"], "false")
        self.assertEqual(attrs["rich-text"], "true")
        self.assertEqual(attrs["data-prose-editable"], "false")
        self.assertEqual(attrs["preset"], "simple")
        self.assertEqual(attrs["placeholder"], "Write here…")

    def test_prose_editable_default(self):
        self.assertTrue(prose_editable_from_options({}))

    @override_settings(
        PROSE_LEXXY_CONFIGURE={
            "default": {"toolbar": {"upload": "image"}},
            "global": {"authenticated_uploads": True},
        }
    )
    def test_lexxy_configure_script(self):
        script = build_lexxy_configure_script()
        self.assertIn("prose-lexxy-configure", script)
        self.assertIn('"authenticatedUploads": true', script)
        self.assertIn('"upload": "image"', script)

    def test_camelize_lexxy_keys(self):
        self.assertEqual(
            camelize_lexxy_keys({"rich_text": False, "multi_line": True}),
            {"richText": False, "multiLine": True},
        )


class RichTextEditorThemeWidgetTests(TestCase):
    @override_settings(
        PROSE_EDITOR_THEME={"background": "#abcdef"},
        PROSE_LEXXY_EDITOR={"markdown": False},
    )
    def test_widget_context_includes_theme_and_lexxy(self):
        widget = RichTextEditor()
        context = widget.get_context("body", "", {"id": "id_body"})
        self.assertIn("--lexxy-color-canvas: #abcdef", context["widget"]["editor_theme_css"])
        self.assertEqual(context["widget"]["lexxy_attributes"]["markdown"], "false")
        self.assertTrue(context["widget"]["prose_editable"])

    def test_widget_lexxy_override(self):
        widget = RichTextEditor(lexxy={"editable": False})
        context = widget.get_context("body", "", {"id": "id_body"})
        self.assertFalse(context["widget"]["prose_editable"])
        self.assertEqual(
            context["widget"]["lexxy_attributes"]["data-prose-editable"], "false"
        )
