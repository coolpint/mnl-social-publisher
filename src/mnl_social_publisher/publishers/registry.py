from __future__ import annotations

from .facebook import build_facebook_publish_request
from .instagram import build_instagram_publish_request
from .threads import build_threads_publish_request
from .x import build_x_publish_request
from .youtube import build_youtube_publish_request


PUBLISH_REQUEST_BUILDERS = {
    "youtube_shorts": build_youtube_publish_request,
    "threads": build_threads_publish_request,
    "x": build_x_publish_request,
    "facebook": build_facebook_publish_request,
    "instagram": build_instagram_publish_request,
}


def get_publish_request_builder(platform: str):
    return PUBLISH_REQUEST_BUILDERS[platform]
