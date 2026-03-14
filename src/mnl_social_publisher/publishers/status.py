from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from ..approval_loader import approval_for_package
from ..models import ApprovalRecord, PublishJob, SocialBatch, SocialNotification, SocialPackage
from ..package_loader import load_package
from ..platforms import get_platform_target, review_draft_filename
from ..social_status import (
    build_article_status_path,
    build_article_status_payload,
    build_batch_status_path,
    build_batch_status_payload,
    local_status_path,
)


def _utcnow_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: dict, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        rendered = json.dumps(payload, ensure_ascii=False)
    path.write_text(rendered + "\n", encoding="utf-8")


def _job_state(
    draft_exists: bool,
    review_required: bool,
    approval: ApprovalRecord | None,
    platform: str,
) -> tuple[str, str, bool, str, str, str]:
    if not draft_exists:
        return (
            "blocked_missing_review_draft",
            "Review draft file not found",
            False,
            "",
            "",
            "",
        )

    if not review_required:
        return ("ready_to_publish", "Review bypassed by target", True, "", "", "")

    if approval is None:
        return ("awaiting_review", "Manual review required", False, "", "", "")

    decision = approval.platforms.get(platform)
    if decision is None:
        return (
            "awaiting_platform_approval",
            "Approval file exists but this platform has no decision",
            False,
            approval.approval_path.as_posix(),
            "",
            "",
        )
    if decision.approved:
        return (
            "approved_for_publish",
            decision.note or "Approved for publishing",
            True,
            approval.approval_path.as_posix(),
            decision.decided_by or approval.decided_by,
            decision.decided_at or approval.decided_at,
        )
    return (
        "rejected_in_review",
        decision.note or "Rejected in review",
        False,
        approval.approval_path.as_posix(),
        decision.decided_by or approval.decided_by,
        decision.decided_at or approval.decided_at,
    )


def _to_contract_state(job_status: str) -> str:
    if job_status in {"ready_to_publish", "approved_for_publish"}:
        return "approved"
    if job_status in {"awaiting_review", "awaiting_platform_approval"}:
        return "review_required"
    if job_status in {"blocked_missing_review_draft", "rejected_in_review"}:
        return "blocked"
    return "received"


def _resolve_batch_status_local_path(
    status_root: str | Path,
    batch: SocialBatch,
    platform: str,
) -> Path:
    template = str(
        batch.status_contract.get("batch_path_template")
        or build_batch_status_path(platform, batch.relative_dir)
    )
    contract_path = template.format(platform=platform)
    return local_status_path(status_root, contract_path)


def _resolve_article_status_local_path(
    status_root: str | Path,
    batch: SocialBatch,
    package: SocialPackage,
    platform: str,
) -> Path:
    target = get_platform_target(package, platform)
    contract_path = target.status_article_path
    if not contract_path:
        template = str(
            batch.status_contract.get("article_path_template")
            or build_article_status_path(platform, batch.relative_dir, package.article.idxno)
        )
        contract_path = template.format(platform=platform, idxno=package.article.idxno)
    return local_status_path(status_root, contract_path)


def _write_batch_status(
    status_root: str | Path,
    batch: SocialBatch,
    platform: str,
    jobs: list[dict],
    pretty: bool,
    state_override: str | None = None,
    detail_override: str = "",
) -> None:
    failed_count = sum(1 for job in jobs if _to_contract_state(job["status"]) == "blocked")
    approved_count = sum(1 for job in jobs if _to_contract_state(job["status"]) == "approved")
    review_count = sum(1 for job in jobs if _to_contract_state(job["status"]) == "review_required")
    processed_count = len(jobs)

    if state_override is not None:
        batch_state = state_override
    elif approved_count:
        batch_state = "approved"
    elif review_count:
        batch_state = "review_required"
    elif failed_count == len(jobs):
        batch_state = "blocked"
    else:
        batch_state = "received"

    detail = detail_override or (
        f"approved={approved_count}, review_required={review_count}, blocked={failed_count}"
    )
    payload = build_batch_status_payload(
        platform=platform,
        relative_dir=batch.relative_dir,
        run_id=batch.run.id,
        state=batch_state,
        article_count=batch.article_count,
        processed_count=processed_count,
        failed_count=failed_count,
        detail=detail,
    )
    _write_json(_resolve_batch_status_local_path(status_root, batch, platform), payload, pretty)


def _write_article_status(
    status_root: str | Path,
    batch: SocialBatch,
    package: SocialPackage,
    job: PublishJob,
    pretty: bool,
    state_override: str | None = None,
    detail_override: str = "",
    output_path: str = "",
) -> None:
    payload = build_article_status_payload(
        platform=job.platform,
        relative_dir=batch.relative_dir,
        run_id=batch.run.id,
        article_idxno=job.article_idxno,
        state=state_override or _to_contract_state(job.status),
        package_dir=job.package_dir,
        package_path=f"{job.package_dir}/package.json",
        detail=detail_override or job.reason,
        output_path=output_path or job.review_draft_path,
        review_url="",
    )
    _write_json(
        _resolve_article_status_local_path(status_root, batch, package, job.platform),
        payload,
        pretty,
    )


def prepare_publish_batch(
    platform: str,
    batch: SocialBatch,
    review_root: str | Path,
    approval_root: str | Path | None = None,
    status_root: str | Path | None = None,
    pretty: bool = False,
    source_notification: SocialNotification | None = None,
) -> dict:
    created_at = _utcnow_seconds()
    review_root_path = Path(review_root)

    jobs = []
    summary = {
        "schema_version": 1,
        "publish_kind": f"mnl/{platform}-publish-batch",
        "created_at": created_at,
        "platform": platform,
        "source_relative_dir": batch.relative_dir,
        "article_count": batch.article_count,
        "jobs": jobs,
    }
    if source_notification is not None:
        summary["source_notification"] = source_notification.notification_path.name

    for package_ref in batch.packages:
        package = load_package(batch.batch_dir / package_ref.package_dir)
        target = get_platform_target(package, platform)
        draft_relative = (
            Path(batch.relative_dir) / package.package_id / review_draft_filename(platform)
        ).as_posix()
        draft_path = review_root_path / draft_relative
        review_required = target.review_required or package.rights.review_required
        approval = approval_for_package(package, batch.relative_dir, approval_root)
        status, reason, ready_for_publish, approval_path, approved_by, approved_at = _job_state(
            draft_exists=draft_path.exists(),
            review_required=review_required,
            approval=approval,
            platform=platform,
        )

        job = PublishJob(
            platform=platform,
            package_id=package.package_id,
            article_idxno=package.article.idxno,
            headline=package.article.headline,
            publisher=target.publisher,
            status=status,
            reason=reason,
            review_required=review_required,
            ready_for_publish=ready_for_publish,
            delivery_mode=target.delivery_mode,
            review_draft_path=draft_relative,
            package_dir=(Path(batch.relative_dir) / package.package_id).as_posix(),
            source_canonical_url=package.article.canonical_url,
            approval_path=approval_path,
            approval_status=status,
            approved_by=approved_by,
            approved_at=approved_at,
            created_at=created_at,
        )
        job_payload = job.to_dict()
        jobs.append(job_payload)

        if status_root is not None:
            _write_article_status(status_root, batch, package, job, pretty)

    if status_root is not None:
        _write_batch_status(status_root, batch, platform, jobs, pretty)

    return summary
