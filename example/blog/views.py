from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from blog.forms import ArticleEditForm, CommentForm
from blog.models import Article, Comment


def blog_index(request):
    articles = Article.objects.select_related("author", "body").order_by("-pk")
    return render(request, "blog/index.html", {"articles": articles})


def blog_login(request):
    if request.user.is_authenticated:
        return redirect("blog_index")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, f"Signed in as {form.get_user().username}.")
        next_url = request.GET.get("next") or "blog_index"
        return redirect(next_url)

    return render(request, "blog/login.html", {"form": form})


def blog_logout(request):
    from django.contrib.auth import logout

    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("blog_index")


def _article_comment_context(request, article):
    comments = article.comment_set.select_related("author").order_by("pk")
    comment_forms = {}
    comment_form = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "comment_edit" and request.user.is_authenticated:
            comment = get_object_or_404(Comment, pk=request.POST.get("comment_id"))
            if comment.author != request.user:
                messages.error(request, "You can only edit your own comments.")
            else:
                form = CommentForm(request.POST, instance=comment)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Comment updated.")
                    return redirect("blog_article", pk=article.pk)
                comment_forms[comment.pk] = form

        elif form_type == "comment_create":
            if not request.user.is_authenticated:
                messages.error(request, "Sign in to post a comment.")
                return redirect("blog_login")
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.article = article
                comment.author = request.user
                comment.save()
                messages.success(request, "Comment posted.")
                return redirect("blog_article", pk=article.pk)

    if comment_form is None and request.user.is_authenticated:
        comment_form = CommentForm()

    if request.method == "GET" and request.user.is_authenticated:
        edit_comment_id = request.GET.get("edit_comment")
        if edit_comment_id and edit_comment_id not in comment_forms:
            comment = comments.filter(pk=edit_comment_id).first()
            if comment and comment.author == request.user:
                comment_forms[comment.pk] = CommentForm(instance=comment)

    comment_rows = [
        {
            "comment": comment,
            "edit_form": comment_forms.get(comment.pk),
            "can_edit": request.user.is_authenticated
            and request.user == comment.author,
        }
        for comment in comments
    ]

    return {
        "article": article,
        "comment_rows": comment_rows,
        "comment_form": comment_form,
    }


def blog_article(request, pk):
    article = get_object_or_404(
        Article.objects.select_related("author", "body"),
        pk=pk,
    )
    context = _article_comment_context(request, article)
    if isinstance(context, HttpResponseBase):
        return context
    return render(request, "blog/article.html", context)


def blog_article_edit(request, pk):
    article = get_object_or_404(
        Article.objects.select_related("author", "body"),
        pk=pk,
    )

    if not request.user.is_authenticated:
        messages.error(request, "Sign in to edit your post.")
        login_url = reverse("blog_login")
        return redirect(f"{login_url}?next={request.path}")

    if request.user != article.author:
        messages.error(request, "You can only edit your own posts.")
        return redirect("blog_article", pk=article.pk)

    article_form = None
    if request.method == "POST":
        article_form = ArticleEditForm(request.POST, instance=article)
        if article_form.is_valid():
            article_form.save()
            messages.success(request, "Post updated.")
            return redirect("blog_article", pk=article.pk)
    else:
        article_form = ArticleEditForm(instance=article)

    return render(
        request,
        "blog/article_edit.html",
        {
            "article": article,
            "article_form": article_form,
        },
    )
