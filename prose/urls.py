from django.urls import path

from prose import views


urlpatterns = [
    path("attachment/", views.upload_attachment, name="prose_upload_attachment"),
    path("embed/", views.embed_url, name="prose_embed"),
    path("embed/check/", views.embed_check, name="prose_embed_check"),
    path(
        "attachment/caption/",
        views.update_attachment_caption,
        name="prose_update_attachment_caption",
    ),
]
