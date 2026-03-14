from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..models import PublishJob, SocialBatch, SocialNotification
from ..package_loader import load_package
from .common import read_review_draft, write_json
from .registry import get_publish_request_builder
from .status import _write_article_status, _write_batch_status, prepare_publish_batch


def _utcnow_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_publish_requests(
    platform: str,
    batch: SocialBatch,
    review_root: str | Path,
    approval_root: str | Path | None = None,
    outbox_root: str | Path | None = None,
    status_root: str | Path | None = None,
    pretty: bool = False,
    source_notification: SocialNotification | None = None,
) -> dict:
    created_at = _utcnow_seconds()
    prepare_summary = prepare_publish_batch(
        platform,
        batch,
        review_root=review_root,
        approval_root=approval_root,
        status_root=status_root,
        pretty=pretty,
        source_notification=source_notification,
    )
    requests = []
    summary = {
        "schema_version": 1,
        "request_batch_kind": f"mnl/{platform}-request-batch",
        "created_at": created_at,
        "platform": platform,
        "source_relative_dir": batch.relative_dir,
        "request_count": 0,
        "requests": requests,
    }
    if source_notification is not None:
        summary["source_notification"] = source_notification.notification_path.name

    outbox_base = None if outbox_root is None else Path(outbox_root) / platform / batch.relative_dir
    request_builder = get_publish_request_builder(platform)

    for job_payload in prepare_summary["jobs"]:
        if not job_payload["ready_for_publish"]:
            continue
        draft_path = Path(review_root) / job_payload["review_draft_path"]
        draft = read_review_draft(draft_path)
        job = PublishJob(**job_payload)
        package = load_package(batch.batch_dir / job.package_id)
        request = request_builder(
            draft=draft,
            job=job,
            created_at=created_at,
        )
        request_payload = request.to_dict()
        relative_request_path = (
            Path(platform) / batch.relative_dir / f"{job_payload['package_id']}.json"
        ).as_posix()
        requests.append(
            {
                "package_id": job_payload["package_id"],
                "article_idxno": job_payload["article_idxno"],
                "publisher": job_payload["publisher"],
                "request_path": relative_request_path,
                "status": "queued_in_outbox",
            }
        )
        if outbox_base is not None:
            write_json(outbox_base / f"{job_payload['package_id']}.json", request_payload, pretty)
            if status_root is not None:
                _write_article_status(
                    status_root,
                    batch,
                    package,
                    job,
                    pretty,
                    state_override="publishing",
                    detail_override="Publish request written to outbox.",
                    output_path=relative_request_path,
                )

    summary["request_count"] = len(requests)
    if outbox_base is not None:
        write_json(outbox_base / "publish_requests.json", summary, pretty)
    if status_root is not None:
        _write_batch_status(
            status_root,
            batch,
            platform,
            prepare_summary["jobs"],
            pretty,
            state_override="publishing" if requests else None,
            detail_override="Publish requests written to outbox." if requests else "",
        )
    return summary
