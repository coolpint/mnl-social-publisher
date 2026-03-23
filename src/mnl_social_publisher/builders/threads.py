from __future__ import annotations

from .common import (
    build_post_draft,
    base_hashtags,
    load_platform_profile,
    padded_story_points,
    render_post_template,
    text_visual_mode,
)
from ..models import PlatformPostDraft, SocialPackage


def build_threads_draft(package: SocialPackage) -> PlatformPostDraft:
    profile = load_platform_profile("threads")
    prompt_template = profile.prompt_template
    points = padded_story_points(package, limit=profile.story_point_limit)
    visual_mode, _, _ = text_visual_mode(package, profile.visual_mode_fallback)
    hashtags = base_hashtags(package, extra=profile.extra_hashtags)
    text = render_post_template(
        prompt_template,
        headline=package.article.headline,
        point_1=points[0],
        point_2=points[1],
        point_3=points[2],
    )
    return build_post_draft(
        "threads",
        package,
        text=text,
        hashtags=hashtags[:4],
        visual_mode=visual_mode,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        prompt_template=prompt_template,
        notes=profile.notes,
    )
