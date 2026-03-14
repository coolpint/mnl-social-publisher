from __future__ import annotations

from .common import sentence_candidates
from ..models import SocialPackage, YouTubeDraft
from ..platforms import get_platform_target


def _headline_hook(title: str) -> str:
    cleaned = " ".join(title.split())
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}, 핵심만 빠르게 보겠습니다."


def _trim_title(title: str, limit: int = 90) -> str:
    cleaned = " ".join(title.split())
    suffix = " | 1분 요약"
    if len(cleaned) + len(suffix) <= limit:
        return f"{cleaned}{suffix}"
    return f"{cleaned[: limit - len(suffix) - 1].rstrip()}...{suffix}"


def build_youtube_draft(package: SocialPackage) -> YouTubeDraft:
    sentences = []
    sentences.extend(sentence_candidates(package.article.summary))
    sentences.extend(sentence_candidates(package.article.body_text))

    if not sentences:
        sentences = [package.article.headline]

    key_lines = sentences[:3]
    context_line = (
        f"기사 섹션은 {package.article.section_name}이며, 자세한 맥락은 본문 검수에서 확인합니다."
        if package.article.section_name
        else "세부 사실관계는 업로드 전 원문과 함께 다시 검수합니다."
    )
    youtube_target = get_platform_target(package, "youtube_shorts")
    delivery_mode = youtube_target.delivery_mode
    builder_name = youtube_target.builder
    publisher_name = youtube_target.publisher
    review_required = package.rights.review_required
    review_required = review_required or youtube_target.review_required

    description_lines = [
        "머니앤로 기사 기반 숏츠 초안입니다.",
        "자동 생성 결과물이며 업로드 전 검수가 필요합니다.",
    ]
    if package.article.canonical_url:
        description_lines.append(f"원문: {package.article.canonical_url}")
    if package.article.author_name:
        description_lines.append(f"출처: {package.article.author_name}")
    if package.rights.notes:
        description_lines.append(f"권리 메모: {package.rights.notes[0]}")

    tags = ["머니앤로", "뉴스요약", "shorts"]
    if package.article.section_name and package.article.section_name not in tags:
        tags.append(package.article.section_name)
    if package.article.subsection_name and package.article.subsection_name not in tags:
        tags.append(package.article.subsection_name)
    if package.article.site_name and package.article.site_name not in tags:
        tags.append(package.article.site_name)

    visuals_mode = "brand_kinetic_typography"
    approved_asset_paths = [
        asset.packaged_path for asset in package.assets if asset.social_use_allowed
    ]
    blocked_asset_paths = [
        asset.packaged_path for asset in package.assets if not asset.social_use_allowed
    ]
    if approved_asset_paths:
        visuals_mode = "brand_typography_plus_approved_stills"

    return YouTubeDraft(
        package_id=package.package_id,
        article_idxno=package.article.idxno,
        privacy_status="private",
        delivery_mode=delivery_mode,
        title=_trim_title(package.article.headline),
        description="\n".join(description_lines),
        tags=tags[:10],
        script_lines=[
            _headline_hook(package.article.headline),
            *key_lines,
            context_line,
            "기사 원문 재가공과 사실관계 검수 후 게시합니다.",
        ],
        review_required=review_required,
        visuals_mode=visuals_mode,
        approved_asset_paths=approved_asset_paths,
        blocked_asset_paths=blocked_asset_paths,
        builder=builder_name,
        publisher=publisher_name,
        source_canonical_url=package.article.canonical_url,
    )
