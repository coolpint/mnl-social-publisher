from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    inbox_root: Path | None = None
    review_root: Path | None = None
    approval_root: Path | None = None
    outbox_root: Path | None = None
    status_root: Path | None = None
    storage_backend: str = "local"
    inbox_remote_root: str | None = None
    review_remote_root: str | None = None
    approval_remote_root: str | None = None
    outbox_remote_root: str | None = None
    status_remote_root: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        inbox_root = os.getenv("MNL_SOCIAL_INBOX_ROOT")
        review_root = os.getenv("MNL_SOCIAL_REVIEW_ROOT")
        approval_root = os.getenv("MNL_SOCIAL_APPROVAL_ROOT")
        outbox_root = os.getenv("MNL_SOCIAL_OUTBOX_ROOT")
        status_root = os.getenv("MNL_SOCIAL_STATUS_ROOT")
        storage_backend = (os.getenv("MNL_SOCIAL_STORAGE_BACKEND") or "local").strip().lower()
        return cls(
            inbox_root=Path(inbox_root) if inbox_root else None,
            review_root=Path(review_root) if review_root else None,
            approval_root=Path(approval_root) if approval_root else None,
            outbox_root=Path(outbox_root) if outbox_root else None,
            status_root=Path(status_root) if status_root else None,
            storage_backend=storage_backend or "local",
            inbox_remote_root=_clean_remote_root(os.getenv("MNL_SOCIAL_INBOX_REMOTE_ROOT")),
            review_remote_root=_clean_remote_root(os.getenv("MNL_SOCIAL_REVIEW_REMOTE_ROOT")),
            approval_remote_root=_clean_remote_root(os.getenv("MNL_SOCIAL_APPROVAL_REMOTE_ROOT")),
            outbox_remote_root=_clean_remote_root(os.getenv("MNL_SOCIAL_OUTBOX_REMOTE_ROOT")),
            status_remote_root=_clean_remote_root(os.getenv("MNL_SOCIAL_STATUS_REMOTE_ROOT")),
        )


def _clean_remote_root(value: str | None) -> str | None:
    cleaned = (value or "").strip().strip("/")
    return cleaned or None
