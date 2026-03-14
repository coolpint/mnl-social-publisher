from __future__ import annotations

from .common import base_hashtags, build_post_draft, story_points, text_visual_mode
from ..models import PlatformPostDraft, SocialPackage


def build_facebook_draft(package: SocialPackage) -> PlatformPostDraft:
    points = story_points(package, limit=3)
    visual_mode, _, _ = text_visual_mode(package, "brand_square_summary_card")
    hashtags = base_hashtags(package, extra=["이슈정리"])
    text = "\n\n".join(
        [
            package.article.headline,
            f"첫째, {points[0]}",
            f"둘째, {points[1] if len(points) > 1 else '세부 사실은 검수 후 보완합니다.'}",
            f"셋째, {points[2] if len(points) > 2 else '관련 맥락은 원문 기준으로 다시 확인합니다.'}",
            "검수 완료 후 링크와 함께 게시하는 전제의 초안입니다.",
        ]
    )
    return build_post_draft(
        "facebook",
        package,
        text=text,
        hashtags=hashtags[:4],
        visual_mode=visual_mode,
        notes=["Facebook용 설명형 포스트 초안입니다."],
    )
