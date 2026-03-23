from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
import json
import os
from pathlib import Path


PROFILE_PACKAGE = "mnl_social_publisher.profiles"


@dataclass(frozen=True)
class TextGenerationProfile:
    platform: str
    profile_id: str
    version: int
    prompt_template: str
    story_point_limit: int
    character_limit: int
    visual_mode_fallback: str
    extra_hashtags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    inspiration_patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class YouTubeGenerationProfile:
    platform: str
    profile_id: str
    version: int
    script_prompt_template: str
    description_prompt_template: str
    story_point_limit: int
    title_limit: int
    title_suffix: str
    hook_suffix: str
    thumbnail_headline_limit: int
    thumbnail_subheadline_limit: int
    scene_labels: list[str] = field(default_factory=list)
    scene_durations: list[int] = field(default_factory=list)
    default_tags: list[str] = field(default_factory=list)
    visual_mode_fallback: str = "brand_kinetic_typography"
    visual_mode_with_assets: str = "brand_typography_plus_approved_stills"
    max_tags: int = 10
    notes: list[str] = field(default_factory=list)
    inspiration_patterns: list[str] = field(default_factory=list)


def load_text_generation_profile(platform: str) -> TextGenerationProfile:
    payload = _load_profile_payload(platform)
    return TextGenerationProfile(
        platform=str(payload["platform"]),
        profile_id=str(payload["profile_id"]),
        version=int(payload["version"]),
        prompt_template=str(payload["prompt_template"]),
        story_point_limit=int(payload.get("story_point_limit", 3)),
        character_limit=int(payload.get("character_limit", 0)),
        visual_mode_fallback=str(payload["visual_mode_fallback"]),
        extra_hashtags=list(payload.get("extra_hashtags", [])),
        notes=list(payload.get("notes", [])),
        inspiration_patterns=list(payload.get("inspiration_patterns", [])),
    )


def load_youtube_generation_profile() -> YouTubeGenerationProfile:
    payload = _load_profile_payload("youtube_shorts")
    return YouTubeGenerationProfile(
        platform=str(payload["platform"]),
        profile_id=str(payload["profile_id"]),
        version=int(payload["version"]),
        script_prompt_template=str(payload["script_prompt_template"]),
        description_prompt_template=str(payload["description_prompt_template"]),
        story_point_limit=int(payload.get("story_point_limit", 3)),
        title_limit=int(payload.get("title_limit", 90)),
        title_suffix=str(payload.get("title_suffix", "")),
        hook_suffix=str(payload.get("hook_suffix", "")),
        thumbnail_headline_limit=int(payload.get("thumbnail_headline_limit", 34)),
        thumbnail_subheadline_limit=int(payload.get("thumbnail_subheadline_limit", 20)),
        scene_labels=list(payload.get("scene_labels", [])),
        scene_durations=[int(value) for value in payload.get("scene_durations", [])],
        default_tags=list(payload.get("default_tags", [])),
        visual_mode_fallback=str(payload.get("visual_mode_fallback", "brand_kinetic_typography")),
        visual_mode_with_assets=str(
            payload.get("visual_mode_with_assets", "brand_typography_plus_approved_stills")
        ),
        max_tags=int(payload.get("max_tags", 10)),
        notes=list(payload.get("notes", [])),
        inspiration_patterns=list(payload.get("inspiration_patterns", [])),
    )


def _load_profile_payload(platform: str) -> dict:
    override_root = _override_root()
    if override_root is not None:
        override_path = override_root / "platforms" / f"{platform}.json"
        if override_path.exists():
            return json.loads(override_path.read_text(encoding="utf-8"))

    resource_path = files(PROFILE_PACKAGE).joinpath("platforms", f"{platform}.json")
    return json.loads(resource_path.read_text(encoding="utf-8"))


def _override_root() -> Path | None:
    raw = (os.getenv("MNL_SOCIAL_PROFILE_ROOT") or "").strip()
    if not raw:
        return None
    return Path(raw)
