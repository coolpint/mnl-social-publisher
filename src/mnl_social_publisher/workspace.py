from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
import tempfile

from .approval_inputs import ApprovalSubmission
from .approval_stores import LocalJsonApprovalStore, RemoteJsonApprovalStore
from .models import SocialBatch, SocialPackage
from .onedrive import OneDriveClient, OneDriveConfig
from .package_loader import load_batch, load_package
from .platforms import review_draft_filename
from .publishers.requests import create_publish_requests
from .review_builds import build_review_all_batch
from .settings import Settings
from .social_status import (
    build_article_status_path,
    build_batch_status_path,
    local_status_path,
    rooted_status_path,
)


class WorkspaceError(RuntimeError):
    pass


class BaseWorkspace(ABC):
    @abstractmethod
    def describe_roots(self) -> list[tuple[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def list_recent_batches(self, limit: int = 24) -> list[SocialBatch]:
        raise NotImplementedError

    @abstractmethod
    def load_batch(self, relative_dir: str) -> SocialBatch:
        raise NotImplementedError

    @abstractmethod
    def load_package(self, relative_dir: str, package_id: str) -> SocialPackage:
        raise NotImplementedError

    @abstractmethod
    def read_review_artifact(self, relative_dir: str, package_id: str, artifact_name: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def read_batch_status(self, batch: SocialBatch, platform: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def read_article_status(self, batch: SocialBatch, package: SocialPackage, platform: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def read_approval(self, relative_dir: str, package_id: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def build_review_all(self, relative_dir: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def save_approval(
        self,
        *,
        relative_dir: str,
        package_id: str,
        article_idxno: int,
        platform: str,
        approved: bool,
        decided_by: str,
        note: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def submit_approval(self, submission: ApprovalSubmission) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def approval_store_kind(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_publish_requests(self, relative_dir: str, platform: str) -> dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_review_root(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_approval_root(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_outbox_root(self) -> bool:
        raise NotImplementedError


class LocalWorkspace(BaseWorkspace):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.approval_store = (
            LocalJsonApprovalStore(settings.approval_root)
            if settings.approval_root is not None
            else None
        )

    @property
    def has_review_root(self) -> bool:
        return self.settings.review_root is not None

    @property
    def has_approval_root(self) -> bool:
        return self.settings.approval_root is not None

    @property
    def has_outbox_root(self) -> bool:
        return self.settings.outbox_root is not None

    @property
    def approval_store_kind(self) -> str:
        if self.approval_store is None:
            return "not configured"
        return self.approval_store.store_kind

    def describe_roots(self) -> list[tuple[str, str]]:
        return [
            ("Mode", "local filesystem"),
            ("Inbox", _stringify_path(self.settings.inbox_root)),
            ("Review", _stringify_path(self.settings.review_root)),
            ("Approval", _stringify_path(self.settings.approval_root)),
            ("Outbox", _stringify_path(self.settings.outbox_root)),
            ("Status", _stringify_path(self.settings.status_root)),
        ]

    def list_recent_batches(self, limit: int = 24) -> list[SocialBatch]:
        if self.settings.inbox_root is None:
            return []
        batch_dirs = sorted(
            {path.parent for path in self.settings.inbox_root.rglob("batch.json")},
            key=lambda path: path.as_posix(),
            reverse=True,
        )
        batches: list[SocialBatch] = []
        for batch_dir in batch_dirs[:limit]:
            try:
                batches.append(load_batch(batch_dir))
            except Exception:
                continue
        return batches

    def load_batch(self, relative_dir: str) -> SocialBatch:
        if self.settings.inbox_root is None:
            raise WorkspaceError("Inbox root is not configured")
        return load_batch(self.settings.inbox_root / relative_dir)

    def load_package(self, relative_dir: str, package_id: str) -> SocialPackage:
        batch = self.load_batch(relative_dir)
        return load_package(batch.batch_dir / package_id)

    def read_review_artifact(self, relative_dir: str, package_id: str, artifact_name: str) -> str | None:
        if self.settings.review_root is None:
            return None
        path = self.settings.review_root / relative_dir / package_id / artifact_name
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def read_batch_status(self, batch: SocialBatch, platform: str) -> dict | None:
        if self.settings.status_root is None:
            return None
        contract_path = str(
            batch.status_contract.get("batch_path_template")
            or build_batch_status_path(platform, batch.relative_dir)
        ).format(platform=platform)
        path = local_status_path(self.settings.status_root, contract_path)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_article_status(self, batch: SocialBatch, package: SocialPackage, platform: str) -> dict | None:
        if self.settings.status_root is None:
            return None
        target = package.platforms.get(platform)
        contract_path = "" if target is None else target.status_article_path
        if not contract_path:
            template = str(
                batch.status_contract.get("article_path_template")
                or build_article_status_path(platform, batch.relative_dir, package.article.idxno)
            )
            contract_path = template.format(platform=platform, idxno=package.article.idxno)
        path = local_status_path(self.settings.status_root, contract_path)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_approval(self, relative_dir: str, package_id: str) -> dict | None:
        if self.approval_store is None:
            return None
        return self.approval_store.read_approval(relative_dir, package_id)

    def build_review_all(self, relative_dir: str) -> dict:
        if self.settings.review_root is None:
            raise WorkspaceError("Review root is not configured")
        batch = self.load_batch(relative_dir)
        return build_review_all_batch(batch, output_root=self.settings.review_root, pretty=True)

    def save_approval(
        self,
        *,
        relative_dir: str,
        package_id: str,
        article_idxno: int,
        platform: str,
        approved: bool,
        decided_by: str,
        note: str,
    ) -> None:
        self.submit_approval(
            ApprovalSubmission(
                relative_dir=relative_dir,
                package_id=package_id,
                article_idxno=article_idxno,
                platform=platform,
                approved=approved,
                decided_by=decided_by,
                note=note,
            )
        )

    def submit_approval(self, submission: ApprovalSubmission) -> None:
        if self.approval_store is None:
            raise WorkspaceError("Approval root is not configured")
        self.approval_store.save_submission(submission)

    def create_publish_requests(self, relative_dir: str, platform: str) -> dict:
        if self.settings.review_root is None or self.settings.outbox_root is None:
            raise WorkspaceError("Review root or outbox root is not configured")
        batch = self.load_batch(relative_dir)
        return create_publish_requests(
            platform,
            batch,
            review_root=self.settings.review_root,
            approval_root=self.settings.approval_root,
            outbox_root=self.settings.outbox_root,
            status_root=self.settings.status_root,
            pretty=True,
        )


class RemoteWorkspace(BaseWorkspace):
    def __init__(self, settings: Settings, client: OneDriveClient) -> None:
        self.settings = settings
        self.client = client
        self.inbox_root = _require_remote_root(settings.inbox_remote_root, "inbox")
        self.review_root = settings.review_remote_root
        self.approval_root = settings.approval_remote_root
        self.outbox_root = settings.outbox_remote_root
        self.status_root = settings.status_remote_root
        self.approval_store = (
            RemoteJsonApprovalStore(self.approval_root, client)
            if self.approval_root
            else None
        )

    @property
    def has_review_root(self) -> bool:
        return bool(self.review_root)

    @property
    def has_approval_root(self) -> bool:
        return bool(self.approval_root)

    @property
    def has_outbox_root(self) -> bool:
        return bool(self.outbox_root)

    @property
    def approval_store_kind(self) -> str:
        if self.approval_store is None:
            return "not configured"
        return self.approval_store.store_kind

    def describe_roots(self) -> list[tuple[str, str]]:
        return [
            ("Mode", "onedrive remote"),
            ("Inbox", self.inbox_root),
            ("Review", self.review_root or "not set"),
            ("Approval", self.approval_root or "not set"),
            ("Outbox", self.outbox_root or "not set"),
            ("Status", self.status_root or "not set"),
        ]

    def list_recent_batches(self, limit: int = 24) -> list[SocialBatch]:
        relative_dirs = self._list_recent_relative_dirs(limit=limit)
        batches: list[SocialBatch] = []
        for relative_dir in relative_dirs:
            try:
                batches.append(self.load_batch(relative_dir))
            except Exception:
                continue
        return batches

    def load_batch(self, relative_dir: str) -> SocialBatch:
        with tempfile.TemporaryDirectory(prefix="mnl-social-remote-batch-") as temp_dir:
            batch_root = self._hydrate_batch(relative_dir, Path(temp_dir))
            return load_batch(batch_root)

    def load_package(self, relative_dir: str, package_id: str) -> SocialPackage:
        with tempfile.TemporaryDirectory(prefix="mnl-social-remote-package-") as temp_dir:
            batch_root = self._hydrate_batch(relative_dir, Path(temp_dir), package_ids={package_id})
            return load_package(batch_root / package_id)

    def read_review_artifact(self, relative_dir: str, package_id: str, artifact_name: str) -> str | None:
        if not self.review_root:
            return None
        remote_path = _join_remote(self.review_root, relative_dir, package_id, artifact_name)
        if not self.client.exists(remote_path):
            return None
        return self.client.read_bytes(remote_path).decode("utf-8")

    def read_batch_status(self, batch: SocialBatch, platform: str) -> dict | None:
        if not self.status_root:
            return None
        contract_path = str(
            batch.status_contract.get("batch_path_template")
            or build_batch_status_path(platform, batch.relative_dir)
        ).format(platform=platform)
        remote_path = rooted_status_path(self.status_root, contract_path)
        return self._read_remote_json_if_exists(remote_path)

    def read_article_status(self, batch: SocialBatch, package: SocialPackage, platform: str) -> dict | None:
        if not self.status_root:
            return None
        target = package.platforms.get(platform)
        contract_path = "" if target is None else target.status_article_path
        if not contract_path:
            template = str(
                batch.status_contract.get("article_path_template")
                or build_article_status_path(platform, batch.relative_dir, package.article.idxno)
            )
            contract_path = template.format(platform=platform, idxno=package.article.idxno)
        remote_path = rooted_status_path(self.status_root, contract_path)
        return self._read_remote_json_if_exists(remote_path)

    def read_approval(self, relative_dir: str, package_id: str) -> dict | None:
        if self.approval_store is None:
            return None
        return self.approval_store.read_approval(relative_dir, package_id)

    def build_review_all(self, relative_dir: str) -> dict:
        if not self.review_root:
            raise WorkspaceError("Review remote root is not configured")
        with tempfile.TemporaryDirectory(prefix="mnl-social-remote-build-") as temp_dir:
            temp_root = Path(temp_dir)
            batch_root = self._hydrate_batch(relative_dir, temp_root / "inbox")
            batch = load_batch(batch_root)
            review_root = temp_root / "review"
            summary = build_review_all_batch(batch, output_root=review_root, pretty=True)
            self._upload_tree(review_root / relative_dir, _join_remote(self.review_root, relative_dir))
            return summary

    def save_approval(
        self,
        *,
        relative_dir: str,
        package_id: str,
        article_idxno: int,
        platform: str,
        approved: bool,
        decided_by: str,
        note: str,
    ) -> None:
        self.submit_approval(
            ApprovalSubmission(
                relative_dir=relative_dir,
                package_id=package_id,
                article_idxno=article_idxno,
                platform=platform,
                approved=approved,
                decided_by=decided_by,
                note=note,
            )
        )

    def submit_approval(self, submission: ApprovalSubmission) -> None:
        if self.approval_store is None:
            raise WorkspaceError("Approval remote root is not configured")
        self.approval_store.save_submission(submission)

    def create_publish_requests(self, relative_dir: str, platform: str) -> dict:
        if not self.review_root or not self.outbox_root:
            raise WorkspaceError("Review remote root or outbox remote root is not configured")
        with tempfile.TemporaryDirectory(prefix="mnl-social-remote-publish-") as temp_dir:
            temp_root = Path(temp_dir)
            batch_root = self._hydrate_batch(relative_dir, temp_root / "inbox")
            batch = load_batch(batch_root)

            review_root = temp_root / "review"
            approval_root = temp_root / "approval"
            outbox_root = temp_root / "outbox"
            status_root = temp_root / "status"

            self._hydrate_review_inputs(batch, review_root, platform)
            self._hydrate_approval_inputs(batch, approval_root)

            summary = create_publish_requests(
                platform,
                batch,
                review_root=review_root,
                approval_root=approval_root if self.approval_root else None,
                outbox_root=outbox_root,
                status_root=status_root if self.status_root else None,
                pretty=True,
            )

            self._upload_tree(outbox_root / platform / relative_dir, _join_remote(self.outbox_root, platform, relative_dir))
            if self.status_root:
                self._upload_tree(status_root / platform / relative_dir, _join_remote(self.status_root, platform, relative_dir))
            return summary

    def _list_recent_relative_dirs(self, limit: int) -> list[str]:
        results: list[str] = []
        years = self._list_dir_names(self.inbox_root)
        for year in sorted(years, reverse=True):
            months = self._list_dir_names(_join_remote(self.inbox_root, year))
            for month in sorted(months, reverse=True):
                days = self._list_dir_names(_join_remote(self.inbox_root, year, month))
                for day in sorted(days, reverse=True):
                    runs = self._list_dir_names(_join_remote(self.inbox_root, year, month, day))
                    for run_name in sorted(runs, reverse=True):
                        relative_dir = f"{year}/{month}/{day}/{run_name}"
                        if self.client.exists(_join_remote(self.inbox_root, relative_dir, "batch.json")):
                            results.append(relative_dir)
                            if len(results) >= limit:
                                return results
        return results

    def _list_dir_names(self, remote_path: str) -> list[str]:
        try:
            entries = self.client.list_children(remote_path)
        except Exception:
            return []
        return [entry.name for entry in entries if entry.is_folder]

    def _hydrate_batch(
        self,
        relative_dir: str,
        destination_root: Path,
        package_ids: set[str] | None = None,
    ) -> Path:
        batch_root = destination_root / relative_dir
        batch_root.mkdir(parents=True, exist_ok=True)
        batch_remote_path = _join_remote(self.inbox_root, relative_dir, "batch.json")
        batch_payload = self._download_json(batch_remote_path, batch_root / "batch.json")
        for package_ref in batch_payload.get("packages", []):
            package_id = str(package_ref.get("package_dir") or "")
            if not package_id:
                continue
            if package_ids is not None and package_id not in package_ids:
                continue
            self._hydrate_package(relative_dir, package_id, batch_root / package_id)
        return batch_root

    def _hydrate_package(self, relative_dir: str, package_id: str, package_root: Path) -> None:
        package_root.mkdir(parents=True, exist_ok=True)
        package_payload = self._download_json(
            _join_remote(self.inbox_root, relative_dir, package_id, "package.json"),
            package_root / "package.json",
        )
        file_refs = dict(package_payload.get("files", {}))
        for key in ("article_json", "article_xml", "source_html", "body_text", "rights"):
            relative_name = str(file_refs.get(key) or "")
            if not relative_name:
                continue
            remote_path = _join_remote(self.inbox_root, relative_dir, package_id, relative_name)
            local_path = package_root / relative_name
            payload = self.client.read_bytes(remote_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payload)
        assets_dir_rel = str(package_payload.get("assets", {}).get("directory") or "assets")
        (package_root / assets_dir_rel).mkdir(parents=True, exist_ok=True)

    def _hydrate_review_inputs(self, batch: SocialBatch, review_root: Path, platform: str) -> None:
        for package_ref in batch.packages:
            draft_name = review_draft_filename(platform)
            remote_path = _join_remote(self.review_root, batch.relative_dir, package_ref.package_dir, draft_name)
            if not self.client.exists(remote_path):
                continue
            local_path = review_root / batch.relative_dir / package_ref.package_dir / draft_name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(self.client.read_bytes(remote_path))

    def _hydrate_approval_inputs(self, batch: SocialBatch, approval_root: Path) -> None:
        if not self.approval_root:
            return
        for package_ref in batch.packages:
            remote_path = _join_remote(self.approval_root, batch.relative_dir, f"{package_ref.package_dir}.json")
            if not self.client.exists(remote_path):
                continue
            local_path = approval_root / batch.relative_dir / f"{package_ref.package_dir}.json"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(self.client.read_bytes(remote_path))

    def _upload_tree(self, local_dir: Path, remote_root: str) -> None:
        if not local_dir.exists():
            return
        for path in sorted(local_dir.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(local_dir).as_posix()
            self.client.write_bytes(_join_remote(remote_root, relative_path), path.read_bytes())

    def _download_json(self, remote_path: str, local_path: Path) -> dict:
        payload = self.client.read_bytes(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(payload)
        return json.loads(payload.decode("utf-8"))

    def _read_remote_json_if_exists(self, remote_path: str) -> dict | None:
        if not self.client.exists(remote_path):
            return None
        return json.loads(self.client.read_bytes(remote_path).decode("utf-8"))


def workspace_from_settings(
    settings: Settings,
    *,
    client: OneDriveClient | None = None,
) -> BaseWorkspace:
    if settings.storage_backend == "onedrive":
        remote_client = client or OneDriveClient(OneDriveConfig.from_env())
        return RemoteWorkspace(settings, remote_client)
    return LocalWorkspace(settings)


def _join_remote(*parts: str | None) -> str:
    cleaned = [str(part).strip("/") for part in parts if part and str(part).strip("/")]
    return "/".join(cleaned)


def _stringify_path(path: Path | None) -> str:
    return str(path) if path is not None else "not set"


def _require_remote_root(value: str | None, label: str) -> str:
    if value:
        return value
    raise WorkspaceError(f"{label} remote root is not configured")
