from __future__ import annotations

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
    ]
}


def artifact_filenames(platform: str) -> list[str]:
    if platform in TEXT_ARTIFACT_FILENAMES:
        return TEXT_ARTIFACT_FILENAMES[platform]
    return YOUTUBE_ARTIFACT_FILENAMES.get(platform, [])


def _render_text_platform_artifact(platform: str, draft: dict) -> str:
    lines = [
        f"Headline: {draft['headline']}",
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
        }
        for filename, content in rendered.items():
            artifact_path = output_path / filename
            artifact_path.write_text(content, encoding="utf-8")
            written.append(filename)
    return written
