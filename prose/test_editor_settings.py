from django.test import TestCase, override_settings

from prose.editor_settings import (
    build_editor_theme_css,
    build_lexxy_editor_attributes,
    format_lexxy_attribute_value,
    prose_editable_from_options,
)
from prose.widgets import RichTextEditor


class EditorThemeTests(TestCase):
    @override_settings(
        PROSE_EDITOR_THEME={
            "background": "#111111",
            "border": "#333333",
            "icon": "#eeeeee",
        }
    )
    def test_build_editor_theme_css(self):
        css = build_editor_theme_css()
        self.assertIn("--lexxy-color-canvas: #111111", css)
        self.assertIn("--lexxy-color-ink-lighter: #333333", css)
        self.assertIn("lexxy-toolbar", css)
        self.assertIn("color: #eeeeee", css)

    def test_empty_theme_returns_empty_css(self):
        self.assertEqual(build_editor_theme_css({}), "")


class LexxyEditorOptionsTests(TestCase):
    def test_format_boolean_for_lexxy_attributes(self):
        self.assertEqual(format_lexxy_attribute_value(True), "true")
        self.assertEqual(format_lexxy_attribute_value(False), "false")

    @override_settings(
        PROSE_LEXXY_EDITOR={
            "attachments": False,
            "rich_text": True,
            "editable": False,
        }
    )
    def test_build_lexxy_editor_attributes(self):
        attrs = build_lexxy_editor_attributes()
        self.assertEqual(attrs["attachments"], "false")
        self.assertEqual(attrs["rich-text"], "true")
        self.assertEqual(attrs["data-prose-editable"], "false")

    def test_prose_editable_default(self):
        self.assertTrue(prose_editable_from_options({}))


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
