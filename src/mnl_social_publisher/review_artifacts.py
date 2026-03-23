from __future__ import annotations

import json
from pathlib import Path


TEXT_ARTIFACT_FILENAMES = {
    "threads": ["threads_post.txt"],
    "x": ["x_post.txt"],
    "facebook": ["facebook_post.txt"],
    "instagram": ["instagram_caption.txt"],
}

YOUTUBE_ARTIFACT_FILENAMES = {
    "youtube_shorts": [
        "youtube_title.txt",
        "youtube_description.txt",
        "youtube_script.txt",
        "youtube_storyboard.txt",
        "youtube_scenes.json",
    ]
}


def artifact_filenames(platform: str) -> list[str]:
    if platform in TEXT_ARTIFACT_FILENAMES:
        return TEXT_ARTIFACT_FILENAMES[platform]
    return YOUTUBE_ARTIFACT_FILENAMES.get(platform, [])


def _render_text_platform_artifact(platform: str, draft: dict) -> str:
    lines = [
        f"Headline: {draft['headline']}",
        f"Profile: {draft.get('profile_id', '')} v{draft.get('profile_version', 0)}",
        f"Prompt Template: {draft.get('prompt_template', '')}",
        "",
        draft["text"],
        "",
        f"Source: {draft['source_canonical_url']}",
    ]
    if draft.get("hashtags"):
        lines.extend(["", "Hashtags:", " ".join(draft["hashtags"])])
    if draft.get("notes"):
        lines.extend(["", "Notes:"])
        lines.extend(f"- {note}" for note in draft["notes"])
    return "\n".join(lines).strip() + "\n"


def _render_youtube_title_artifact(draft: dict) -> str:
    return draft["title"].strip() + "\n"


def _render_youtube_description_artifact(draft: dict) -> str:
    return draft["description"].strip() + "\n"


def _render_youtube_script_artifact(draft: dict) -> str:
    lines = [f"Title: {draft['title']}", "", "Script:"]
    lines.extend(f"{index}. {line}" for index, line in enumerate(draft["script_lines"], start=1))
    lines.extend(["", f"Source: {draft['source_canonical_url']}"])
    return "\n".join(lines).strip() + "\n"


def _render_youtube_storyboard_artifact(draft: dict) -> str:
    lines = [
        f"Title: {draft['title']}",
        f"Profile: {draft.get('profile_id', '')} v{draft.get('profile_version', 0)}",
        f"Thumbnail: {draft.get('thumbnail_headline', '')} / {draft.get('thumbnail_subheadline', '')}",
        f"Total Duration: {draft.get('total_duration_seconds', 0)}s",
        "",
        "Scenes:",
    ]
    for scene in draft.get("scenes", []):
        lines.extend(
            [
                f"{scene['sequence']}. [{scene['cue_label']}] {scene['duration_seconds']}s",
                f"   Narration: {scene['narration']}",
                f"   Overlay: {scene['overlay_text']}",
                f"   Visual: {scene['visual_direction']}",
                f"   Asset: {scene.get('asset_path') or '-'}",
            ]
        )
    lines.extend(
        [
            "",
            f"Script Template: {draft.get('script_prompt_template', '')}",
            f"Description Template: {draft.get('description_prompt_template', '')}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_youtube_scenes_json_artifact(draft: dict) -> str:
    payload = {
        "package_id": draft["package_id"],
        "article_idxno": draft["article_idxno"],
        "title": draft["title"],
        "total_duration_seconds": draft.get("total_duration_seconds", 0),
        "thumbnail": {
            "headline": draft.get("thumbnail_headline", ""),
            "subheadline": draft.get("thumbnail_subheadline", ""),
        },
        "scenes": draft.get("scenes", []),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_review_artifacts(
    platform: str,
    draft: dict,
    output_dir: str | Path,
) -> list[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    if platform in TEXT_ARTIFACT_FILENAMES:
        filename = TEXT_ARTIFACT_FILENAMES[platform][0]
        artifact_path = output_path / filename
        artifact_path.write_text(_render_text_platform_artifact(platform, draft), encoding="utf-8")
        written.append(filename)
        return written

    if platform == "youtube_shorts":
        rendered = {
            "youtube_title.txt": _render_youtube_title_artifact(draft),
            "youtube_description.txt": _render_youtube_description_artifact(draft),
            "youtube_script.txt": _render_youtube_script_artifact(draft),
            "youtube_storyboard.txt": _render_youtube_storyboard_artifact(draft),
            "youtube_scenes.json": _render_youtube_scenes_json_artifact(draft),
        }
        for filename, content in rendered.items():
            artifact_path = output_path / filename
            artifact_path.write_text(content, encoding="utf-8")
            written.append(filename)
    return written
