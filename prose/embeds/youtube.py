import json
import re
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import urlopen

from prose.attachables import vendor_content_type
from prose.models import Attachment

YOUTUBE_CONTENT_TYPE = vendor_content_type("youtube")
YOUTUBE_EMBED_PREFIX = "https://www.youtube-nocookie.com/embed/"

_YOUTUBE_PATTERNS = [
    re.compile(
        r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
    ),
]


def parse_youtube_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            if vid and len(vid) == 11:
                return vid
        if parsed.path.startswith("/embed/"):
            vid = parsed.path.split("/embed/")[-1].split("/")[0]
            if len(vid) == 11:
                return vid
        if parsed.path.startswith("/shorts/"):
            vid = parsed.path.split("/shorts/")[-1].split("/")[0]
            if len(vid) == 11:
                return vid
    if parsed.hostname == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        if len(vid) == 11:
            return vid
    for pattern in _YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def youtube_embed_url(video_id):
    return f"{YOUTUBE_EMBED_PREFIX}{video_id}"


def fetch_youtube_title(canonical_url):
    try:
        oembed_url = (
            "https://www.youtube.com/oembed?"
            f"url={quote(canonical_url, safe='')}&format=json"
        )
        with urlopen(oembed_url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return (data.get("title") or "").strip()
    except Exception:
        return ""


class YouTubeEmbedProvider:
    def match(self, url):
        return parse_youtube_video_id(url) is not None

    def create_attachment(self, url):
        video_id = parse_youtube_video_id(url)
        if not video_id:
            return None
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        title = fetch_youtube_title(canonical_url) or f"YouTube video {video_id}"
        embed_url = youtube_embed_url(video_id)
        return Attachment.objects.create(
            content_type=YOUTUBE_CONTENT_TYPE,
            filename=title,
            byte_size=0,
            metadata={
                "provider": "youtube",
                "video_id": video_id,
                "canonical_url": canonical_url,
                "embed_url": embed_url,
                "title": title,
                "url": canonical_url,
            },
        )

    def render_html(self, attachment):
        """HTML for Lexxy editor embed insertion."""
        return attachment.render_attachment_html(context="editor")
