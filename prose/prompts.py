"""Inline Lexxy prompts for attachable models (mentions, references, etc.)."""

from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from prose.attachables import AttachableMixin


def render_lexxy_prompt(*, trigger, name, items_html="", src=None):
    """
    Render a <lexxy-prompt> wrapper.

    See https://basecamp.github.io/lexxy/prompts/inline-attachments.html
    """
    attrs = {
        "trigger": trigger,
        "name": name,
    }
    if src:
        attrs["src"] = src
    attr_str = " ".join(f'{key}="{escape(value)}"' for key, value in attrs.items())
    return format_html("<lexxy-prompt {}>{}</lexxy-prompt>", mark_safe(attr_str), mark_safe(items_html))


def render_lexxy_prompt_item(
    attachable,
    *,
    search=None,
    menu_html=None,
    editor_html=None,
):
    """
    Render a <lexxy-prompt-item> for an AttachableMixin instance.

    menu_html and editor_html override the attachable's default prompt rendering.
    """
    if not isinstance(attachable, AttachableMixin):
        raise TypeError("attachable must use AttachableMixin")

    search_text = search if search is not None else attachable.attachment_search_text()
    menu_html = menu_html if menu_html is not None else attachable.render_prompt_menu_html()
    editor_html = (
        editor_html if editor_html is not None else attachable.render_prompt_editor_html()
    )
    content_type = attachable.attachment_content_type

    return format_html(
        '<lexxy-prompt-item search="{search}" sgid="{sgid}">'
        '<template type="menu">{menu}</template>'
        '<template type="editor" content-type="{content_type}">{editor}</template>'
        "</lexxy-prompt-item>",
        search=escape(search_text),
        sgid=escape(attachable.attachable_sgid),
        menu=mark_safe(menu_html),
        content_type=escape(content_type),
        editor=mark_safe(editor_html),
    )


class InlineAttachablePrompt:
    """
    Build inline <lexxy-prompt> markup from attachable model instances.

    Example::

        RichTextEditor(
            prompts=InlineAttachablePrompt(
                trigger="@",
                name="mention",
                queryset=Person.objects.all(),
            ).render(),
        )
    """

    def __init__(
        self,
        *,
        trigger,
        name,
        queryset=None,
        items=None,
        search=None,
        menu_template=None,
        editor_template=None,
        src=None,
    ):
        self.trigger = trigger
        self.name = name
        self.queryset = queryset
        self.items = items
        self.search = search
        self.menu_template = menu_template
        self.editor_template = editor_template
        self.src = src

    def iter_attachables(self):
        if self.items is not None:
            yield from self.items
            return
        if self.queryset is not None:
            yield from self.queryset

    def render_item(self, attachable):
        menu_html = None
        editor_html = None
        if self.menu_template or self.editor_template:
            from prose.template_utils import render_attachable_template

            context = {
                "attachable": attachable,
                attachable._meta.model_name: attachable,
                "contributor": attachable,
            }
            if self.menu_template:
                menu_html = render_attachable_template(self.menu_template, context)
            if self.editor_template:
                editor_html = render_attachable_template(self.editor_template, context)

        search = self.search(attachable) if callable(self.search) else self.search
        return render_lexxy_prompt_item(
            attachable,
            search=search,
            menu_html=menu_html,
            editor_html=editor_html,
        )

    def render_items(self):
        return mark_safe("".join(str(self.render_item(item)) for item in self.iter_attachables()))

    def render(self):
        return render_lexxy_prompt(
            trigger=self.trigger,
            name=self.name,
            items_html=self.render_items(),
            src=self.src,
        )
