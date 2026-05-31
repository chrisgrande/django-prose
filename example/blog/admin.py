from django.contrib import admin

from blog.models import Article, Comment, Contributor


class CommentAdminInline(admin.StackedInline):
    model = Comment


class ArticleAdmin(admin.ModelAdmin):
    inlines = [CommentAdminInline]


admin.site.register(Article, ArticleAdmin)
admin.site.register(Contributor)
