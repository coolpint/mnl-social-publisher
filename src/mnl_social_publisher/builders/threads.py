from __future__ import annotations

from .common import base_hashtags, build_post_draft, story_points, text_visual_mode
from ..models import PlatformPostDraft, SocialPackage


def build_threads_draft(package: SocialPackage) -> PlatformPostDraft:
    points = story_points(package, limit=3)
    visual_mode, _, _ = text_visual_mode(package, "brand_text_card_required")
    hashtags = base_hashtags(package, extra=["뉴스브리프"])
    paragraphs = [
        f"{package.article.headline}",
        f"핵심: {points[0]}",
    ]
    if len(points) > 1:
        paragraphs.append(f"이어서: {points[1]}")
    if len(points) > 2:
        paragraphs.append(f"왜 중요한가: {points[2]}")
    paragraphs.append("링크와 사실관계는 검수 후 함께 정리합니다.")
    text = "\n\n".join(paragraphs)
    return build_post_draft(
        "threads",
        package,
        text=text,
        hashtags=hashtags[:4],
        visual_mode=visual_mode,
        notes=["Threads용 확산 초안입니다."],
    )
