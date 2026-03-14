from __future__ import annotations

import json
from pathlib import Path

from .models import ApprovalDecision, ApprovalRecord, SocialBatch, SocialPackage


APPROVAL_REQUIRED_FIELDS = {
    "schema_version",
    "approval_kind",
    "package_id",
    "article_idxno",
    "platforms",
}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _missing_fields(payload: dict, required_fields: set[str]) -> list[str]:
    return sorted(required_fields - payload.keys())


def resolve_approval_path(
    approval_root: str | Path,
    relative_dir: str,
    package_id: str,
) -> Path:
    return Path(approval_root) / relative_dir / f"{package_id}.json"


def validate_approval_file(approval_path: str | Path) -> list[str]:
    path = Path(approval_path)
    if not path.exists():
        return [f"Approval file does not exist: {path}"]
    if not path.is_file():
        return [f"Approval path is not a file: {path}"]

    try:
        payload = _read_json(path)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    errors: list[str] = []
    missing_fields = _missing_fields(payload, APPROVAL_REQUIRED_FIELDS)
    if missing_fields:
        errors.append(f"approval missing fields: {', '.join(missing_fields)}")
        return errors

    if not isinstance(payload.get("platforms"), dict):
        errors.append("approval platforms must be an object")
        return errors

    for platform, decision in payload["platforms"].items():
        if not isinstance(decision, dict):
            errors.append(f"approval decision for {platform} must be an object")
            continue
        if "approved" not in decision:
            errors.append(f"approval decision for {platform} missing approved")
            continue
        if not isinstance(decision["approved"], bool):
            errors.append(f"approval decision for {platform} approved must be a boolean")

    return errors


def load_approval(approval_path: str | Path) -> ApprovalRecord:
    path = Path(approval_path)
    errors = validate_approval_file(path)
    if errors:
        raise ValueError("; ".join(errors))

    payload = _read_json(path)
    platforms = {
        platform: ApprovalDecision(
            approved=bool(decision.get("approved", False)),
            decided_at=str(decision.get("decided_at") or ""),
            decided_by=str(decision.get("decided_by") or ""),
            note=str(decision.get("note") or ""),
        )
        for platform, decision in payload.get("platforms", {}).items()
    }
    return ApprovalRecord(
        schema_version=int(payload["schema_version"]),
        approval_kind=str(payload["approval_kind"]),
        package_id=str(payload["package_id"]),
        article_idxno=int(payload["article_idxno"]),
        approval_path=path,
        decided_at=str(payload.get("decided_at") or ""),
        decided_by=str(payload.get("decided_by") or ""),
        platforms=platforms,
        notes=list(payload.get("notes", [])),
    )


def load_batch_approvals(
    batch: SocialBatch,
    approval_root: str | Path | None,
) -> dict[str, ApprovalRecord]:
    if approval_root is None:
        return {}

    approvals: dict[str, ApprovalRecord] = {}
    for package_ref in batch.packages:
        approval_path = resolve_approval_path(approval_root, batch.relative_dir, package_ref.package_dir)
        if approval_path.exists():
            approvals[package_ref.package_dir] = load_approval(approval_path)
    return approvals


def approval_for_package(
    package: SocialPackage,
    relative_dir: str,
    approval_root: str | Path | None,
) -> ApprovalRecord | None:
    if approval_root is None:
        return None
    approval_path = resolve_approval_path(approval_root, relative_dir, package.package_id)
    if not approval_path.exists():
        return None
    return load_approval(approval_path)
