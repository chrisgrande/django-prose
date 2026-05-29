# Django Prose

![PyPI - Downloads](https://img.shields.io/pypi/dw/django-prose?color=purple) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-prose)

Django Prose provides your Django applications with wonderful rich-text editing capabilities.

## Requirements

- Python 3.8 or later
- Django 3.2 or later
- Bleach 4.0 or later

## Getting started

To get started with Django Prose, all you need to do is follow **just four steps**.

1. **Install `django-prose`**
    
    We use and suggest using Poetry, although Pipenv and plain pip will work seamlessly as well
    
    ```console
    poetry add django-prose
    ```

2. **Add to `INSTALLED_APPS`**
    
    Add `prose` in your Django project's installed apps (example: [`example/example/settings.py`](https://github.com/withlogicco/django-prose/blob/9e24cc794eae6db48818dd15a483d106d6a99da0/example/example/settings.py#L46)):
    
    ```python
    INSTALLED_APPS = [
        # Django stock apps (e.g. 'django.contrib.admin')
    
        'prose',
    
        # your application's apps
    ]
    ```

3. **Run migrations**

    This is required so you can use Django Prose's built-in Document model:
  
    ```console
    python manage.py migrate prose
    ```

4. **Include URLs**

    You need to edit the main `urls.py` file of your Django project and include `prose.urls`:
    
    ```python
    urlpatterns = [
        path('admin/', admin.site.urls),
        # other urls ...
        path("prose/", include("prose.urls")),
    ]
    ```

Now, you are ready to go 🚀.

## Usage

There are different ways to use Django prose according to your needs. We will examine all of them here.

### Rendering rich-text in templates

Rich text content essentially is HTML. For this reason it needs to be manually marked as [`safe`](https://docs.djangoproject.com/en/4.2/ref/templates/builtins/#safe), when rendered in Django templates. Example:

```django
{{ document.content | safe}}
```

### Small rich-text content

You might want to add rich-text content in a model that is just a few characters (e.g. 140), like an excerpt from an article. In that case we suggest using the `RichTextField`. Example:

```py
from django.db import models
from prose.fields import RichTextField

class Article(models.Model):
    excerpt = RichTextField()
```

As mentioned above, you need to mark the article excerpt as `safe`, in order to render it:

```django
<div class="article-excerpt">{{ article.excerpt | safe}}</div>
```

### Large rich-text content

In case you want to store large rich-text content, like the body of an article, which can span to quite a few thousand characters, we suggest you use the `AbstractDocument` model. This will save large rich-text content in a separate database table, which is better for performance. Example:

```py
from django.db import models
from prose.fields import RichTextField
from prose.models import AbstractDocument

class ArticleContent(AbstractDocument):
    pass

class Article(models.Model):
    excerpt = RichTextField()
    body = models.OneToOneField(ArticleContent, on_delete=models.CASCADE)
```

Similarly here as well, you need to mark the article's body as `safe`, in order to render it:

```django
<div class="article-body">{{ article.body.content | safe}}</div>
```

### Forms with rich-text editing

You can create forms for your Django Prose models, to provide rich-text editing functionality. In that case, you will also need to render `form.media`, to load the Lexxy-based editor and its stylesheets.

```django
<form  method="POST" >
  {% csrf_token %}
  
  {{ form.as_p }}
  {{ form.media }}
  
  <button type="submit">Submit</button>
</form>
```

The same is true also, if you are rendering the forms field manually.

### Attachments

Django Prose can also handle uploading attachments with drag and drop. To set this up, first you need to:

- [x] Set up the `MEDIA_ROOT` and `MEDIA_URL` of your Django project (example in [`example/example/settings.py`](https://github.com/withlogicco/django-prose/blob/9e24cc794eae6db48818dd15a483d106d6a99da0/example/example/settings.py#L130-L131)))
- [x] Include the Django Prose URLs (example in [`example/example/urls.py`](https://github.com/withlogicco/django-prose/blob/9e24cc794eae6db48818dd15a483d106d6a99da0/example/example/urls.py#L13-L14))
- [x] Run migrations so the `Attachment` model is created (`python manage.py migrate prose`)
- [x] (Optional) Set up a different Django storage to store your files (e.g. S3)

- Attachments are stored in the database (`prose.Attachment`) and referenced in HTML with `<prose-attachment sgid="...">` tags (compatible with [Lexxy](https://basecamp.github.io/lexxy/) and [Action Text](https://guides.rubyonrails.org/action_text_overview.html)-style signed IDs).
- Files use a path structure of `prose/YEAR/MONTH/DATE/UUID.EXT` in your storage backend.
- By default, only files 5MB or less are allowed.
- The upload endpoint returns JSON with `sgid`, `url`, `download_url`, `filename`, `content_type`, `size`, `kind` (`image`, `file`, or `embed`), and `previewable`.
- The editor uses Lexxy’s default **file** upload toolbar button; uploads are handled by Django, not ActiveStorage.
- **CSRF:** the page must expose a CSRF token (e.g. `{% csrf_token %}` in the form, or the `csrftoken` cookie readable by JS). The loader sends `csrfmiddlewaretoken` and the `X-CSRFToken` header.

**Displaying content:** resolve attachment tags before marking HTML safe:

```django
{% load prose_attachments %}
{{ article.body|prose_attachments|safe }}
```

Allowed file size can be overridden by setting `PROSE_ATTACHMENT_ALLOWED_FILE_SIZE` in your Django project's settings file.

```python
# File size in megabytes
PROSE_ATTACHMENT_ALLOWED_FILE_SIZE = 15
```

To restrict uploads to specific MIME types, set `PROSE_ATTACHMENT_ALLOWED_CONTENT_TYPES` to a list of allowed `Content-Type` strings (lowercase matching). If unset, MIME types are not restricted (only file size and safe image handling: SVG is stored as a file link, not inline as `<img>`).

```python
PROSE_ATTACHMENT_ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]
```

PDF, Word, Excel, and PowerPoint files appear in the editor as a **pill** with a remove control, an editable title, and the original filename plus file type underneath.

To control what the editor accepts (drag/drop and the upload button), set `PROSE_PERMITTED_ATTACHMENT_TYPES`. When set, this list **replaces** the built-in defaults (it is not merged). Wildcards such as `image/*` and `application/*` are supported.

```python
PROSE_PERMITTED_ATTACHMENT_TYPES = [
    "image/*",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]
```

### Embeds (YouTube)

Supported URLs (YouTube: `youtube.com`, `youtu.be`, Shorts) can be embedded from the **Link** toolbar popover: enter the URL and click **Embed** when the server recognizes it (`GET /prose/embed/check/`). Pasting a URL only creates a normal link; embedding is never automatic on paste. Embeds are stored as `<prose-attachment>` with a sandboxed `youtube-nocookie.com` player.

Add custom embed providers by implementing a class with `match(url)`, `create_attachment(url)`, and `render_html(attachment)`, then register it in settings:

```python
PROSE_EMBED_PROVIDERS = [
    "prose.embeds.youtube.YouTubeEmbedProvider",
    "myapp.embeds.VimeoEmbedProvider",
]
```

### Extensible attachables (mentions, custom embeds)

Use `AttachableMixin` on your own models and register them so rich text can reference them by signed ID (like Action Text attachables):

```python
from django.db import models
from prose.attachables import AttachableMixin, registry

class Person(AttachableMixin, models.Model):
    attachment_name = "mention"
    name = models.CharField(max_length=100)

    def render_attachment_html(self, *, context="display"):
        return f'<em class="mention">{self.name}</em>'

# myapp/apps.py
class MyAppConfig(AppConfig):
    def ready(self):
        registry.register(Person.get_attachment_content_type(), Person)
```

In your form template, add Lexxy prompts with `{% load prose_attachments %}` and `{% attachable_sgid person %}` on each `lexxy-prompt-item` (see [Lexxy inline attachments](https://basecamp.github.io/lexxy/prompts/inline-attachments.html)).

Optional settings:

- `PROSE_PERMITTED_ATTACHMENT_TYPES` — MIME patterns allowed in the editor (drag/drop and upload). Replaces defaults when set; supports wildcards (`image/*`, `application/*`).
- `PROSE_EMBED_IFRAME_SRC_PREFIXES` — allowed `iframe` `src` prefixes when sanitizing (default: YouTube nocookie embeds).
- `PROSE_UPLOAD_PERMISSION` — dotted path to a callable `(request) -> bool` for upload/embed authorization.

#### Editor appearance (`PROSE_EDITOR_THEME`)

Override Lexxy CSS variables for the editor chrome (canvas/background, toolbar, icons, text, tables, highlights, and more). Values are scoped to the editor host and map to [Lexxy theme variables](https://github.com/basecamp/lexxy).

```python
PROSE_EDITOR_THEME = {
    "background": "#1e1e1e",
    "border": "#3c3c3c",
    "toolbar_background": "#2a2a2a",
    "icon": "#e0e0e0",
    "toolbar_icon_size": "1.2em",
    "text": "#f5f5f5",
    "accent": "#6ea8fe",
}
```

Common keys: `background` / `canvas`, `border`, `toolbar_background`, `icon` (toolbar icon color), `toolbar_icon_size`, `toolbar_button_size`, `toolbar_gap`, `toolbar_spacing`, `text`, `text_subtle`, `accent`, `focus`, `selected`, `link`, ink/accent scales, table colors, highlight colors (`highlight_1` … `highlight_bg_9`), typography (`font_base`, `font_mono`, `radius`, `shadow`, …).

Any Lexxy variable can also be set with a `lexxy_*` key (e.g. `lexxy_z_popup`) or a raw `--lexxy-*` key.

Per-widget overrides: `RichTextEditor(theme={"background": "#fff"})`.

#### Lexxy behaviour (`PROSE_LEXXY_EDITOR`)

These options become attributes on `<lexxy-editor>` (Lexxy’s preset API): `attachments`, `markdown`, `multi_line` → `multi-line`, `rich_text` → `rich-text`, `toolbar` (JSON), `highlight` (JSON), `preset`, `placeholder`, `permitted_attachment_types`, and `single_line` → `single-line`.

```python
PROSE_LEXXY_EDITOR = {
    "attachments": True,
    "markdown": True,
    "multi_line": True,
    "rich_text": True,
    "editable": True,  # False = read-only (toolbar hidden, Lexical not editable)
    "toolbar": {"upload": "file"},
    "placeholder": "Write something…",
}
```

Per-widget overrides: `RichTextEditor(lexxy={"editable": False})`.

#### Lexxy global / presets (`PROSE_LEXXY_CONFIGURE`)

Advanced options passed to `Lexxy.configure()` (camelCase in JS; use snake_case in settings). Supports `global`, `default`, and custom preset names. django-prose always keeps `prose-attachment` tags and its upload extension; do not override `attachment_tag_name`, `attachment_content_type_namespace`, or `extensions`.

```python
PROSE_LEXXY_CONFIGURE = {
    "global": {"authenticated_uploads": True},
    "default": {"toolbar": {"upload": "both"}},
}
```

### Full example

You can find a full example of a blog, built with Django Prose in the [`example`](./example/) directory.

## 🔒 A note on security

As you can see in the examples above, what Django Prose does is provide you with a user friendly editor (powered by [Lexxy](https://github.com/basecamp/lexxy)) for your rich text content and then store it as HTML in your database. Since you will mark this HTML as safe in order to use it in your templates, it needs to be **sanitised**, before it gets stored in the database.

For this reason Django Prose is using [Bleach](https://bleach.readthedocs.io/en/latest/) to only allow the following tags and attributes:

- **Allowed tags**: `p`, `ul`, `ol`, `li`, `strong`, `em`, `div`, `span`, `a`, `blockquote`, `pre`, `figure`, `figcaption`, `br`, `code`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `picture`, `source`, `img`, `prose-attachment`, `iframe`, `del`
- **Allowed attributes**: `alt`, `class`, `src`, `srcset`, `href`, `media`, `data-content-type`, `sgid`, `content-type`, `filename`, `filesize`, `previewable`, `presentation`, and sandboxed `iframe` attributes (`src` is limited to configured embed prefixes)

## Screenshots

### Django Prose Documents in Django Admin

![Django Prose Document in Django Admin](./docs/django-admin-prose-document.png)

## Video tutorial

If you are more of a video person, you can watch our video showcasing how to **Create a blog using Django Prose** on YouTube

[![Watch the video](https://img.youtube.com/vi/uICZjUpAbhQ/hqdefault.jpg)](https://youtu.be/uICZjUpAbhQ)

## Real world use cases
- **Remote Work Café**: Used to edit location pagess, like [Amsterdam | Remote Work Café](https://remotework.cafe/locations/amsterdam/)
- In production by multiple clients of [LOGIC](https://withlogic.co), from small companies to the public sector.

If you are using Django Prose in your application too, feel free to open a [Pull Request](https://github.com/withlogicco/django-prose/pulls) to include it here. We would love to have it.

## Development for Django Prose

If you plan to contribute code to Django Prose, this section is for you. All development tooling for Django Prose has been set up with Docker and Development Containers.

To get started run these commands in the provided order:

```console
docker compose run --rm migrate
docker compose run --rm createsuperuser
docker compose up
```

If you are using Visual Studio code, just open this repository in a container using the [`Dev Containers: Open Folder in Container`](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-an-existing-folder-in-a-container).

---

<p align="center">
  <i>🦄 Built with <a href="https://withlogic.co/">LOGIC</a>. 🦄</i>
</p>
