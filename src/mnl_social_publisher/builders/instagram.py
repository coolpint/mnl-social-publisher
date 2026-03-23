from __future__ import annotations

from .common import (
    base_hashtags,
    build_post_draft,
    padded_story_points,
    render_post_template,
    text_visual_mode,
)
from ..models import PlatformPostDraft, SocialPackage


def build_instagram_draft(package: SocialPackage) -> PlatformPostDraft:
    prompt_template = "builders/instagram.txt"
    points = padded_story_points(package, limit=3)
    visual_mode, _, _ = text_visual_mode(package, "brand_reel_or_card_template_required")
    hashtags = base_hashtags(package, extra=["인사이트", "오늘의이슈"])
    text = render_post_template(
        prompt_template,
        headline=package.article.headline,
        point_1=points[0],
        point_2=points[1],
        point_3=points[2],
        hashtags_line=" ".join(hashtags[:5]),
    )
    return build_post_draft(
        "instagram",
        package,
        text=text,
        hashtags=hashtags[:5],
        visual_mode=visual_mode,
        prompt_template=prompt_template,
        notes=["Instagram용 캡션 초안입니다."],
    )
