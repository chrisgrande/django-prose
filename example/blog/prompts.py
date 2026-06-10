from prose.prompts import InlineAttachablePrompt

from blog.models import Contributor


def mention_prompts():
    return InlineAttachablePrompt(
        trigger="@",
        name="mention",
        queryset=Contributor.objects.order_by("name"),
        menu_template="blog/prompts/mention_menu.html",
        editor_template="blog/prompts/mention_editor.html",
    ).render()
