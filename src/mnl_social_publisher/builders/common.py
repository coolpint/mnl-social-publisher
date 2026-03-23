from __future__ import annotations

import re

from ..prompt_templates import render_prompt_template
from ..models import PlatformPostDraft, SocialPackage
from ..platforms import get_platform_target


def sentence_candidates(text: str | None) -> list[str]:
    if not text:
        return []
    collapsed = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+|\n+", collapsed)
    return [part.strip() for part in parts if part.strip()]


def story_points(package: SocialPackage, limit: int = 3) -> list[str]:
    points = []
    points.extend(sentence_candidates(package.article.summary))
    points.extend(sentence_candidates(package.article.body_text))
    if not points:
        points = [package.article.headline]
    return points[:limit]


def padded_story_points(package: SocialPackage, limit: int = 3) -> list[str]:
    points = story_points(package, limit=limit)
    fallbacks = [
        "세부 내용은 검수 후 보완합니다.",
        "관련 맥락은 원문 기준으로 다시 확인합니다.",
        "표현 수위와 사실관계는 업로드 전 다시 점검합니다.",
    ]
    filled = list(points)
    while len(filled) < limit:
        fallback = fallbacks[len(filled)] if len(filled) < len(fallbacks) else package.article.headline
        filled.append(fallback)
    return filled[:limit]


def trim_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"


def _normalize_hashtag(raw: str) -> str:
    compact = re.sub(r"\s+", "", raw)
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_]", "", compact)
    return f"#{cleaned}" if cleaned else ""


def base_hashtags(package: SocialPackage, extra: list[str] | None = None) -> list[str]:
    values = [
        "머니앤로",
        package.article.section_name,
        package.article.subsection_name,
    ]
    if extra:
        values.extend(extra)

    hashtags: list[str] = []
    for value in values:
        tag = _normalize_hashtag(value)
        if tag and tag not in hashtags:
            hashtags.append(tag)
    return hashtags


def approved_and_blocked_asset_paths(package: SocialPackage) -> tuple[list[str], list[str]]:
    approved = [asset.packaged_path for asset in package.assets if asset.social_use_allowed]
    blocked = [asset.packaged_path for asset in package.assets if not asset.social_use_allowed]
    return approved, blocked


def review_required_for_platform(package: SocialPackage, platform: str) -> bool:
    target = get_platform_target(package, platform)
    return package.rights.review_required or target.review_required


def default_notes(package: SocialPackage) -> list[str]:
    notes = list(package.rights.notes)
    if package.rights.transformation_required:
        notes.append("원문을 그대로 재게시하지 않고 플랫폼별로 재가공해야 합니다.")
    return notes


def text_visual_mode(package: SocialPackage, fallback: str) -> tuple[str, list[str], list[str]]:
    approved, blocked = approved_and_blocked_asset_paths(package)
    if approved:
        return "approved_source_media_optional", approved, blocked
    return fallback, approved, blocked


def build_post_draft(
    platform: str,
    package: SocialPackage,
    text: str,
    hashtags: list[str],
    visual_mode: str,
    prompt_template: str = "",
    notes: list[str] | None = None,
) -> PlatformPostDraft:
    target = get_platform_target(package, platform)
    approved, blocked = approved_and_blocked_asset_paths(package)
    all_notes = default_notes(package)
    if notes:
        all_notes.extend(notes)
    return PlatformPostDraft(
        platform=platform,
        package_id=package.package_id,
        article_idxno=package.article.idxno,
        headline=package.article.headline,
        text=text,
        hashtags=hashtags,
        character_count=len(text),
        review_required=review_required_for_platform(package, platform),
        delivery_mode=target.delivery_mode,
        visual_mode=visual_mode,
        approved_asset_paths=approved,
        blocked_asset_paths=blocked,
        builder=target.builder,
        publisher=target.publisher,
        source_canonical_url=package.article.canonical_url,
        prompt_template=prompt_template,
        notes=all_notes,
    )


def render_post_template(template_name: str, **context: object) -> str:
    return render_prompt_template(template_name, **context).strip()
