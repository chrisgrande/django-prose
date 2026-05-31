from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from blog import views


urlpatterns = [
    path("", views.blog_index, name="blog_index"),
    path("articles/<int:pk>/", views.blog_article, name="blog_article"),
    path("articles/<int:pk>/edit/", views.blog_article_edit, name="blog_article_edit"),
    path("login/", views.blog_login, name="blog_login"),
    path("logout/", views.blog_logout, name="blog_logout"),
    path("admin/", admin.site.urls),
    path("prose/", include("prose.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
