from __future__ import annotations

from .common import (
    base_hashtags,
    build_post_draft,
    padded_story_points,
    render_post_template,
    text_visual_mode,
    trim_text,
)
from ..models import PlatformPostDraft, SocialPackage


def build_x_draft(package: SocialPackage) -> PlatformPostDraft:
    prompt_template = "builders/x.txt"
    points = padded_story_points(package, limit=2)
    visual_mode, _, _ = text_visual_mode(package, "text_only_link_post")
    hashtags = base_hashtags(package)
    candidate = render_post_template(
        prompt_template,
        headline=package.article.headline,
        point_1=points[0],
        point_2=points[1],
    )
    text = trim_text(candidate, 260)
    return build_post_draft(
        "x",
        package,
        text=text,
        hashtags=hashtags[:3],
        visual_mode=visual_mode,
        prompt_template=prompt_template,
        notes=["X용 짧은 확산 초안입니다. 링크는 게시 단계에서 붙일 수 있습니다."],
    )
