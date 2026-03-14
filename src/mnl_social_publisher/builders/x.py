from __future__ import annotations

from .common import base_hashtags, build_post_draft, story_points, text_visual_mode, trim_text
from ..models import PlatformPostDraft, SocialPackage


def build_x_draft(package: SocialPackage) -> PlatformPostDraft:
    points = story_points(package, limit=2)
    visual_mode, _, _ = text_visual_mode(package, "text_only_link_post")
    hashtags = base_hashtags(package)
    candidate = (
        f"{package.article.headline}\n"
        f"- {points[0]}\n"
        f"- {points[1] if len(points) > 1 else '세부 내용은 검수 후 링크와 함께 정리합니다.'}"
    )
    text = trim_text(candidate, 260)
    return build_post_draft(
        "x",
        package,
        text=text,
        hashtags=hashtags[:3],
        visual_mode=visual_mode,
        notes=["X용 짧은 확산 초안입니다. 링크는 게시 단계에서 붙일 수 있습니다."],
    )
