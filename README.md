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

To control which file types the editor accepts (drag/drop and the upload button) and which uploads the server allows, set `PROSE_PERMITTED_ATTACHMENT_TYPES`. When set, this list **replaces** the built-in defaults (it is not merged). Wildcards such as `image/*` and `application/*` are supported. When unset, django-prose uses a built-in default list (images, videos, PDF, Office documents, and other `application/*` types).

```python
PROSE_PERMITTED_ATTACHMENT_TYPES = [
    "image/*",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]
```

PDF, Word, Excel, and PowerPoint files appear in the editor as a **pill** with a remove control, an editable title, and the original filename plus file type underneath. SVG is always stored as a file link, not inline as `<img>`.

Saving a model with a `RichTextField` normally syncs attachment links and deletes orphans. To purge unlinked `Attachment` rows that accumulated (for example from abandoned uploads), run:

```console
python manage.py cleanup_abandoned_attachments
```

Use `--dry-run` to preview and `--minimum-age-hours 0` to include recently created unlinked attachments. By default only attachments older than 24 hours are removed.

### Embeds

URL-based embeds (YouTube is built in) are stored as `Attachment` rows and referenced in HTML with `<prose-attachment sgid="…">`, the same as uploaded files. In the editor, paste only creates a normal link; embedding is always explicit from the **Link** toolbar popover — enter a URL and click **Embed** when the server recognizes it.

**Endpoints**

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/prose/embed/check/?url=…` | Returns `{"embeddable": true/false}` for the Link popover |
| `POST` | `/prose/embed/` | Creates an embed attachment from `{"url": "…"}` |

YouTube (`youtube.com`, `youtu.be`, Shorts) is included by default. Embeds use a sandboxed `youtube-nocookie.com` player with in-editor captions.

#### Adding your own embed provider

An embed provider teaches Django Prose how to recognize a URL, persist an `Attachment`, and render HTML for the editor and public pages. Implement three methods and register the dotted path in settings.

**Provider interface**

| Method | Purpose |
| --- | --- |
| `match(url) -> bool` | Return `True` when this provider should handle the URL |
| `create_attachment(url) -> Attachment \| None` | Parse the URL, create an `Attachment` row, return it (or `None` on failure) |
| `render_html(attachment) -> str` | Return HTML to insert in the Lexxy editor (usually a `<figure>` with an `iframe` or preview) |

Register providers in order — the first match wins:

```python
PROSE_EMBED_PROVIDERS = [
    "prose.embeds.youtube.YouTubeEmbedProvider",
    "myapp.embeds.VimeoEmbedProvider",
]
```

When `PROSE_EMBED_PROVIDERS` is set, it **replaces** the default list entirely. Include YouTube explicitly if you still want it.

**1. Choose a vendor content type**

Use `vendor_content_type()` so your embed type is namespaced and does not collide with MIME types:

```python
from prose.attachables import vendor_content_type

VIMEO_CONTENT_TYPE = vendor_content_type("vimeo")
# → "application/vnd.prose.vimeo"  (namespace from PROSE_ATTACHMENT_CONTENT_TYPE_NAMESPACE)
```

**2. Create the provider**

Store everything needed to render later in `Attachment.metadata`. Set `filename` to a human title. Embeds do not use `Attachment.file`.

```python
# myapp/embeds/vimeo.py
import re
from urllib.parse import urlparse

from prose.attachables import vendor_content_type
from prose.models import Attachment

VIMEO_CONTENT_TYPE = vendor_content_type("vimeo")
VIMEO_EMBED_PREFIX = "https://player.vimeo.com/video/"


def parse_vimeo_id(url):
    parsed = urlparse(url)
    if parsed.hostname and "vimeo.com" in parsed.hostname:
        match = re.search(r"/(\d+)", parsed.path)
        if match:
            return match.group(1)
    return None


def render_vimeo_figure(attachment, *, context="display"):
    """Shared HTML for editor insertion and public display."""
    video_id = (attachment.metadata or {}).get("video_id")
    if not video_id:
        return ""
    title = attachment.metadata.get("title") or attachment.filename or "Vimeo video"
    canonical = attachment.metadata.get("canonical_url") or attachment.url
    embed_src = f"{VIMEO_EMBED_PREFIX}{video_id}"

    if context in ("editor", "paste"):
        caption = attachment.metadata.get("title") or ""
        return (
            f'<figure class="attachment attachment--embed attachment--preview attachment--vimeo" '
            f'data-prose-sgid="{attachment.attachable_sgid}" '
            f'data-prose-content-type="{attachment.content_type}"'
            f'{" data-prose-caption=\"" + caption + "\"" if caption else ""}>'
            f'<div class="attachment__container">'
            f'<iframe src="{embed_src}" title="{title}" width="560" height="315" '
            f'frameborder="0" allow="autoplay; fullscreen; picture-in-picture" '
            f'allowfullscreen loading="lazy"></iframe>'
            f"</div>"
            f'<figcaption class="attachment__caption">'
            f'<textarea class="django-prose-youtube-caption__input" rows="1" '
            f'placeholder="Add caption…"></textarea>'
            f"</figcaption></figure>"
        )

    return (
        f'<figure class="attachment attachment--embed attachment--vimeo">'
        f'<div class="attachment__container">'
        f'<iframe src="{embed_src}" title="{title}" width="560" height="315" '
        f'frameborder="0" allow="autoplay; fullscreen; picture-in-picture" '
        f'allowfullscreen loading="lazy"></iframe>'
        f"</div>"
        f'<figcaption class="attachment__caption">'
        f'<a href="{canonical}">{title}</a>'
        f"</figcaption></figure>"
    )


class VimeoEmbedProvider:
    def match(self, url):
        return parse_vimeo_id(url) is not None

    def create_attachment(self, url):
        video_id = parse_vimeo_id(url)
        if not video_id:
            return None
        canonical_url = f"https://vimeo.com/{video_id}"
        title = f"Vimeo video {video_id}"  # replace with oEmbed/API lookup if you prefer
        return Attachment.objects.create(
            content_type=VIMEO_CONTENT_TYPE,
            filename=title,
            byte_size=0,
            metadata={
                "provider": "vimeo",
                "video_id": video_id,
                "canonical_url": canonical_url,
                "embed_url": f"{VIMEO_EMBED_PREFIX}{video_id}",
                "title": title,
                "url": canonical_url,
                "previewable": True,
            },
        )

    def render_html(self, attachment):
        return render_vimeo_figure(attachment, context="editor")
```

**3. Teach `Attachment` how to render on the public site**

The embed API calls `render_html()` when a user clicks **Embed**. When published HTML is rendered, `{% prose_attachments %}` calls `Attachment.render_attachment_html()` instead. Hook your content type in `AppConfig.ready()`:

```python
# myapp/apps.py
from django.apps import AppConfig

from prose.models import Attachment

from myapp.embeds.vimeo import VIMEO_CONTENT_TYPE, render_vimeo_figure


class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"

    def ready(self):
        _original = Attachment.render_attachment_html

        def render_attachment_html(self, *, context="display"):
            if self.content_type == VIMEO_CONTENT_TYPE:
                return render_vimeo_figure(self, context=context)
            return _original(self, context=context)

        Attachment.render_attachment_html = render_attachment_html
```

YouTube uses dedicated templates under `prose/templates/prose/attachments/` plus extra save/load canonicalization in django-prose itself. For app-local providers, the `AppConfig` hook above is the supported way to wire up display rendering without forking the package.

**4. Allow iframe sources through the sanitizer**

Bleach only keeps `iframe` tags whose `src` starts with a configured prefix:

```python
PROSE_EMBED_IFRAME_SRC_PREFIXES = [
    "https://www.youtube-nocookie.com/embed/",
    "https://player.vimeo.com/video/",
]
```

**5. (Optional) Gate who can embed**

```python
def prose_upload_allowed(request):
    return request.user.is_staff

PROSE_UPLOAD_PERMISSION = "myapp.permissions.prose_upload_allowed"
```

This applies to uploads and embed endpoints.

#### How embed insertion works

1. User enters a URL in the Link popover → `GET /prose/embed/check/` runs `match()` on each provider.
2. **Embed** appears when a provider matches.
3. `POST /prose/embed/` calls `create_attachment()` then returns JSON including `sgid`, `html`, `editor_html`, and attachment metadata.
4. The Lexxy loader inserts `editor_html` (or builds a `<prose-attachment>` wrapper around `html`). The HTML must include an `<iframe>` for rich insertion.
5. On save, HTML is sanitized and attachment links are synced. Stored embeds are empty `<prose-attachment sgid="…">` wrappers (YouTube has additional caption canonicalization built in).
6. On the public site, `|prose_attachments` resolves each tag via `render_attachment_html(context="display")`.

#### Embed vs file vs attachable

| Mechanism | Use for | Stored as |
| --- | --- | --- |
| **Embed provider** | External URLs (YouTube, Vimeo, maps, …) | `Attachment` row + signed ID |
| **File upload** | User-uploaded files (PDF, images, …) | `Attachment` row + signed ID |
| **`AttachableMixin`** | Your own models (mentions, records, …) | Your model row + signed ID |

Embed providers and file uploads both use `prose.Attachment`. `AttachableMixin` is for referencing arbitrary Django models inline — see below.

#### Reference: YouTube provider

See [`prose/embeds/youtube.py`](prose/embeds/youtube.py) and [`prose/templates/prose/attachments/youtube*.html`](prose/templates/prose/attachments/) for the full production implementation, including oEmbed title lookup, nocookie embed URLs, caption editing, and save-time deduplication of duplicate caption text.

### Extensible attachables (mentions, inline references)

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

Attachables are separate from URL embed providers (above): they reference your own models, not external URLs.

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

These options become attributes on `<lexxy-editor>` (Lexxy’s preset API): `attachments`, `markdown`, `multi_line` → `multi-line`, `rich_text` → `rich-text`, `toolbar` (JSON), `highlight` (JSON), `preset`, `placeholder`, and `single_line` → `single-line`. Use `PROSE_PERMITTED_ATTACHMENT_TYPES` (not `PROSE_LEXXY_EDITOR`) for attachment MIME allowlists.

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
docker compose run --rm test
docker compose run --rm createsuperuser
docker compose up
```

If you are using Visual Studio code, just open this repository in a container using the [`Dev Containers: Open Folder in Container`](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-an-existing-folder-in-a-container).

### Updating Lexxy

Lexxy’s editor JavaScript and CSS are vendored under `prose/static/prose/lexxy/` (served from Django static files — no CDN requests for the editor). The vendored release is recorded in `prose/static/prose/lexxy/VERSION`.

To upgrade to a newer Lexxy release:

1. Check the [Lexxy changelog](https://github.com/basecamp/lexxy/releases) for breaking changes.
2. Set the new version in `package.json` under `devDependencies` → `@37signals/lexxy`.
3. Rebuild the vendored assets:

```console
yarn install
yarn vendor:lexxy
```

4. Review the git diff under `prose/static/prose/lexxy/` and in `yarn.lock`.
5. If Lexxy changed editor APIs, events, or DOM structure, update `prose/static/prose/lexxy-loader.js` (and any related templates or CSS) to match.

**Tests to run after a Lexxy upgrade**

Run these before opening a pull request:

```console
# Python — full django-prose test suite (attachments, embeds, sanitization, widget)
docker compose run --rm test

# JavaScript/CSS — Prettier on prose/static/prose (excludes the minified bundle)
yarn lint
```

Then smoke-test the example app in a browser (hard-refresh or restart `docker compose up` so static files reload):

- Rich text formatting (bold, lists, tables, links)
- File and image uploads (including oversize rejection)
- Office/PDF file pills and captions
- YouTube embed from the Link toolbar
- Read-only editor mode if you rely on `editable: false`

If you only changed vendored static files and `package.json` / `yarn.lock`, `docker compose run --rm test` and `yarn lint` are the required automated checks. Manual browser smoke tests catch Lexxy integration regressions that unit tests do not cover.

---

<p align="center">
  <i>🦄 Built with <a href="https://withlogic.co/">LOGIC</a>. 🦄</i>
</p>
