from __future__ import annotations

from .common import base_hashtags, build_post_draft, story_points, text_visual_mode
from ..models import PlatformPostDraft, SocialPackage


def build_instagram_draft(package: SocialPackage) -> PlatformPostDraft:
    points = story_points(package, limit=3)
    visual_mode, _, _ = text_visual_mode(package, "brand_reel_or_card_template_required")
    hashtags = base_hashtags(package, extra=["인사이트", "오늘의이슈"])
    text = "\n".join(
        [
            f"[오늘의 포인트] {package.article.headline}",
            f"1. {points[0]}",
            f"2. {points[1] if len(points) > 1 else '세부 내용은 검수 후 보완합니다.'}",
            f"3. {points[2] if len(points) > 2 else '원문 맥락은 링크와 함께 다시 정리합니다.'}",
            "",
            "저장해두고 체크할 이슈로 정리한 인스타그램 캡션 초안입니다.",
            "게시 전 시각 자산 권리와 표현 수위를 다시 확인합니다.",
            "",
            " ".join(hashtags[:5]),
        ]
    )
    return build_post_draft(
        "instagram",
        package,
        text=text,
        hashtags=hashtags[:5],
        visual_mode=visual_mode,
        notes=["Instagram용 캡션 초안입니다."],
    )
