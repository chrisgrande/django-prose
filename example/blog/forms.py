from django import forms

from blog.models import Article, Comment
from blog.prompts import mention_prompts
from prose.models import Document
from prose.widgets import RichTextEditor


class MentionRichTextField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            RichTextEditor(prompts=mention_prompts()),
        )
        super().__init__(*args, **kwargs)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"] = MentionRichTextField()


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "excerpt"]
        widgets = {
            "excerpt": RichTextEditor(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"] = MentionRichTextField(label="Body")
        if self.instance.pk:
            self.fields["body"].initial = self.instance.body.content

    def save(self, commit=True):
        body_content = self.cleaned_data.get("body", "")
        is_new = not self.instance.pk

        if is_new:
            article = super().save(commit=False)
            article.body = Document.objects.create(content=body_content)
            if commit:
                article.save()
            return article

        article = super().save(commit=commit)
        if commit and "body" in self.cleaned_data:
            article.body.content = body_content
            article.body.save(update_fields=["content"])
        return article
