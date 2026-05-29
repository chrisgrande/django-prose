import json
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from prose.views import upload_attachment


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
        self.assertIn("download_url", data)
        self.assertEqual(data["filename"], "photo.jpg")
        self.assertEqual(data["kind"], "image")
        self.assertTrue(data["previewable"])
        self.assertEqual(data["content_type"], "image/jpeg")

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

    @override_settings(PROSE_ATTACHMENT_ALLOWED_CONTENT_TYPES=["image/png"])
    def test_content_type_allowlist(self):
        f = SimpleUploadedFile("x.jpg", b"data", content_type="image/jpeg")
        request = self.factory.post("/prose/attachment/", {"file": f})
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 400)

    def test_method_not_allowed_for_get(self):
        request = self.factory.get("/prose/attachment/")
        response = self._upload_attachment(request)
        self.assertEqual(response.status_code, 405)
