from django import forms

from blog.models import Article, Comment
from blog.prompts import mention_prompts
from prose.widgets import RichTextEditor


class MentionRichTextField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            RichTextEditor(prompts=mention_prompts()),
        )
        super().__init__(*args, **kwargs)


class CommentForm(forms.ModelForm):
    body = MentionRichTextField()

    class Meta:
        model = Comment
        fields = ["body"]


class ArticleEditForm(forms.ModelForm):
    body = MentionRichTextField(label="Body")

    class Meta:
        model = Article
        fields = ["title", "excerpt"]
        widgets = {
            "excerpt": RichTextEditor(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["body"].initial = self.instance.body.content

    def save(self, commit=True):
        article = super().save(commit=commit)
        if commit and "body" in self.cleaned_data:
            article.body.content = self.cleaned_data["body"]
            article.body.save(update_fields=["content"])
        return article
