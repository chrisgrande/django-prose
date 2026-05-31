import json
import shutil
import tempfile
from html import escape
from unittest.mock import patch

import django
from django.conf import settings


def _ensure_django():
    if settings.configured:
        return
    media_root = tempfile.mkdtemp(prefix="prose_test_media_")
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "prose",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        MEDIA_ROOT=media_root,
        MEDIA_URL="/media/",
        SECRET_KEY="test-secret-key",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
    )
    django.setup()
    from django.core.management import call_command

    call_command("migrate", verbosity=0, interactive=False)


_ensure_django()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import RequestFactory, TestCase, override_settings

from prose.attachables import (
    AttachableMixin,
    registry,
    resolve_attachable,
    sign_attachable,
    vendor_content_type,
)
from prose.attachment_types import (
    content_type_allowed,
    get_permitted_attachment_types,
    matches_permitted_type,
    mime_from_filename,
    normalize_upload_content_type,
)
from prose.content import (
    _sync_youtube_caption_metadata,
    canonicalize_youtube_for_storage,
    cleanup_attachments_for_instance,
    extract_attachment_sgids,
    hydrate_editor_attachments,
    render_prose_attachments,
    sync_attachments_for_instance,
)
from prose.embeds.youtube import parse_youtube_video_id
from prose.fields import RichTextField, sanitize_rich_text_html
from prose.models import Attachment, Document, RichTextAttachment
from prose.views import (
    embed_check,
    embed_url,
    update_attachment_caption,
    upload_attachment,
)
from prose.widgets import RichTextEditor


class AttachmentTypesTests(TestCase):
    def test_mime_from_filename_office_types(self):
        self.assertEqual(mime_from_filename("report.pdf"), "application/pdf")
        self.assertEqual(
            mime_from_filename("sheet.xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_matches_custom_permitted_types(self):
        custom = ["application/pdf", "image/*"]
        self.assertTrue(matches_permitted_type("application/pdf", "x.pdf", custom))
        self.assertTrue(matches_permitted_type("image/jpeg", "photo.jpg", custom))
        self.assertTrue(matches_permitted_type("image/png", "shot.png", custom))
        self.assertFalse(matches_permitted_type("application/zip", "x.zip", custom))

    def test_default_permitted_types_allow_image_png(self):
        permitted = get_permitted_attachment_types()
        self.assertTrue(matches_permitted_type("image/png", "photo.png", permitted))

    def test_normalize_upload_content_type_for_office_zip(self):
        sheet_mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.assertEqual(
            normalize_upload_content_type("application/zip", "report.xlsx"),
            sheet_mime,
        )
        self.assertTrue(
            content_type_allowed(
                "application/zip",
                "report.xlsx",
                [sheet_mime],
            )
        )

    @override_settings(PROSE_PERMITTED_ATTACHMENT_TYPES=["application/pdf"])
    def test_custom_permitted_types_replace_defaults(self):
        permitted = get_permitted_attachment_types()
        self.assertEqual(permitted, ["application/pdf"])


class WidgetPermittedTypesTests(TestCase):
    def test_widget_exposes_permitted_types_json(self):
        widget = RichTextEditor()
        context = widget.get_context("body", "", {"id": "id_body"})
        permitted = json.loads(context["widget"]["permitted_attachment_types_json"])
        self.assertIn("application/pdf", permitted)
        self.assertIn("image/*", permitted)

    def test_widget_exposes_max_upload_size_mb(self):
        widget = RichTextEditor()
        context = widget.get_context("body", "", {"id": "id_body"})
        self.assertEqual(context["widget"]["max_upload_size_mb"], 5)

    @override_settings(PROSE_ATTACHMENT_ALLOWED_FILE_SIZE=15)
    def test_widget_respects_max_upload_size_setting(self):
        widget = RichTextEditor()
        context = widget.get_context("body", "", {"id": "id_body"})
        self.assertEqual(context["widget"]["max_upload_size_mb"], 15)


class UploadAttachmentViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp(prefix="prose_test_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.factory = RequestFactory()

    def _upload_attachment(self, request):
        with self.settings(MEDIA_ROOT=self._media_root):
            return upload_attachment(request)

    def test_returns_json_metadata_for_image(self):
        f = SimpleUploadedFile("photo.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode())
        self.assertIn("url", data)
        self.assertIn("sgid", data)
        self.assertEqual(data["filename"], "photo.jpg")
        self.assertEqual(data["kind"], "image")
        self.assertTrue(data["previewable"])
        self.assertEqual(Attachment.objects.count(), 1)

    def test_svg_is_file_not_inline_image(self):
        f = SimpleUploadedFile(
            "icon.svg",
            b"<svg xmlns='http://www.w3.org/2000/svg'/>",
            content_type="image/svg+xml",
        )
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode())
        self.assertEqual(data["kind"], "file")
        self.assertFalse(data["previewable"])

    def test_rejects_when_no_file(self):
        request = self.factory.post("/prose/attachment/", {})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 400)

    @override_settings(
        PROSE_PERMITTED_ATTACHMENT_TYPES=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
    )
    def test_upload_xlsx(self):
        f = SimpleUploadedFile(
            "sheet.xlsx",
            b"PK",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode())
        self.assertEqual(data["kind"], "file")
        self.assertEqual(data["content_type"], f.content_type)

    @override_settings(
        PROSE_PERMITTED_ATTACHMENT_TYPES=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
    )
    def test_upload_xlsx_as_application_zip(self):
        f = SimpleUploadedFile(
            "sheet.xlsx",
            b"PK",
            content_type="application/zip",
        )
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode())
        self.assertEqual(data["kind"], "file")
        self.assertIn("spreadsheetml.sheet", data["content_type"])

    @override_settings(PROSE_PERMITTED_ATTACHMENT_TYPES=["image/png"])
    def test_content_type_allowlist(self):
        f = SimpleUploadedFile("x.jpg", b"data", content_type="image/jpeg")
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 400)

    @override_settings(PROSE_PERMITTED_ATTACHMENT_TYPES=["application/pdf"])
    def test_upload_rejects_types_outside_permitted_list(self):
        f = SimpleUploadedFile("photo.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 400)

    def test_rejects_oversized_file(self):
        f = SimpleUploadedFile(
            "big.jpg",
            b"x" * (6 * 1024 * 1024),
            content_type="image/jpeg",
        )
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertIn("MB", data["error"])

    def test_method_not_allowed_for_get(self):
        request = self.factory.get("/prose/attachment/")
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 405)


class EmbedUrlViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("prose.embeds.youtube.fetch_youtube_title", return_value="Never Gonna Give You Up")
    def test_youtube_embed(self, _mock_title):
        request = self.factory.post(
            "/prose/embed/",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}),
            content_type="application/json",
        )
        response = embed_url(request)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode())
        self.assertIn("sgid", data)
        self.assertIn("youtube-nocookie.com/embed/", data["html"])
        self.assertIn("Never Gonna Give You Up", data["html"])
        self.assertEqual(data["kind"], "embed")
        self.assertEqual(data["filename"], "Never Gonna Give You Up")
        self.assertIn("editor_html", data)
        editor_html = data["editor_html"]
        self.assertIn('content="', editor_html)
        self.assertIn("youtube-nocookie.com/embed/", editor_html)
        self.assertRegex(editor_html, r"<prose-attachment\b[^>]*\bcontent=")
        self.assertRegex(editor_html, r"</prose-attachment>\s*$")

    def test_unsupported_url(self):
        request = self.factory.post(
            "/prose/embed/",
            data=json.dumps({"url": "https://example.com/page"}),
            content_type="application/json",
        )
        response = embed_url(request)
        self.assertEqual(response.status_code, 400)

    def test_embed_check_recognizes_youtube(self):
        request = self.factory.get(
            "/prose/embed/check/",
            {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        response = embed_check(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertTrue(data["embeddable"])

    def test_sync_youtube_caption_from_editor_html(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Old Title",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Old Title"},
        )
        inner = "<figcaption><textarea>New &amp; Better</textarea></figcaption>"
        synced = _sync_youtube_caption_metadata(attachment, inner)
        self.assertEqual(synced.metadata["title"], "New & Better")
        self.assertEqual(synced.filename, "New & Better")

    def test_sync_youtube_caption_can_clear_title(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Old Title",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Old Title"},
        )
        synced = _sync_youtube_caption_metadata(
            attachment,
            "<figcaption><textarea></textarea></figcaption>",
        )
        self.assertEqual(synced.metadata["title"], "")
        self.assertEqual(synced.filename, "")

    def test_update_attachment_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Before",
            metadata={"video_id": "x", "title": "Before"},
        )
        sgid = sign_attachable(attachment)
        request = self.factory.post(
            "/prose/attachment/caption/",
            data=json.dumps({"sgid": sgid, "caption": "After"}),
            content_type="application/json",
        )
        response = update_attachment_caption(request)
        self.assertEqual(response.status_code, 200)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "After")
        self.assertEqual(attachment.filename, "After")

    def test_update_file_attachment_display_name(self):
        attachment = Attachment.objects.create(
            content_type="application/pdf",
            filename="report.pdf",
            byte_size=1024,
            metadata={"original_filename": "report.pdf"},
        )
        sgid = sign_attachable(attachment)
        request = self.factory.post(
            "/prose/attachment/caption/",
            data=json.dumps({"sgid": sgid, "caption": "Q1 financials"}),
            content_type="application/json",
        )
        response = update_attachment_caption(request)
        self.assertEqual(response.status_code, 200)
        attachment.refresh_from_db()
        self.assertEqual(attachment.filename, "Q1 financials")
        self.assertEqual(attachment.metadata["original_filename"], "report.pdf")

    def test_update_attachment_caption_can_clear_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Before",
            metadata={"video_id": "x", "title": "Before"},
        )
        request = self.factory.post(
            "/prose/attachment/caption/",
            data=json.dumps({"sgid": sign_attachable(attachment), "caption": ""}),
            content_type="application/json",
        )
        response = update_attachment_caption(request)
        self.assertEqual(response.status_code, 200)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "")
        self.assertEqual(attachment.filename, "")

    def test_embed_check_rejects_unsupported_url(self):
        request = self.factory.get(
            "/prose/embed/check/",
            {"url": "https://example.com/page"},
        )
        response = embed_check(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertFalse(data["embeddable"])


class SigningTests(TestCase):
    def test_sign_and_resolve_attachment(self):
        attachment = Attachment.objects.create(
            content_type="image/png",
            filename="test.png",
            byte_size=100,
        )
        sgid = sign_attachable(attachment)
        resolved = resolve_attachable(sgid)
        self.assertEqual(resolved.pk, attachment.pk)

    def test_tampered_sgid_rejected(self):
        attachment = Attachment.objects.create(
            content_type="image/png",
            filename="test.png",
        )
        sgid = sign_attachable(attachment) + "tampered"
        self.assertIsNone(resolve_attachable(sgid))


class ContentTests(TestCase):
    def test_extract_sgids(self):
        html = (
            '<p>Hi <prose-attachment sgid="abc123" content-type="image/png">'
            "<figure></figure></prose-attachment></p>"
        )
        self.assertEqual(extract_attachment_sgids(html), ["abc123"])

    def test_hydrate_editor_attachments_unwraps_youtube(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="My Video Title",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
                "title": "My Video Title",
            },
        )
        sgid = sign_attachable(attachment)
        html = f'<prose-attachment sgid="{sgid}"></prose-attachment>'
        hydrated = hydrate_editor_attachments(html)
        self.assertIn("prose-attachment", hydrated)
        self.assertIn("content=", hydrated)
        self.assertIn(vendor_content_type("youtube"), hydrated)
        self.assertIn("iframe", hydrated)
        self.assertIn("title=", hydrated)
        self.assertIn("My Video Title", hydrated)
        self.assertIn("figcaption", hydrated)
        self.assertIn("textarea", hydrated)
        self.assertIn("data-prose-caption=", hydrated)
        self.assertNotRegex(hydrated, r"<textarea[^>]*>\s*[^<\s]")
        self.assertIn(sgid, hydrated)
        self.assertNotRegex(hydrated, r'\bcaption="')

    def test_hydrate_file_attachment_uses_pill_editor_template(self):
        attachment = Attachment.objects.create(
            content_type="application/pdf",
            filename="report.pdf",
            metadata={"original_filename": "report.pdf"},
        )
        sgid = sign_attachable(attachment)
        html = f'<prose-attachment sgid="{sgid}"></prose-attachment>'
        hydrated = hydrate_editor_attachments(html)
        self.assertIn("django-prose-file-pill", hydrated)
        self.assertIn("django-prose-file-pill__name", hydrated)
        self.assertIn("report.pdf", hydrated)
        self.assertIn("PDF", hydrated)

    def test_hydrate_strips_duplicate_caption_paragraph_from_lexxy_export(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Only in embed",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Only in embed",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}" caption="Only in embed"></prose-attachment></p>'
            "<p>Only in embed</p>"
        )
        cleaned = hydrate_editor_attachments(html)
        self.assertNotIn("<p>Only in embed</p>", cleaned)
        self.assertNotRegex(cleaned, r'\bcaption="')

    def test_hydrate_strips_duplicate_from_data_prose_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Caption from data attr",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Caption from data attr",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
            "<p>Caption from data attr</p>"
        )
        cleaned = hydrate_editor_attachments(html)
        self.assertIn("data-prose-caption=", cleaned)
        self.assertNotIn("<p>Caption from data attr</p>", cleaned)

    def test_hydrate_strips_same_paragraph_trailing_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Inline dup caption",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Inline dup caption",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment>'
            "Inline dup caption</p>"
        )
        cleaned = hydrate_editor_attachments(html)
        self.assertIn("prose-attachment", cleaned)
        self.assertIn("data-prose-caption=", cleaned)
        self.assertNotIn("Inline dup caption</p>", cleaned)
        self.assertNotRegex(cleaned, r"</prose-attachment>\s*Inline dup caption")

    def test_canonicalize_strips_same_paragraph_trailing_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Saved inline dup",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Saved inline dup",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment>'
            "Saved inline dup</p>"
        )
        stored = sanitize_rich_text_html(html)
        self.assertNotRegex(stored, r"</prose-attachment>\s*Saved inline dup")

    def test_canonicalize_syncs_caption_from_data_prose_caption(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Before",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Before"},
        )
        sgid = sign_attachable(attachment)
        inner = (
            f'<figure class="attachment attachment--youtube" data-prose-sgid="{sgid}" '
            'data-prose-caption="From data attr">'
            "<figcaption><textarea></textarea></figcaption></figure>"
        )
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}">'
            f"{inner}</prose-attachment>"
        )
        canonicalize_youtube_for_storage(raw)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "From data attr")
        self.assertEqual(attachment.filename, "From data attr")

    def test_strip_duplicate_youtube_title_paragraphs(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Anthropic fights back",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Anthropic fights back",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
            "<p>Anthropic fights back</p>"
            "<p><span>Anthropic fights back</span></p>"
            "<p>Other text</p>"
        )
        cleaned = hydrate_editor_attachments(html)
        self.assertIn("prose-attachment", cleaned)
        self.assertIn("iframe", cleaned)
        self.assertNotIn("<p>Anthropic fights back</p>", cleaned)
        self.assertNotIn("<span>Anthropic fights back</span></p>", cleaned)
        self.assertIn("Other text", cleaned)

    def test_strip_preserves_paragraph_wrapping_embed(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video Title",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Video Title",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = (
            f'<p><prose-attachment sgid="{sgid}">'
            '<figure class="attachment--youtube">'
            '<figcaption><span>Video Title</span></figcaption>'
            "</figure></prose-attachment></p>"
            "<p>Video Title</p>"
        )
        cleaned = hydrate_editor_attachments(html)
        self.assertIn("prose-attachment", cleaned)
        self.assertIn("youtube-nocookie.com/embed", cleaned)
        self.assertNotIn("<p>Video Title</p>", cleaned)

    def test_hydrate_lexxy_export_youtube(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        figure = (
            f'<figure class="attachment attachment--embed" '
            f'data-prose-sgid="{sgid}">'
            '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>'
            "</figure>"
        )
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="text/html" '
            f'content="{figure}"></prose-attachment>'
        )
        hydrated = hydrate_editor_attachments(raw)
        self.assertIn(vendor_content_type("youtube"), hydrated)
        self.assertIn("content=", hydrated)
        self.assertIn("iframe", hydrated)

    def test_canonicalize_lexxy_export_youtube(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={"video_id": "dQw4w9WgXcQ"},
        )
        sgid = sign_attachable(attachment)
        figure = (
            f'<figure data-prose-sgid="{sgid}">'
            '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>'
            "</figure>"
        )
        from html import escape

        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="text/html" '
            f'content="{escape(figure, quote=True)}"></prose-attachment>'
        )
        stored = canonicalize_youtube_for_storage(raw)
        self.assertIn(vendor_content_type("youtube"), stored)
        self.assertIn("prose-attachment", stored)
        self.assertNotIn("<iframe", stored)

    def test_canonicalize_youtube_for_storage_wraps_editor_figure(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="My Video Title",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
                "title": "My Video Title",
            },
        )
        sgid = sign_attachable(attachment)
        editor_html = (
            f'<figure class="attachment attachment--embed attachment--youtube" '
            f'data-prose-sgid="{sgid}" '
            f'data-prose-content-type="{vendor_content_type("youtube")}">'
            "<p>placeholder</p></figure>"
        )
        stored = canonicalize_youtube_for_storage(editor_html)
        self.assertIn("prose-attachment", stored)
        self.assertNotIn("iframe", stored)
        self.assertNotIn("data-prose-sgid", stored)

    def test_canonicalize_normalizes_youtube_prose_attachment(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={"video_id": "dQw4w9WgXcQ"},
        )
        sgid = sign_attachable(attachment)
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}" '
            'url="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" filename="Video" '
            'filesize="0" previewable="true">'
            '<figure class="attachment attachment--unknown">broken</figure>'
            "</prose-attachment>"
        )
        stored = canonicalize_youtube_for_storage(raw)
        self.assertIn("prose-attachment", stored)
        self.assertNotIn("attachment--unknown", stored)
        self.assertNotIn("<iframe", stored)

    def test_canonicalize_syncs_youtube_caption_from_inner_attachment(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Before",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Before"},
        )
        sgid = sign_attachable(attachment)
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}">'
            '<figure class="attachment attachment--youtube">'
            "<figcaption><textarea>After</textarea></figcaption>"
            "</figure></prose-attachment>"
        )
        stored = canonicalize_youtube_for_storage(raw)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "After")
        self.assertEqual(attachment.filename, "After")
        self.assertIn("After", stored)

    def test_canonicalize_syncs_caption_from_content_attribute(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Before",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Before"},
        )
        sgid = sign_attachable(attachment)
        inner = (
            f'<figure class="attachment attachment--youtube" data-prose-sgid="{sgid}">'
            "<figcaption><textarea>From export</textarea></figcaption>"
            "</figure>"
        )
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}" '
            f'content="{escape(inner, quote=True)}"></prose-attachment>'
        )
        canonicalize_youtube_for_storage(raw)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "From export")
        self.assertEqual(attachment.filename, "From export")

    def test_canonicalize_can_clear_caption_from_empty_textarea(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Old",
            metadata={"video_id": "dQw4w9WgXcQ", "title": "Old"},
        )
        sgid = sign_attachable(attachment)
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}">'
            '<figure class="attachment attachment--youtube">'
            "<figcaption><textarea></textarea></figcaption>"
            "</figure></prose-attachment>"
        )
        canonicalize_youtube_for_storage(raw)
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata["title"], "")
        self.assertEqual(attachment.filename, "")

    def test_render_prose_attachments(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "canonical_url": "https://youtu.be/x",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            },
        )
        sgid = sign_attachable(attachment)
        html = f'<prose-attachment sgid="{sgid}"></prose-attachment>'
        rendered = render_prose_attachments(html)
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", rendered)
        self.assertEqual(rendered.lower().count("<iframe"), 1)

    def test_render_prose_attachments_youtube_no_duplicate_iframe(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
                "title": "Video",
            },
        )
        sgid = sign_attachable(attachment)
        # Legacy stored HTML: bleach hoists the embed figure beside the wrapper.
        legacy = (
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
            '<figure class="attachment attachment--embed attachment--youtube">'
            '<div class="attachment__container">'
            '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>'
            "</div></figure>"
        )
        rendered = render_prose_attachments(legacy)
        self.assertEqual(rendered.lower().count("<iframe"), 1)

    def test_sanitize_youtube_stores_empty_prose_attachment(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
                "title": "Video",
            },
        )
        sgid = sign_attachable(attachment)
        stored = sanitize_rich_text_html(
            f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        self.assertIn("prose-attachment", stored)
        self.assertNotIn("<iframe", stored)
        rendered = render_prose_attachments(stored)
        self.assertEqual(rendered.lower().count("<iframe"), 1)

    def test_render_prose_attachments_image(self):
        media_root = tempfile.mkdtemp(prefix="prose_test_")
        try:
            with self.settings(MEDIA_ROOT=media_root):
                uploaded = SimpleUploadedFile(
                    "photo.jpg", b"\xff\xd8\xff", content_type="image/jpeg"
                )
                attachment = Attachment.objects.create(
                    file=uploaded,
                    content_type="image/jpeg",
                    filename="photo.jpg",
                    byte_size=3,
                )
                sgid = sign_attachable(attachment)
                html = f'<prose-attachment sgid="{sgid}"></prose-attachment>'
                rendered = render_prose_attachments(html)
            self.assertIn("<img", rendered)
            self.assertIn(attachment.url, rendered)
            self.assertNotIn("prose-attachment", rendered)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_sync_attachments_for_document(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="a.jpg",
        )
        sgid = sign_attachable(attachment)
        doc = Document.objects.create(
            content=f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        sync_attachments_for_instance(doc, "content", doc.content)
        self.assertEqual(
            RichTextAttachment.objects.filter(
                object_id=doc.pk, field_name="content"
            ).count(),
            1,
        )

    def test_deleting_document_deletes_its_attachments(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="a.jpg",
        )
        sgid = sign_attachable(attachment)
        doc = Document.objects.create(
            content=f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        sync_attachments_for_instance(doc, "content", doc.content)
        attachment_id = attachment.pk
        doc.delete()
        self.assertFalse(Attachment.objects.filter(pk=attachment_id).exists())
        self.assertEqual(RichTextAttachment.objects.count(), 0)

    def test_sync_removes_abandoned_attachments_via_field_pre_save(self):
        kept = Attachment.objects.create(
            content_type="image/jpeg",
            filename="kept.jpg",
        )
        abandoned = Attachment.objects.create(
            content_type="image/jpeg",
            filename="removed.jpg",
        )
        kept_sgid = sign_attachable(kept)
        abandoned_sgid = sign_attachable(abandoned)
        doc = Document.objects.create(
            content=(
                f'<p><prose-attachment sgid="{kept_sgid}"></prose-attachment>'
                f'<prose-attachment sgid="{abandoned_sgid}"></prose-attachment></p>'
            )
        )
        self.assertEqual(Attachment.objects.count(), 2)

        doc.content = (
            f'<p><prose-attachment sgid="{kept_sgid}"></prose-attachment></p>'
        )
        doc.save()

        self.assertTrue(Attachment.objects.filter(pk=kept.pk).exists())
        self.assertFalse(Attachment.objects.filter(pk=abandoned.pk).exists())

    def test_sync_deletes_session_abandoned_attachment_never_in_html(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="uploaded.jpg",
        )
        sgid = sign_attachable(attachment)
        doc = Document.objects.create(content="<p></p>")
        sync_attachments_for_instance(
            doc,
            "content",
            doc.content,
            abandoned_sgids=[sgid],
        )
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_sync_keeps_session_abandoned_sgid_still_in_html(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="kept.jpg",
        )
        sgid = sign_attachable(attachment)
        doc = Document.objects.create(
            content=f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        sync_attachments_for_instance(
            doc,
            "content",
            doc.content,
            abandoned_sgids=[sgid],
        )
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_sync_removes_abandoned_lexxy_figure_attachment(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="photo.jpg",
        )
        sgid = sign_attachable(attachment)
        stored_with_figure = (
            f'<figure class="attachment attachment--preview" data-prose-sgid="{sgid}">'
            f'<img src="/media/prose/photo.jpg" alt="photo.jpg"></figure>'
        )
        doc = Document.objects.create(content=f"<p>{stored_with_figure}</p>")
        sync_attachments_for_instance(doc, "content", doc.content)
        self.assertEqual(Attachment.objects.count(), 1)

        doc.content = "<p></p>"
        doc.save()

        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_sync_removes_abandoned_attachments(self):
        kept = Attachment.objects.create(
            content_type="image/jpeg",
            filename="kept.jpg",
        )
        abandoned = Attachment.objects.create(
            content_type="image/jpeg",
            filename="removed.jpg",
        )
        kept_sgid = sign_attachable(kept)
        abandoned_sgid = sign_attachable(abandoned)
        doc = Document.objects.create(
            content=(
                f'<p><prose-attachment sgid="{kept_sgid}"></prose-attachment>'
                f'<prose-attachment sgid="{abandoned_sgid}"></prose-attachment></p>'
            )
        )
        sync_attachments_for_instance(doc, "content", doc.content)
        self.assertEqual(Attachment.objects.count(), 2)

        doc.content = (
            f'<p><prose-attachment sgid="{kept_sgid}"></prose-attachment></p>'
        )
        doc.save()

        self.assertTrue(Attachment.objects.filter(pk=kept.pk).exists())
        self.assertFalse(Attachment.objects.filter(pk=abandoned.pk).exists())
        self.assertEqual(
            RichTextAttachment.objects.filter(object_id=doc.pk).count(),
            1,
        )

    def test_deleting_document_keeps_shared_attachment(self):
        attachment = Attachment.objects.create(
            content_type="image/jpeg",
            filename="shared.jpg",
        )
        sgid = sign_attachable(attachment)
        doc1 = Document.objects.create(
            content=f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        doc2 = Document.objects.create(
            content=f'<p><prose-attachment sgid="{sgid}"></prose-attachment></p>'
        )
        sync_attachments_for_instance(doc1, "content", doc1.content)
        sync_attachments_for_instance(doc2, "content", doc2.content)
        doc1.delete()
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())
        self.assertEqual(
            RichTextAttachment.objects.filter(attachment=attachment).count(),
            1,
        )
        doc2.delete()
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())


class BleachTests(TestCase):
    def test_prose_attachment_survives_sanitization(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={"video_id": "abc12345678"},
        )
        sgid = sign_attachable(attachment)
        raw = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}">'
            '<figure class="attachment attachment--embed">'
            '<iframe src="https://www.youtube-nocookie.com/embed/abc12345678" '
            'title="Video" allowfullscreen></iframe></figure></prose-attachment>'
        )
        cleaned = sanitize_rich_text_html(raw)
        self.assertIn("prose-attachment", cleaned)
        self.assertNotIn("<iframe", cleaned)

    def test_evil_iframe_src_stripped(self):
        raw = '<figure><iframe src="https://evil.example/embed/1"></iframe></figure>'
        cleaned = sanitize_rich_text_html(raw)
        self.assertNotIn("evil.example", cleaned)


class AttachableRegistryTests(TestCase):
    def test_register_and_get_model(self):
        registry.register(vendor_content_type("mention"), Attachment)
        self.assertEqual(
            registry.get_model(vendor_content_type("mention")),
            Attachment,
        )

    def test_attachable_mixin_content_type(self):
        class Person(AttachableMixin):
            attachment_name = "mention"
            pk = 1

            class _meta:
                app_label = "prose"
                model_name = "person"

            def render_attachment_html(self, *, context="display"):
                return '<span class="mention">@jane</span>'

        person = Person()
        self.assertEqual(
            person.attachment_content_type,
            vendor_content_type("mention"),
        )
        self.assertIn("mention", person.render_attachment_html())


class YouTubeParserTests(TestCase):
    def test_parse_watch_url(self):
        self.assertEqual(
            parse_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_parse_short_url(self):
        self.assertEqual(
            parse_youtube_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )


class RichTextEditorWidgetTests(TestCase):
    def test_get_context_hydrates_youtube_for_editor(self):
        attachment = Attachment.objects.create(
            content_type=vendor_content_type("youtube"),
            filename="Video",
            metadata={"video_id": "dQw4w9WgXcQ"},
        )
        sgid = sign_attachable(attachment)
        stored = (
            f'<prose-attachment sgid="{sgid}" content-type="{vendor_content_type("youtube")}">'
            "</prose-attachment>"
        )
        widget = RichTextEditor()
        context = widget.get_context("content", stored, {"id": "id_content"})
        value = context["widget"]["value"]
        self.assertEqual(context["widget"]["initial_script_id"], "id_content_initial")
        self.assertIn("prose-attachment", value)
        self.assertIn("content=", value)
        self.assertIn(vendor_content_type("youtube"), value)
        self.assertIn("iframe", value)


class RichTextFieldLexxySanitizerTests(TestCase):
    def test_preserves_tables_dividers_and_underline(self):
        raw = (
            '<figure class="lexxy-content__table-wrapper">'
            "<table><tbody><tr><td><u>Cell value</u></td></tr></tbody></table>"
            "</figure>"
            "<hr>"
        )
        sanitized = sanitize_rich_text_html(raw)
        self.assertIn("<table>", sanitized)
        self.assertIn("<td><u>Cell value</u></td>", sanitized)
        self.assertIn("<hr>", sanitized)

    def test_preserves_lexxy_color_styles(self):
        raw = (
            '<p><span style="color: rgb(255, 0, 0); background-color: rgb(255, 255, 0)">'
            "Highlighted"
            "</span></p>"
        )
        sanitized = sanitize_rich_text_html(raw)
        self.assertIn(
            'style="color: rgb(255, 0, 0); background-color: rgb(255, 255, 0);"',
            sanitized,
        )


class RichTextFieldTests(TestCase):
    def test_pre_save_sanitizes(self):
        class Article(models.Model):
            body = RichTextField()

            class Meta:
                app_label = "prose"

        article = Article(body="<script>alert(1)</script><p>ok</p>")
        field = Article._meta.get_field("body")
        sanitized = field.pre_save(article, add=True)
        self.assertNotIn("<script>", sanitized)
        self.assertIn("<p>ok</p>", sanitized)
