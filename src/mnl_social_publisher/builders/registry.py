from __future__ import annotations

from .facebook import build_facebook_draft
from .instagram import build_instagram_draft
from .threads import build_threads_draft
from .x import build_x_draft
from .youtube import build_youtube_draft


PLATFORM_BUILDERS = {
    "youtube_shorts": build_youtube_draft,
    "threads": build_threads_draft,
    "x": build_x_draft,
    "facebook": build_facebook_draft,
    "instagram": build_instagram_draft,
}


def get_platform_builder(platform: str):
    return PLATFORM_BUILDERS[platform]
