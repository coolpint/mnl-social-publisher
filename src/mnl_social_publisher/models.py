from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RunInfo:
    id: int
    mode: str = ""
    change_type: str = ""
    started_at: str = ""
    finished_at: str = ""
    discovered_count: int = 0
    fetched_count: int = 0
    updated_count: int = 0


@dataclass(frozen=True)
class PlatformTarget:
    builder: str
    publisher: str
    content_kind: str
    delivery_mode: str
    review_required: bool
    status: str
    status_batch_path: str = ""
    status_article_path: str = ""


@dataclass(frozen=True)
class ArticleAsset:
    ordinal: int
    role: str
    source_url: str
    packaged_path: str
    mime_type: str = ""
    width: int | None = None
    height: int | None = None
    alt_text: str = ""
    caption: str = ""
    sha256: str = ""
    social_use_allowed: bool = False
    credit_text: str = ""
    review_required: bool = True
    license_type: str = "unknown"


@dataclass(frozen=True)
class Article:
    idxno: int
    headline: str
    summary: str = ""
    body_text: str = ""
    section_name: str = ""
    subsection_name: str = ""
    author_name: str = ""
    published_at: str = ""
    canonical_url: str = ""
    source_url: str = ""
    site_name: str = ""
    language: str = ""
    browser_title: str = ""
    change_type: str = ""
    copyright_notice: str = ""


@dataclass(frozen=True)
class Rights:
    status: str
    transformation_required: bool
    notes: list[str] = field(default_factory=list)
    music_status: str = ""
    music_license_required: bool = True
    review_required: bool = True


@dataclass(frozen=True)
class PackageFileRefs:
    article_json: str
    article_xml: str
    source_html: str
    body_text: str
    rights: str


@dataclass(frozen=True)
class SocialPackage:
    schema_version: int
    export_kind: str
    exported_at: str
    package_dir: Path
    run: RunInfo
    article: Article
    rights: Rights
    files: PackageFileRefs
    assets_dir: Path
    assets: list[ArticleAsset]
    platforms: dict[str, PlatformTarget]
    status_contract: dict[str, object] = field(default_factory=dict)

    @property
    def package_id(self) -> str:
        return self.package_dir.name


@dataclass(frozen=True)
class BatchPackageRef:
    article_idxno: int
    headline: str
    change_type: str
    package_dir: str
    package_path: str = ""
    article_json_path: str = ""
    rights_path: str = ""
    asset_count: int = 0


@dataclass(frozen=True)
class SocialBatch:
    schema_version: int
    export_kind: str
    exported_at: str
    relative_dir: str
    batch_dir: Path
    batch_manifest_path: Path
    run: RunInfo
    article_count: int
    packages: list[BatchPackageRef]
    status_contract: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationPackageRef:
    article_idxno: int
    headline: str
    change_type: str
    package_dir: str


@dataclass(frozen=True)
class SocialNotification:
    schema_version: int
    event_kind: str
    exported_at: str
    relative_dir: str
    batch_manifest: str
    article_count: int
    review_required: bool
    run: RunInfo
    publisher_targets: list[str]
    packages: list[NotificationPackageRef]
    notification_path: Path
    status_contract: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    decided_at: str = ""
    decided_by: str = ""
    note: str = ""


@dataclass(frozen=True)
class ApprovalRecord:
    schema_version: int
    approval_kind: str
    package_id: str
    article_idxno: int
    approval_path: Path
    decided_at: str = ""
    decided_by: str = ""
    platforms: dict[str, ApprovalDecision] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class YouTubeDraft:
    package_id: str
    article_idxno: int
    privacy_status: str
    delivery_mode: str
    title: str
    description: str
    tags: list[str]
    script_lines: list[str]
    review_required: bool
    visuals_mode: str
    approved_asset_paths: list[str]
    blocked_asset_paths: list[str]
    builder: str
    publisher: str
    source_canonical_url: str
    scenes: list["YouTubeScene"] = field(default_factory=list)
    total_duration_seconds: int = 0
    thumbnail_headline: str = ""
    thumbnail_subheadline: str = ""
    script_prompt_template: str = ""
    description_prompt_template: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class YouTubeScene:
    sequence: int
    cue_label: str
    duration_seconds: int
    narration: str
    overlay_text: str
    visual_direction: str
    asset_path: str = ""


@dataclass(frozen=True)
class PlatformPostDraft:
    platform: str
    package_id: str
    article_idxno: int
    headline: str
    text: str
    hashtags: list[str]
    character_count: int
    review_required: bool
    delivery_mode: str
    visual_mode: str
    approved_asset_paths: list[str]
    blocked_asset_paths: list[str]
    builder: str
    publisher: str
    source_canonical_url: str
    prompt_template: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PublishJob:
    platform: str
    package_id: str
    article_idxno: int
    headline: str
    publisher: str
    status: str
    reason: str
    review_required: bool
    ready_for_publish: bool
    delivery_mode: str
    review_draft_path: str
    package_dir: str
    source_canonical_url: str
    created_at: str = ""
    approval_path: str = ""
    approval_status: str = ""
    approved_by: str = ""
    approved_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PublishRequest:
    schema_version: int
    request_kind: str
    platform: str
    package_id: str
    article_idxno: int
    headline: str
    publisher: str
    delivery_mode: str
    created_at: str
    review_draft_path: str
    approval_path: str
    source_canonical_url: str
    payload: dict

    def to_dict(self) -> dict:
        return asdict(self)
