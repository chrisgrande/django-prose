from django import template
from django.template import Node, TemplateSyntaxError
from django.utils.safestring import mark_safe

from prose.attachables import sign_attachable
from prose.content import render_prose_attachments
from prose.prompts import render_lexxy_prompt, render_lexxy_prompt_item

register = template.Library()


@register.filter(name="prose_attachments")
def prose_attachments_filter(html, context="display"):
    if not html:
        return ""
    return mark_safe(render_prose_attachments(html, context=context))


@register.simple_tag
def attachable_sgid(obj):
    return sign_attachable(obj)


class LexxyPromptNode(Node):
    def __init__(self, nodelist, trigger, name, src):
        self.nodelist = nodelist
        self.trigger = trigger
        self.name = name
        self.src = src

    def render(self, context):
        items_html = self.nodelist.render(context)
        return render_lexxy_prompt(
            trigger=self.trigger.resolve(context),
            name=self.name.resolve(context),
            items_html=items_html,
            src=self.src.resolve(context) if self.src else None,
        )


@register.tag(name="lexxy_prompt")
def do_lexxy_prompt(parser, token):
    """
    Inline Lexxy prompt wrapper. Wrap {% lexxy_prompt_item %} tags inside.

    Usage::

        {% lexxy_prompt trigger="@" name="mention" %}
          {% for person in people %}
            {% lexxy_prompt_item attachable=person %}
          {% endfor %}
        {% endlexxy_prompt %}
    """
    bits = token.split_contents()
    trigger = None
    name = None
    src = None
    for bit in bits[1:]:
        if bit.startswith("trigger="):
            trigger = parser.compile_filter(bit.split("=", 1)[1])
        elif bit.startswith("name="):
            name = parser.compile_filter(bit.split("=", 1)[1])
        elif bit.startswith("src="):
            src = parser.compile_filter(bit.split("=", 1)[1])
        else:
            raise TemplateSyntaxError(
                f"'{bits[0]}' accepts trigger=, name=, and optional src= only"
            )
    if trigger is None or name is None:
        raise TemplateSyntaxError(f"'{bits[0]}' requires trigger= and name=")

    nodelist = parser.parse(("endlexxy_prompt",))
    parser.delete_first_token()
    return LexxyPromptNode(nodelist, trigger, name, src)


class LexxyPromptItemNode(Node):
    def __init__(
        self,
        nodelist,
        attachable,
        search,
        menu_template,
        editor_template,
    ):
        self.nodelist = nodelist
        self.attachable = attachable
        self.search = search
        self.menu_template = menu_template
        self.editor_template = editor_template

    def render(self, context):
        attachable = self.attachable.resolve(context)
        search = self.search.resolve(context) if self.search else None
        menu_html = None
        editor_html = None

        if self.nodelist:
            with context.push(attachable=attachable):
                body = self.nodelist.render(context).strip()
                if body:
                    menu_html = body

        if self.menu_template:
            from prose.template_utils import render_attachable_template

            menu_html = render_attachable_template(
                self.menu_template.resolve(context),
                {
                    **context.flatten(),
                    "attachable": attachable,
                    attachable._meta.model_name: attachable,
                    "contributor": attachable,
                },
            )
        if self.editor_template:
            from prose.template_utils import render_attachable_template

            editor_html = render_attachable_template(
                self.editor_template.resolve(context),
                {
                    **context.flatten(),
                    "attachable": attachable,
                    attachable._meta.model_name: attachable,
                    "contributor": attachable,
                },
            )

        return render_lexxy_prompt_item(
            attachable,
            search=search,
            menu_html=menu_html,
            editor_html=editor_html,
        )


@register.tag(name="lexxy_prompt_item")
def do_lexxy_prompt_item(parser, token):
    """
    One selectable item inside {% lexxy_prompt %}.

    Usage::

        {% lexxy_prompt_item attachable=person search=person.name %}
        {% lexxy_prompt_item attachable=person menu_template="people/menu.html" editor_template="people/editor.html" %}
        {% lexxy_prompt_item attachable=person %}Custom menu label{% endlexxy_prompt_item %}
    """
    bits = token.split_contents()
    attachable = None
    search = None
    menu_template = None
    editor_template = None
    for bit in bits[1:]:
        if bit.startswith("attachable="):
            attachable = parser.compile_filter(bit.split("=", 1)[1])
        elif bit.startswith("search="):
            search = parser.compile_filter(bit.split("=", 1)[1])
        elif bit.startswith("menu_template="):
            menu_template = parser.compile_filter(bit.split("=", 1)[1])
        elif bit.startswith("editor_template="):
            editor_template = parser.compile_filter(bit.split("=", 1)[1])
        else:
            raise TemplateSyntaxError(
                f"'{bits[0]}' accepts attachable=, search=, menu_template=, "
                "and editor_template= only"
            )
    if attachable is None:
        raise TemplateSyntaxError(f"'{bits[0]}' requires attachable=")

    nodelist = parser.parse(("endlexxy_prompt_item",))
    parser.delete_first_token()
    return LexxyPromptItemNode(
        nodelist,
        attachable,
        search,
        menu_template,
        editor_template,
    )
