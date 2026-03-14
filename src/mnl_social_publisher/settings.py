from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    inbox_root: Path | None
    review_root: Path | None
    approval_root: Path | None
    outbox_root: Path | None
    status_root: Path | None

    @classmethod
    def from_env(cls) -> "Settings":
        inbox_root = os.getenv("MNL_SOCIAL_INBOX_ROOT")
        review_root = os.getenv("MNL_SOCIAL_REVIEW_ROOT")
        approval_root = os.getenv("MNL_SOCIAL_APPROVAL_ROOT")
        outbox_root = os.getenv("MNL_SOCIAL_OUTBOX_ROOT")
        status_root = os.getenv("MNL_SOCIAL_STATUS_ROOT")
        return cls(
            inbox_root=Path(inbox_root) if inbox_root else None,
            review_root=Path(review_root) if review_root else None,
            approval_root=Path(approval_root) if approval_root else None,
            outbox_root=Path(outbox_root) if outbox_root else None,
            status_root=Path(status_root) if status_root else None,
        )
