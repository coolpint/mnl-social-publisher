from __future__ import annotations

import json
from pathlib import Path

from .approval_loader import resolve_approval_path
from .models import ApprovalSubmission


class LocalJsonApprovalStore:
    store_kind = "local_json"

    def __init__(self, approval_root: str | Path) -> None:
        self.approval_root = Path(approval_root)

    def read_approval(self, relative_dir: str, package_id: str) -> dict | None:
        path = resolve_approval_path(self.approval_root, relative_dir, package_id)
        if not path.exists():
            return None
        return _read_json(path)

    def save_submission(self, submission: ApprovalSubmission) -> Path:
        approval_path = resolve_approval_path(
            self.approval_root,
            submission.relative_dir,
            submission.package_id,
        )
        payload = _merge_submission(
            existing=self.read_approval(submission.relative_dir, submission.package_id),
            submission=submission,
        )
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(_render_json(payload), encoding="utf-8")
        return approval_path


class RemoteJsonApprovalStore:
    store_kind = "remote_json"

    def __init__(self, approval_root: str, client) -> None:
        self.approval_root = approval_root.strip("/")
        self.client = client

    def read_approval(self, relative_dir: str, package_id: str) -> dict | None:
        remote_path = _join_remote(self.approval_root, relative_dir, f"{package_id}.json")
        try:
            payload = self.client.read_bytes(remote_path)
        except Exception:
            return None
        return json.loads(payload.decode("utf-8"))

    def save_submission(self, submission: ApprovalSubmission) -> str:
        remote_path = _join_remote(
            self.approval_root,
            submission.relative_dir,
            f"{submission.package_id}.json",
        )
        payload = _merge_submission(
            existing=self.read_approval(submission.relative_dir, submission.package_id),
            submission=submission,
        )
        self.client.write_bytes(remote_path, _render_json(payload).encode("utf-8"))
        return remote_path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _merge_submission(existing: dict | None, submission: ApprovalSubmission) -> dict:
    payload = existing or {
        "schema_version": 1,
        "approval_kind": "mnl/social-approval",
        "package_id": submission.package_id,
        "article_idxno": int(submission.article_idxno),
        "platforms": {},
        "notes": [],
    }
    decided_at = _utcnow_seconds()
    payload["schema_version"] = 1
    payload["approval_kind"] = "mnl/social-approval"
    payload["package_id"] = submission.package_id
    payload["article_idxno"] = int(submission.article_idxno)
    payload["decided_at"] = decided_at
    payload["decided_by"] = submission.decided_by
    payload["input_method"] = submission.input_method
    platforms = payload.setdefault("platforms", {})
    platforms[submission.platform] = {
        "approved": bool(submission.approved),
        "decided_at": decided_at,
        "decided_by": submission.decided_by,
        "note": submission.note,
    }
    return payload


def _render_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _join_remote(*parts: str | None) -> str:
    cleaned = [str(part).strip("/") for part in parts if part and str(part).strip("/")]
    return "/".join(cleaned)


def _utcnow_seconds() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
