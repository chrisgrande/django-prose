from django.forms.widgets import Textarea


class RichTextEditor(Textarea):
    template_name = "prose/forms/widgets/editor.html"

    class Media:
        css = {
            "all": (
                "https://unpkg.com/@37signals/lexxy@0.9.0-beta/dist/stylesheets/lexxy.css",
                "prose/editor.css",
            ),
        }
        js = (
            "prose/lexxy-loader.js",
        )
