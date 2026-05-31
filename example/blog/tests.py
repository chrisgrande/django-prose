from django.contrib.auth.models import User
from django.test import Client, TestCase

from blog.models import Article, Comment, Contributor
from prose.models import Document


class ArticleModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.su = User.objects.create_superuser(
            "admin", "fake@adminmail.com", "superpass"
        )
        assert User.objects.count() == 1

    def create_article(self, title: str, excerpt: str | None, body: str) -> Article:
        """Create a Article with the given informations."""
        body_document = Document.objects.create(content=body)
        return Article.objects.create(
            title=title, author=self.su, excerpt=excerpt, body=body_document
        )

    def test_article_is_in_db_with_none(self):
        """Article is in database and excerpt field is None."""
        excerpt = None
        article = self.create_article(title="Test", excerpt=excerpt, body="Test body.")
        assert isinstance(article, Article)
        assert article.excerpt == excerpt
        article_in_db = Article.objects.all()[0]
        assert Article.objects.count() == 1
        self.assertQuerysetEqual([article_in_db], [article])

    def test_article_is_in_db_with_empty_string(self):
        """Article is in database and excerpt field is empty string => ''."""
        excerpt = ""
        article = self.create_article(title="Test", excerpt=excerpt, body="Test body")
        assert isinstance(article, Article)
        assert article.excerpt == excerpt
        article_in_db = Article.objects.all()[0]
        assert Article.objects.count() == 1
        self.assertQuerysetEqual([article_in_db], [article])

    def test_article_is_in_db_with_string(self):
        """Article is in database and excerpt field is string => 'string'."""
        excerpt = "string"
        article = self.create_article(title="Test", excerpt=excerpt, body="Test body")
        assert isinstance(article, Article)
        assert article.excerpt == excerpt
        article_in_db = Article.objects.all()[0]
        assert Article.objects.count() == 1
        self.assertQuerysetEqual([article_in_db], [article])

    def test_article_is_in_db_correctly(self):
        """We test whether it is possible to have a string, empty string or None in RichTextField. RichTextField is an excerpt field in the Article model."""
        excerpt_list = ["string", "", None]
        for nr, excerpt in enumerate(excerpt_list, start=1):
            title = f"Test {nr}"
            body = f"Test body {nr}"
            article = self.create_article(title=title, excerpt=excerpt, body=body)
            assert isinstance(article, Article)
            assert article.excerpt == excerpt
            article_in_db = Article.objects.get(title=title)
            assert Article.objects.count() == nr
            self.assertQuerysetEqual([article_in_db], [article])


class MentionCommentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user("writer", "writer@example.com", "pass")
        cls.other = User.objects.create_user("reader", "reader@example.com", "pass")
        cls.contributor = Contributor.objects.create(name="Jane Doe", initials="JD")
        body = Document.objects.create(content="<p>Article body</p>")
        cls.article = Article.objects.create(
            title="Mentions demo",
            author=cls.author,
            excerpt="",
            body=body,
        )

    def test_article_page_includes_mention_prompt_when_logged_in(self):
        client = Client()
        client.login(username="writer", password="pass")
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("lexxy-prompt", content)
        self.assertIn("Jane Doe", content)

    def test_author_sees_article_edit_form(self):
        client = Client()
        client.login(username="writer", password="pass")
        response = client.get(f"/articles/{self.article.pk}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit your post")
        self.assertContains(response, 'name="title"', html=False)
        content = response.content.decode()
        excerpt_editor = content.split('id="id_excerpt"', 1)[1].split("</lexxy-editor>", 1)[0]
        body_editor = content.split('id="id_body"', 1)[1].split("</lexxy-editor>", 1)[0]
        self.assertIn('attachments="false"', excerpt_editor)
        self.assertNotIn("lexxy-prompt", excerpt_editor)
        self.assertNotIn('attachments="false"', body_editor)
        self.assertIn("lexxy-prompt", body_editor)

    def test_author_read_only_article_page_has_no_edit_form(self):
        client = Client()
        client.login(username="writer", password="pass")
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="form_type" value="article"', html=False)
        self.assertContains(response, "Article body")
        self.assertContains(response, "Edit your post")

    def test_non_author_sees_read_only_article(self):
        client = Client()
        client.login(username="reader", password="pass")
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertNotContains(response, "Edit your post")
        self.assertContains(response, "Article body")

    def test_post_comment_requires_login(self):
        response = Client().post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>Hi</p>"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_post_comment_with_mention_renders_on_page(self):
        sgid = self.contributor.attachable_sgid
        content_type = self.contributor.attachment_content_type
        body = (
            f'<p>Thanks <prose-attachment sgid="{sgid}" '
            f'content-type="{content_type}"></prose-attachment>!</p>'
        )
        client = Client()
        client.login(username="writer", password="pass")
        response = client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": body},
        )
        self.assertEqual(response.status_code, 302)
        client.login(username="reader", password="pass")
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertIn('class="mention-pill"', response.content.decode())
        self.assertIn("Jane Doe", response.content.decode())
        self.assertIn("JD", response.content.decode())

    def test_author_can_edit_own_comment(self):
        client = Client()
        client.login(username="writer", password="pass")
        client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>First draft</p>"},
        )
        comment = Comment.objects.get()
        response = client.post(
            f"/articles/{self.article.pk}/",
            data={
                "form_type": "comment_edit",
                "comment_id": comment.pk,
                "body": "<p>Updated comment</p>",
            },
        )
        self.assertEqual(response.status_code, 302)
        comment.refresh_from_db()
        self.assertIn("Updated comment", comment.body)

    def test_author_comment_shows_read_only_by_default(self):
        client = Client()
        client.login(username="writer", password="pass")
        client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>First draft</p>"},
        )
        comment = Comment.objects.get()
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First draft")
        self.assertContains(
            response,
            f"?edit_comment={comment.pk}",
            html=False,
        )
        self.assertNotContains(response, "Save comment")

    def test_author_comment_edit_shows_form_with_query_param(self):
        client = Client()
        client.login(username="writer", password="pass")
        client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>First draft</p>"},
        )
        comment = Comment.objects.get()
        response = client.get(
            f"/articles/{self.article.pk}/?edit_comment={comment.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save comment")
        self.assertContains(response, f'name="comment_id" value="{comment.pk}"', html=False)

    def test_non_author_cannot_see_comment_edit_button(self):
        client = Client()
        client.login(username="writer", password="pass")
        client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>Writer comment</p>"},
        )
        client.login(username="reader", password="pass")
        response = client.get(f"/articles/{self.article.pk}/")
        self.assertContains(response, "Writer comment")
        self.assertNotContains(response, "edit_comment")

    def test_non_author_cannot_edit_comment_via_query_param(self):
        client = Client()
        client.login(username="writer", password="pass")
        client.post(
            f"/articles/{self.article.pk}/",
            data={"form_type": "comment_create", "body": "<p>Writer comment</p>"},
        )
        comment = Comment.objects.get()
        client.login(username="reader", password="pass")
        response = client.get(
            f"/articles/{self.article.pk}/?edit_comment={comment.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Writer comment")
        self.assertNotContains(response, "Save comment")

    def test_author_can_edit_own_article(self):
        client = Client()
        client.login(username="writer", password="pass")
        response = client.post(
            f"/articles/{self.article.pk}/edit/",
            data={
                "title": "Updated title",
                "excerpt": "",
                "body": "<p>Updated body</p>",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.article.body.refresh_from_db()
        self.assertEqual(self.article.title, "Updated title")
        self.assertIn("Updated body", self.article.body.content)
