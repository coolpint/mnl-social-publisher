from __future__ import annotations

from .common import (
    build_post_draft,
    base_hashtags,
    load_platform_profile,
    padded_story_points,
    render_post_template,
    text_visual_mode,
    trim_text,
)
from ..models import PlatformPostDraft, SocialPackage


def build_x_draft(package: SocialPackage) -> PlatformPostDraft:
    profile = load_platform_profile("x")
    prompt_template = profile.prompt_template
    points = padded_story_points(package, limit=profile.story_point_limit)
    visual_mode, _, _ = text_visual_mode(package, profile.visual_mode_fallback)
    hashtags = base_hashtags(package, extra=profile.extra_hashtags)
    candidate = render_post_template(
        prompt_template,
        headline=package.article.headline,
        point_1=points[0],
        point_2=points[1],
    )
    text = trim_text(candidate, profile.character_limit)
    return build_post_draft(
        "x",
        package,
        text=text,
        hashtags=hashtags[:3],
        visual_mode=visual_mode,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        prompt_template=prompt_template,
        notes=profile.notes,
    )
