from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .builders.registry import get_platform_builder
from .models import SocialBatch, SocialNotification
from .package_loader import load_package
from .platforms import get_platform_target, review_build_filename, review_draft_filename
from .review_artifacts import artifact_filenames, write_review_artifacts


def _utcnow_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        rendered = json.dumps(payload, ensure_ascii=False)
    path.write_text(rendered + "\n", encoding="utf-8")


def build_review_batch(
    platform: str,
    batch: SocialBatch,
    output_root: str | Path | None = None,
    pretty: bool = False,
    source_notification: SocialNotification | None = None,
) -> dict:
    built_at = _utcnow_seconds()
    drafts = []
    build_summary = {
        "schema_version": 1,
        "build_kind": f"mnl/{platform}-review-batch",
        "built_at": built_at,
        "platform": platform,
        "source_relative_dir": batch.relative_dir,
        "source_batch_manifest": "batch.json",
        "article_count": batch.article_count,
        "drafts": drafts,
    }
    if source_notification is not None:
        build_summary["source_notification"] = source_notification.notification_path.name

    output_base: Path | None = None
    if output_root is not None:
        output_base = Path(output_root) / batch.relative_dir

    builder = get_platform_builder(platform)
    draft_filename = review_draft_filename(platform)
    build_filename = review_build_filename(platform)

    for package_ref in batch.packages:
        package = load_package(batch.batch_dir / package_ref.package_dir)
        target = get_platform_target(package, platform)
        draft = builder(package).to_dict()
        relative_output_path = (Path(batch.relative_dir) / package.package_id / draft_filename).as_posix()
        relative_artifact_paths = [
            (Path(batch.relative_dir) / package.package_id / artifact_name).as_posix()
            for artifact_name in artifact_filenames(platform)
        ]
        if output_base is not None:
            _write_json(output_base / package.package_id / draft_filename, draft, pretty)
            write_review_artifacts(platform, draft, output_base / package.package_id)
        drafts.append(
            {
                "article_idxno": package.article.idxno,
                "package_id": package.package_id,
                "headline": package.article.headline,
                "status": "built",
                "delivery_mode": target.delivery_mode,
                "review_required": draft["review_required"],
                "output_path": relative_output_path,
                "artifact_paths": relative_artifact_paths,
            }
        )

    if output_base is not None:
        _write_json(output_base / build_filename, build_summary, pretty)

    return build_summary


def build_youtube_review_batch(
    batch: SocialBatch,
    output_root: str | Path | None = None,
    pretty: bool = False,
    source_notification: SocialNotification | None = None,
) -> dict:
    return build_review_batch(
        "youtube_shorts",
        batch,
        output_root=output_root,
        pretty=pretty,
        source_notification=source_notification,
    )


def build_review_all_batch(
    batch: SocialBatch,
    output_root: str | Path | None = None,
    pretty: bool = False,
    source_notification: SocialNotification | None = None,
) -> dict:
    built_at = _utcnow_seconds()
    builds = {}
    for platform in ("youtube_shorts", "threads", "x", "facebook", "instagram"):
        builds[platform] = build_review_batch(
            platform,
            batch,
            output_root=output_root,
            pretty=pretty,
            source_notification=source_notification,
        )

    summary = {
        "schema_version": 1,
        "build_kind": "mnl/all-platform-review-batch",
        "built_at": built_at,
        "source_relative_dir": batch.relative_dir,
        "platform_count": len(builds),
        "platforms": sorted(builds.keys()),
        "builds": builds,
    }

    if output_root is not None:
        output_base = Path(output_root) / batch.relative_dir
        _write_json(output_base / "all_review_build.json", summary, pretty)

    return summary
