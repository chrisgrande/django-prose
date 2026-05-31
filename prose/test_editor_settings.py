from django.test import TestCase, override_settings

from prose.editor_settings import (
    build_editor_theme_css,
    build_lexxy_configure_script,
    build_lexxy_editor_attributes,
    build_theme_host_selector,
    camelize_lexxy_keys,
    format_lexxy_attribute_value,
    prose_editable_from_options,
    resolve_editor_field_lexxy,
    resolve_editor_field_theme,
    theme_css_variable,
    theme_host_class_for_id,
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
        self.assertIn("border-start-start-radius:", css)

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

    def test_theme_host_class_for_id(self):
        self.assertEqual(
            theme_host_class_for_id("id_excerpt"),
            "django-prose-theme-host--id_excerpt",
        )

    def test_build_editor_theme_css_scoped_to_host_class(self):
        host = build_theme_host_selector(theme_host_class_for_id("id_excerpt"))
        css = build_editor_theme_css({"background": "#abcdef"}, host_selector=host)
        self.assertIn(host, css)
        self.assertIn("--lexxy-color-canvas: #abcdef", css)

    def test_resolve_editor_field_theme(self):
        with self.settings(
            PROSE_EDITOR_FIELD_THEMES={"excerpt": {"background": "#111111"}}
        ):
            self.assertEqual(
                resolve_editor_field_theme("excerpt"),
                {"background": "#111111"},
            )
        self.assertIsNone(resolve_editor_field_theme(None))
        self.assertEqual(
            resolve_editor_field_theme({"accent": "#000"}),
            {"accent": "#000"},
        )

    def test_resolve_editor_field_lexxy(self):
        with self.settings(
            PROSE_EDITOR_FIELD_LEXXY={
                "excerpt": {"placeholder": "Summary…", "toolbar": {"upload": "file"}}
            }
        ):
            self.assertEqual(
                resolve_editor_field_lexxy("excerpt"),
                {"placeholder": "Summary…", "toolbar": {"upload": "file"}},
            )
        self.assertIsNone(resolve_editor_field_lexxy(None))
        self.assertEqual(
            resolve_editor_field_lexxy({"markdown": False}),
            {"markdown": False},
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
        self.assertIn(
            "django-prose-theme-host--id_body",
            context["widget"]["theme_host_class"],
        )
        self.assertEqual(context["widget"]["lexxy_attributes"]["markdown"], "false")
        self.assertTrue(context["widget"]["prose_editable"])

    def test_widget_per_field_theme_scoped_separately(self):
        widget_a = RichTextEditor(theme={"background": "#aaaaaa"})
        widget_b = RichTextEditor(theme={"background": "#bbbbbb"})
        ctx_a = widget_a.get_context("excerpt", "", {"id": "id_excerpt"})
        ctx_b = widget_b.get_context("body", "", {"id": "id_body"})
        self.assertIn(
            ".django-prose-editor-container.django-prose-theme-host--id_excerpt",
            ctx_a["widget"]["editor_theme_css"],
        )
        self.assertIn("--lexxy-color-canvas: #aaaaaa", ctx_a["widget"]["editor_theme_css"])
        self.assertIn(
            ".django-prose-editor-container.django-prose-theme-host--id_body",
            ctx_b["widget"]["editor_theme_css"],
        )
        self.assertIn("--lexxy-color-canvas: #bbbbbb", ctx_b["widget"]["editor_theme_css"])

    def test_widget_lexxy_override(self):
        widget = RichTextEditor(lexxy={"editable": False})
        context = widget.get_context("body", "", {"id": "id_body"})
        self.assertFalse(context["widget"]["prose_editable"])
        self.assertEqual(
            context["widget"]["lexxy_attributes"]["data-prose-editable"], "false"
        )
