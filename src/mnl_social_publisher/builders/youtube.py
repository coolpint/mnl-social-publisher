from __future__ import annotations

from .common import padded_story_points, trim_text
from ..generation_profiles import YouTubeGenerationProfile, load_youtube_generation_profile
from ..models import SocialPackage, YouTubeDraft, YouTubeScene
from ..platforms import get_platform_target
from ..prompt_templates import render_prompt_template


def _headline_hook(title: str, suffix: str) -> str:
    cleaned = " ".join(title.split())
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}{suffix}"


def _trim_title(title: str, limit: int, suffix: str) -> str:
    cleaned = " ".join(title.split())
    if len(cleaned) + len(suffix) <= limit:
        return f"{cleaned}{suffix}"
    return f"{cleaned[: limit - len(suffix) - 1].rstrip()}...{suffix}"


def _trim_thumbnail_text(text: str, limit: int) -> str:
    return trim_text(text, limit)


def _render_nonempty_lines(template_name: str, **context: object) -> list[str]:
    return [
        line.strip()
        for line in render_prompt_template(template_name, **context).splitlines()
        if line.strip()
    ]


def _scene_specs(
    script_lines: list[str],
    profile: YouTubeGenerationProfile,
) -> list[tuple[str, str, int]]:
    labels = profile.scene_labels or ["hook", "point_1", "point_2", "point_3", "context", "cta"]
    durations = profile.scene_durations or [5, 7, 7, 7, 8, 6]
    scene_count = min(len(script_lines), len(labels), len(durations))
    return [
        (labels[index], line, durations[index])
        for index, line in enumerate(script_lines[:scene_count])
    ]


def _build_scenes(
    script_lines: list[str],
    approved_asset_paths: list[str],
    profile: YouTubeGenerationProfile,
) -> list[YouTubeScene]:
    scenes: list[YouTubeScene] = []
    for sequence, (cue_label, line, duration_seconds) in enumerate(
        _scene_specs(script_lines, profile),
        start=1,
    ):
        asset_path = ""
        visual_direction = "brand kinetic typography with animated data cues"
        if approved_asset_paths and sequence in (2, 3):
            asset_path = approved_asset_paths[min(sequence - 2, len(approved_asset_paths) - 1)]
            visual_direction = "approved still image with typography overlay and headline motion"
        scenes.append(
            YouTubeScene(
                sequence=sequence,
                cue_label=cue_label,
                duration_seconds=duration_seconds,
                narration=line,
                overlay_text=_trim_thumbnail_text(line, limit=min(profile.thumbnail_headline_limit, 28)),
                visual_direction=visual_direction,
                asset_path=asset_path,
            )
        )
    return scenes


def build_youtube_draft(package: SocialPackage) -> YouTubeDraft:
    profile = load_youtube_generation_profile()
    story_points = padded_story_points(package, limit=max(profile.story_point_limit, 3))
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

    script_prompt_template = profile.script_prompt_template
    description_prompt_template = profile.description_prompt_template

    tags = list(profile.default_tags)
    if package.article.section_name and package.article.section_name not in tags:
        tags.append(package.article.section_name)
    if package.article.subsection_name and package.article.subsection_name not in tags:
        tags.append(package.article.subsection_name)
    if package.article.site_name and package.article.site_name not in tags:
        tags.append(package.article.site_name)

    visuals_mode = profile.visual_mode_fallback
    approved_asset_paths = [
        asset.packaged_path for asset in package.assets if asset.social_use_allowed
    ]
    blocked_asset_paths = [
        asset.packaged_path for asset in package.assets if not asset.social_use_allowed
    ]
    if approved_asset_paths:
        visuals_mode = profile.visual_mode_with_assets

    script_lines = _render_nonempty_lines(
        script_prompt_template,
        hook=_headline_hook(package.article.headline, profile.hook_suffix),
        point_1=story_points[0],
        point_2=story_points[1],
        point_3=story_points[2],
        context_line=context_line,
    )
    description_lines = _render_nonempty_lines(
        description_prompt_template,
        canonical_line=f"원문: {package.article.canonical_url}" if package.article.canonical_url else "",
        author_line=f"출처: {package.article.author_name}" if package.article.author_name else "",
        rights_line=f"권리 메모: {package.rights.notes[0]}" if package.rights.notes else "",
    )
    scenes = _build_scenes(script_lines, approved_asset_paths, profile)
    total_duration_seconds = sum(scene.duration_seconds for scene in scenes)
    thumbnail_headline = _trim_thumbnail_text(
        package.article.headline,
        limit=profile.thumbnail_headline_limit,
    )
    thumbnail_subheadline = _trim_thumbnail_text(
        package.article.section_name or "머니앤로 1분 요약",
        limit=profile.thumbnail_subheadline_limit,
    )

    return YouTubeDraft(
        package_id=package.package_id,
        article_idxno=package.article.idxno,
        privacy_status="private",
        delivery_mode=delivery_mode,
        title=_trim_title(
            package.article.headline,
            limit=profile.title_limit,
            suffix=profile.title_suffix,
        ),
        description="\n".join(description_lines),
        tags=tags[: profile.max_tags],
        script_lines=script_lines,
        review_required=review_required,
        visuals_mode=visuals_mode,
        approved_asset_paths=approved_asset_paths,
        blocked_asset_paths=blocked_asset_paths,
        builder=builder_name,
        publisher=publisher_name,
        source_canonical_url=package.article.canonical_url,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        scenes=scenes,
        total_duration_seconds=total_duration_seconds,
        thumbnail_headline=thumbnail_headline,
        thumbnail_subheadline=thumbnail_subheadline,
        script_prompt_template=script_prompt_template,
        description_prompt_template=description_prompt_template,
    )
