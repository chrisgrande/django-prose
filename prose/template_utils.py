from pathlib import Path

from django.template import Context, Engine

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_prose_engine = None


def get_prose_engine():
    global _prose_engine
    if _prose_engine is None:
        _prose_engine = Engine(dirs=[str(_TEMPLATES_DIR)])
    return _prose_engine


def render_prose_template(template_name, context):
    template = get_prose_engine().get_template(template_name)
    return template.render(Context(context))


def render_attachable_template(template_name, context):
    """Render a prompt or attachment partial from any installed app template."""
    from django.template.loader import render_to_string

    return render_to_string(template_name, context)
