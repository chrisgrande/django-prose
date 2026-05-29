from django.utils.module_loading import import_string

from prose.embeds.youtube import YouTubeEmbedProvider

_default_providers = [
    "prose.embeds.youtube.YouTubeEmbedProvider",
]


def get_embed_providers():
    from django.conf import settings

    paths = getattr(settings, "PROSE_EMBED_PROVIDERS", None)
    if paths is None:
        paths = _default_providers
    return [import_string(path)() for path in paths]


def match_embed_provider(url):
    for provider in get_embed_providers():
        if provider.match(url):
            return provider
    return None
