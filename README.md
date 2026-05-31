# Django Prose

![PyPI - Downloads](https://img.shields.io/pypi/dw/django-prose?color=purple) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-prose)

Django Prose provides your Django applications with wonderful rich-text editing capabilities.

## Requirements

- Python 3.8 or later
- Django 3.2 or later
- Bleach 4.0 or later
- tinycss2 1.1 or later (installed automatically with django-prose; used for limited inline text colors in the sanitizer)

## Getting started

To get started with Django Prose, follow these steps in your Django project.

1. **Install `django-prose`**
    
    We use and suggest using Poetry, although Pipenv and plain pip will work seamlessly as well. The package vendors the [Lexxy](https://github.com/basecamp/lexxy) editor (no CDN scripts required at runtime).
    
    ```console
    poetry add django-prose
    ```

2. **Add to `INSTALLED_APPS`**
    
    Add `prose` in your Django project's installed apps (example: [`example/example/settings.py`](example/example/settings.py)):
    
    ```python
    INSTALLED_APPS = [
        # Django stock apps (e.g. 'django.contrib.admin')
        "django.contrib.contenttypes",  # required for attachment linking
    
        "prose",
    
        # your application's apps
    ]
    ```

3. **Run migrations**

    Creates the `Document`, `Attachment`, and `RichTextAttachment` models:
  
    ```console
    python manage.py migrate prose
    ```

4. **Include URLs**

    Required for file uploads, embeds, and caption updates. Edit your project's main `urls.py` (example: [`example/example/urls.py`](example/example/urls.py)):
    
    ```python
    urlpatterns = [
        path("admin/", admin.site.urls),
        # other urls ...
        path("prose/", include("prose.urls")),
    ]
    ```

5. **Add middleware**

    Recommended whenever you use the rich-text editor with attachments. It lets the editor report uploads removed before save so orphaned `Attachment` rows can be cleaned up (example: [`example/example/settings.py`](example/example/settings.py)):

    ```python
    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "prose.middleware.ProseEditorMiddleware",
        "django.middleware.common.CommonMiddleware",
        # ...
    ]
    ```

6. **Collect static files (production)**

    Lexxy's JavaScript and CSS ship inside the package under `prose/static/`. Run collectstatic before deploying:

    ```console
    python manage.py collectstatic
    ```

For **file uploads and embeds**, you also need `MEDIA_ROOT` and `MEDIA_URL` configured, CSRF available on editor forms (`{% csrf_token %}`), and `{{ form.media }}` on forms that use `RichTextField` — see [Attachments](#attachments) below.

For **public pages**, render stored HTML with the `prose_attachments` template filter so `<prose-attachment>` tags and embeds resolve correctly — see [Rendering rich-text in templates](#rendering-rich-text-in-templates).

Now, you are ready to go 🚀.

## Usage

There are different ways to use Django prose according to your needs. We will examine all of them here.

### Rendering rich-text in templates

Rich text content is stored as HTML. Mark it [`safe`](https://docs.djangoproject.com/en/4.2/ref/templates/builtins/#safe) in templates.

If the content includes **uploads or embeds** (anything stored as `<prose-attachment>` tags), load the filter and resolve attachments before marking safe:

```django
{% load prose_attachments %}
{{ document.content|prose_attachments|safe }}
```

Plain formatting-only HTML (no attachments) can use `|safe` alone. The filter leaves that markup unchanged when no attachment tags are present.

```django
{{ document.content|safe }}
```

### Small rich-text content

You might want to add rich-text content in a model that is just a few characters (e.g. 140), like an excerpt from an article. In that case we suggest using the `RichTextField`. Example:

```py
from django.db import models
from prose.fields import RichTextField

class Article(models.Model):
    excerpt = RichTextField()
```

Mark the excerpt `safe` to render it (use `|prose_attachments|safe` if the field can contain uploads):

```django
<div class="article-excerpt">{{ article.excerpt|safe }}</div>
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

For article bodies with attachments or embeds, use `prose_attachments`:

```django
{% load prose_attachments %}
<div class="article-body">{{ article.body.content|prose_attachments|safe }}</div>
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

Django Prose handles file uploads (drag and drop or toolbar) and URL embeds through the Lexxy editor. In addition to the [getting started](#getting-started) steps above, confirm:

- [x] `MEDIA_ROOT` and `MEDIA_URL` are configured (example: [`example/example/settings.py`](example/example/settings.py))
- [x] `path("prose/", include("prose.urls"))` is in your root URLconf
- [x] `python manage.py migrate prose` has been run
- [x] `prose.middleware.ProseEditorMiddleware` is in `MIDDLEWARE`
- [x] Editor forms include `{% csrf_token %}` and `{{ form.media }}`
- [x] Public templates use `|prose_attachments|safe` (see [Rendering rich-text in templates](#rendering-rich-text-in-templates))
- [x] (Production) `python manage.py collectstatic` has been run
- [x] (Optional) A custom storage backend for files (e.g. S3)

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

Use `AttachableMixin` on your own models and register them so rich text can reference them by signed ID (like Action Text attachables).

**Working reference:** the [`example/`](example/) blog app implements `@` mentions end to end. Start with these files:

| Step | Demo file | Purpose |
| --- | --- | --- |
| Model | [`example/blog/models.py`](example/blog/models.py) | `Contributor` with `AttachableMixin`, `render_attachment_html()`, `attachment_search_text()` |
| Registry | [`example/blog/apps.py`](example/blog/apps.py) | `registry.register()` in `AppConfig.ready()` |
| Prompt builder | [`example/blog/prompts.py`](example/blog/prompts.py) | `InlineAttachablePrompt` wired to menu/editor templates |
| Form widget | [`example/blog/forms.py`](example/blog/forms.py) | `RichTextEditor(prompts=…)` on comment/article body fields |
| Prompt partials | [`example/blog/templates/blog/prompts/`](example/blog/templates/blog/prompts/) | Shared `mention_chip.html` plus menu, editor, and display variants |
| Public display | [`example/blog/templates/blog/article.html`](example/blog/templates/blog/article.html) | `\|prose_attachments\|safe` on stored HTML |
| Editor UX (optional) | [`example/blog/static/blog/mentions.css`](example/blog/static/blog/mentions.css), [`mentions.js`](example/blog/static/blog/mentions.js) | Pill styling, inline flow, delete-on-select behaviour |

The editor must have `attachments` enabled (default). If you set `PROSE_PERMITTED_ATTACHMENT_TYPES`, registered attachable content types are appended automatically so `@` prompts keep working.

#### 1. Model and registry

Define a mentionable model and register its vendor content type when Django starts:

```python
# example/blog/models.py (abbreviated)
from prose.attachables import AttachableMixin
from prose.template_utils import render_attachable_template

class Contributor(AttachableMixin, models.Model):
    attachment_name = "mention"  # → application/vnd.prose.mention
    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, blank=True)

    def attachment_search_text(self):
        return f"{self.name} {self.initials}".strip()

    def render_attachment_html(self, *, context="display"):
        template = (
            "blog/prompts/mention_editor.html"
            if context == "editor"
            else "blog/prompts/mention_display.html"
        )
        return render_attachable_template(
            template,
            {"contributor": self, "attachable": self},
        )
```

```python
# example/blog/apps.py
from prose.attachables import registry

class BlogConfig(AppConfig):
    def ready(self):
        from blog.models import Contributor

        registry.register(Contributor.get_attachment_content_type(), Contributor)
```

`attachment_name` sets the vendor MIME type (`application/vnd.prose.<name>`). Implement `render_attachment_html()` for both `"editor"` and `"display"` contexts — they can share markup or use separate templates as the demo does.

#### 2. Inline `@` prompts on the widget

Lexxy loads prompt items inside `<lexxy-editor>`. See [Lexxy inline attachments](https://basecamp.github.io/lexxy/prompts/inline-attachments.html).

**Option 1 — Python helper (used in the demo)**

[`example/blog/prompts.py`](example/blog/prompts.py) builds prompt markup once; [`example/blog/forms.py`](example/blog/forms.py) passes it to the widget:

```python
from prose.prompts import InlineAttachablePrompt
from prose.widgets import RichTextEditor

def mention_prompts():
    return InlineAttachablePrompt(
        trigger="@",
        name="mention",
        queryset=Contributor.objects.order_by("name"),
        menu_template="blog/prompts/mention_menu.html",
        editor_template="blog/prompts/mention_editor.html",
    ).render()

class CommentForm(forms.ModelForm):
    body = forms.CharField(widget=RichTextEditor(prompts=mention_prompts()))
```

**Option 2 — Template tags inside a custom editor template**

Override `RichTextEditor.template_name` or render prompts in your form template and pass HTML to `RichTextEditor(prompts=...)`. Tags:

```django
{% load prose_attachments %}
{% lexxy_prompt trigger="@" name="mention" %}
  {% for contributor in contributors %}
    {% lexxy_prompt_item attachable=contributor search=contributor.attachment_search_text %}
  {% endfor %}
{% endlexxy_prompt %}
```

Each `lexxy-prompt-item` needs a `search` value and signed ID (`attachable` sets both). Optional `menu_template` / `editor_template` point at partials; otherwise the attachable's `render_prompt_menu_html()` and `render_attachment_html(context="editor")` are used.

Default partials ship with django-prose when you do not supply your own:

- [`prose/templates/prose/prompts/attachable_menu.html`](prose/templates/prose/prompts/attachable_menu.html) — popover row
- [`prose/templates/prose/prompts/attachable_editor.html`](prose/templates/prose/prompts/attachable_editor.html) — prompt item chip (includes `{{ attachable.attachment_editor_html|safe }}`)
- [`prose/templates/prose/attachments/attachable_editor.html`](prose/templates/prose/attachments/attachable_editor.html) — optional generic editor chip for `render_attachment_html(context="editor")`

The demo instead uses a shared chip partial ([`mention_chip.html`](example/blog/templates/blog/prompts/mention_chip.html)) included from thin menu/editor/display wrappers.

#### 3. Editor vs display HTML (`content=` hydration)

Lexxy renders custom attachables with `CustomActionTextAttachmentNode`, which only recognizes `<prose-attachment>` tags that carry a **`content=` attribute** (HTML escaped inside the attribute, empty tag body). Inner HTML placed between opening and closing tags is ignored on load and often shows as an unknown attachment.

django-prose handles the round trip for you:

1. **On save** — `RichTextField` canonicalizes attachables to an empty wrapper: `<prose-attachment sgid="…" content-type="application/vnd.prose.mention"></prose-attachment>`.
2. **On edit** — `RichTextEditor` runs `hydrate_editor_attachments()`, which resolves each wrapper and rewrites it with `content="…"` using `render_attachment_html(context="editor")`.
3. **On display** — `{% prose_attachments %}` expands wrappers with `render_attachment_html(context="display")`.

**Use DOMPurify-safe markup in editor chips.** Lexxy sanitizes the HTML inside `content=` with DOMPurify. Stick to simple inline elements such as `<span>` with `class` attributes — the demo mention pill is spans only. Avoid `<button>`, `<svg>`, and other interactive or scriptable markup inside `render_attachment_html(context="editor")`; Lexxy may strip them and the chip will not round-trip. Put icons in CSS (for example a background image on a `<span class="…__delete-icon">`) and wire delete behaviour with small page-level JavaScript instead of buttons inside the chip HTML.

#### 4. Display saved mentions

On public pages, resolve attachable wrappers before marking safe (see [`article.html`](example/blog/templates/blog/article.html)):

```django
{% load prose_attachments %}
{{ comment.body|prose_attachments|safe }}
```

Stored HTML uses `<prose-attachment sgid="…" content-type="application/vnd.prose.mention">` tags; the filter resolves them via `render_attachment_html(context="display")`.

Load `{{ form.media }}` on edit forms that use mention prompts, and include any attachable-specific CSS/JS on pages that render the editor ([`article_edit.html`](example/blog/templates/blog/article_edit.html) loads `mentions.css` / `mentions.js` alongside `form.media`).

#### 5. Demo editor UX (copy vs customize)

The example app's mention pills are **optional presentation** on top of django-prose — you do not need them for basic `@` mentions to work.

| Copy as-is | Customize for your app |
| --- | --- |
| Model + registry + `InlineAttachablePrompt` + `\|prose_attachments\|` pipeline | Your own model fields, trigger character, and search text |
| Separate editor/display templates (or a shared partial with context flags) | Pill colours, avatar shape, typography |
| [`mentions.css`](example/blog/static/blog/mentions.css) rules that force inline flow (`display: inline` on `prose-attachment:has(.mention-pill--editor)`) and hide Lexxy's default `lexxy-node-delete-button` | Class names and visual design |
| [`mentions.js`](example/blog/static/blog/mentions.js) — on selected mention, clicking the avatar triggers Lexxy's hidden delete control | Different delete affordance or keyboard behaviour |

The demo delete UX is CSS-driven: when a mention is selected (`.node--selected`), CSS swaps initials for a delete icon on the avatar span and turns the avatar red; the companion JS clicks Lexxy's built-in delete button programmatically. File uploads use `<button>`/`<svg>` pills because django-prose controls that markup server-side; custom attachables should follow the span-based pattern in [`mention_chip.html`](example/blog/templates/blog/prompts/mention_chip.html).

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

You can find a full example of a blog, built with Django Prose, in the [`example/`](example/) directory. It covers file uploads, YouTube embeds, and **`@` contributor mentions** via `AttachableMixin` — see [Extensible attachables](#extensible-attachables-mentions-inline-references) and the file table there for the canonical implementation paths.

## Upgrading to 3.0 (Trix → Lexxy)

This release replaces the [Trix](https://trix-editor.org/) editor (loaded from a CDN) with a vendored [Lexxy](https://github.com/basecamp/lexxy) editor and introduces database-backed attachments, embeds, and stricter upload validation. Existing HTML in your database is **not** rewritten automatically when you install the new version; most sites can upgrade with a small set of project changes and optional content re-saving.

### What changed

| Area | Before (Trix) | After (Lexxy) |
| --- | --- | --- |
| Editor | Trix from `unpkg.com` + `prose/editor.js` | Vendored Lexxy under `prose/static/prose/lexxy/` + `prose/lexxy-loader.js` |
| Stored files | Saved to storage at `prose/YEAR/MONTH/DATE/UUID.ext`; **no** `Attachment` database row | Same storage path; each upload also creates a `prose.Attachment` row |
| HTML references | Inline `<figure>` / `<img src="…">` (and similar) pointing at `MEDIA_URL` | `<prose-attachment sgid="…">` wrappers with signed IDs (Action Text–style) |
| Public rendering | `{{ field \| safe }}` | Use `{{ field \| prose_attachments \| safe }}` so attachments and embeds resolve correctly |
| Upload API | JSON `{"url": "…"}` | JSON with `sgid`, `url`, `download_url`, `filename`, `content_type`, `size`, `kind`, `previewable` |
| Orphan files | Files left in storage if removed from content | Unlinked `Attachment` rows (and their files) are removed on save; use `cleanup_abandoned_attachments` for uploads never saved |
| Dependencies | `bleach` only | `bleach` + `tinycss2` (for limited inline `color` / `background-color` styles) |
| Sanitizer | Smaller tag/attribute allowlist | Tables, `hr`, `iframe` (embed prefixes only), `prose-attachment`, limited `style`, etc. |

### Upgrade checklist

1. **Upgrade the package** and install dependencies (`tinycss2` is new).
2. **Run migrations** — migration `0003_attachment_richtextattachment` creates `Attachment` and `RichTextAttachment`:

   ```console
   python manage.py migrate prose
   ```

3. **Collect static files** — Trix assets are gone; Lexxy is bundled in the package:

   ```console
   python manage.py collectstatic
   ```

4. **Add middleware** (recommended) so the editor can report attachments removed before save:

   ```python
   MIDDLEWARE = [
       # ...
       "prose.middleware.ProseEditorMiddleware",
       # ...
   ]
   ```

5. **Update public templates** that render article/document body HTML:

   ```django
   {% load prose_attachments %}
   {{ article.body.content|prose_attachments|safe }}
   ```

   The filter leaves plain HTML (including legacy inline images) unchanged when no `<prose-attachment>` tags are present.

6. **Keep `form.media` on edit forms** — the widget still exposes CSS/JS via `RichTextEditor.Media`; you do not need to reference Trix or `prose/editor.js` yourself.

7. **Remove project-specific Trix integration** — delete custom CSS targeting `trix-editor` / `trix-toolbar`, CDN fallbacks, and any calls to `window.djangoProse.initializeEditors()` (that API no longer exists; Lexxy bootstraps from `lexxy-loader.js` on `DOMContentLoaded` and `lexxy:initialize`).

8. **Smoke-test** editing and viewing existing content (see [Post-upgrade testing](#post-upgrade-testing) below).

### Existing attachment content (important)

On the Trix-based release, uploads went to storage and the editor stored **direct URLs** in HTML (typically `<img src="/media/prose/…">` inside a `<figure class="attachment">`). There were **no** `Attachment` rows and **no** signed IDs.

After upgrading:

- **Reading old content on the site** — Inline images and links to `/media/prose/…` continue to work with `|prose_attachments|safe` (or plain `|safe`). No database backfill is required for display-only.
- **Editing old content** — Opening a record in the Lexxy editor shows the previous HTML. Lexxy may normalize layout (lists, tables, spacing). Saving runs the new sanitizer and attachment sync.
- **Attachment lifecycle** — Only references the new code understands (`<prose-attachment sgid="…">`, editor figures with `data-prose-sgid`, or legacy figures with class `django-prose-attachment` **and** a matching `Attachment` row) are tracked. **Legacy Trix inline images are not linked to `Attachment` rows** until you re-insert them or run a custom backfill.
- **Removing an old inline image and saving** does **not** delete the file from storage (there was never an `Attachment` row). New uploads after upgrade are tracked and deleted when unlinked from content.
- **Automatic migration (built in)** — When legacy Trix content is opened in the editor, django-prose creates `Attachment` rows for files already in storage (`prose/Y/M/D/…`) and replaces Trix `<figure class="attachment">` blocks with Lexxy-ready `<prose-attachment>` markup. **Saving** the document persists that format and links attachments via `RichTextAttachment`. No custom backfill script is required for typical Trix uploads.

**Optional manual migration**

| Goal | Approach |
| --- | --- |
| Minimal change | Upgrade + `|prose_attachments|safe`; open and save documents in the admin when you want attachment lifecycle tracking |
| Bulk upgrade without opening each record | Data migration that scans HTML for `/prose/` media URLs and mirrors `migrate_trix_attachments_in_html()` / `sanitize_rich_text_html()` |

Storage paths are unchanged (`prose/%Y/%m/%d/`); you do **not** need to move files on disk.

### New features you can adopt after upgrade

- **YouTube embeds** — Link toolbar → **Embed**; requires embed URL routes (included in `prose.urls`) and `|prose_attachments` on display.
- **Office/PDF file pills** — Non-image uploads render as titled file pills in the editor; SVG is stored as a file link, not inline `<img>` (XSS hardening).
- **MIME allowlist** — Server and editor both honor `PROSE_PERMITTED_ATTACHMENT_TYPES` when set (replaces defaults entirely).
- **Upload permission** — Optional `PROSE_UPLOAD_PERMISSION` dotted path for uploads and embeds.
- **Theme / Lexxy options** — `PROSE_EDITOR_THEME`, `PROSE_LEXXY_EDITOR`, `PROSE_LEXXY_CONFIGURE` (see sections above).

### Sanitizer and stored HTML

Re-saving content applies the expanded allowlist (tables, `mark`, `u`, `del`, `iframe` for configured embed hosts, etc.) and may **strip** markup that was never allowed (e.g. `script`, arbitrary `iframe` hosts, disallowed attributes). Review a few representative documents after the first edit/save cycle.

YouTube and other embeds are stored as empty `<prose-attachment>` wrappers; iframes are injected at display time via `|prose_attachments`, not stored inline (avoids duplicate embeds after Bleach).

### Custom CSS and JavaScript

- Replace selectors such as `.django-prose-editor-container trix-editor` with `.django-prose-lexxy-host` / `lexxy-editor.django-prose-lexxy` (see `prose/static/prose/editor.css`).
- Do not load Trix from unpkg or ship `prose/editor.js`; it has been removed.
- Dynamic forms that previously called `djangoProse.initializeEditors()` should re-render `form.media` or dispatch Lexxy’s initialization path; listen for `lexxy:initialize` on new `lexxy-editor` nodes if you inject editors client-side.

### Post-upgrade testing

1. Open existing rich-text records in the admin — confirm formatting and images still appear.
2. Save without intentional edits — confirm public pages match expectations (`|prose_attachments|safe`).
3. Upload a new image and a PDF — confirm `Attachment` rows in admin and correct public rendering.
4. Remove a **new** upload before save, then save — confirm the file is removed (requires `ProseEditorMiddleware`).
5. If you use embeds — exercise Link → **Embed** and public iframe output.
6. Run `python manage.py cleanup_abandoned_attachments --dry-run` after editors have been in use (optional housekeeping).

### Developing django-prose after the upgrade

Package contributors upgrading vendored Lexxy versions should follow [Updating Lexxy](#updating-lexxy) below; that is separate from this application-level Trix → Lexxy migration.

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
