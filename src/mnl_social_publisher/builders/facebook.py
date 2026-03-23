from __future__ import annotations

from .common import (
    base_hashtags,
    build_post_draft,
    padded_story_points,
    render_post_template,
    text_visual_mode,
)
from ..models import PlatformPostDraft, SocialPackage


def build_facebook_draft(package: SocialPackage) -> PlatformPostDraft:
    prompt_template = "builders/facebook.txt"
    points = padded_story_points(package, limit=3)
    visual_mode, _, _ = text_visual_mode(package, "brand_square_summary_card")
    hashtags = base_hashtags(package, extra=["이슈정리"])
    text = render_post_template(
        prompt_template,
        headline=package.article.headline,
        point_1=points[0],
        point_2=points[1],
        point_3=points[2],
    )
    return build_post_draft(
        "facebook",
        package,
        text=text,
        hashtags=hashtags[:4],
        visual_mode=visual_mode,
        prompt_template=prompt_template,
        notes=["Facebook용 설명형 포스트 초안입니다."],
    )
