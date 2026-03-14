from __future__ import annotations

import json
from pathlib import Path

from .models import (
    Article,
    ArticleAsset,
    BatchPackageRef,
    NotificationPackageRef,
    PackageFileRefs,
    PlatformTarget,
    Rights,
    RunInfo,
    SocialBatch,
    SocialNotification,
    SocialPackage,
)

PACKAGE_REQUIRED_FIELDS = {
    "schema_version",
    "export_kind",
    "exported_at",
    "run",
    "article",
    "files",
    "assets",
    "platforms",
}
PACKAGE_FILE_REQUIRED_FIELDS = {
    "article_json",
    "article_xml",
    "source_html",
    "body_text",
    "rights",
}
PACKAGE_ARTICLE_REQUIRED_FIELDS = {"idxno", "headline"}
ARTICLE_REQUIRED_FIELDS = {"schema_version", "article", "assets"}
ARTICLE_PAYLOAD_REQUIRED_FIELDS = {"idxno", "headline"}
RIGHTS_REQUIRED_FIELDS = {"schema_version", "status", "article_idxno", "article_text", "music"}
BATCH_REQUIRED_FIELDS = {
    "schema_version",
    "export_kind",
    "exported_at",
    "relative_dir",
    "run",
    "article_count",
    "packages",
}
NOTIFICATION_REQUIRED_FIELDS = {
    "schema_version",
    "event_kind",
    "exported_at",
    "relative_dir",
    "batch_manifest",
    "article_count",
    "review_required",
    "run",
    "publisher_targets",
    "packages",
}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _missing_fields(payload: dict, required_fields: set[str]) -> list[str]:
    return sorted(required_fields - payload.keys())


def _as_run_info(payload: dict) -> RunInfo:
    return RunInfo(
        id=int(payload.get("id") or 0),
        mode=str(payload.get("mode") or ""),
        change_type=str(payload.get("change_type") or ""),
        started_at=str(payload.get("started_at") or ""),
        finished_at=str(payload.get("finished_at") or ""),
        discovered_count=int(payload.get("discovered_count") or 0),
        fetched_count=int(payload.get("fetched_count") or 0),
        updated_count=int(payload.get("updated_count") or 0),
    )


def _load_payloads(package_dir: Path) -> tuple[dict, dict, dict]:
    package_payload = _read_json(package_dir / "package.json")
    file_payload = package_payload.get("files", {})
    article_path = package_dir / str(file_payload.get("article_json") or "article.json")
    rights_path = package_dir / str(file_payload.get("rights") or "rights.json")
    article_payload = _read_json(article_path)
    rights_payload = _read_json(rights_path)
    return package_payload, article_payload, rights_payload


def validate_package_dir(package_dir: str | Path) -> list[str]:
    root = Path(package_dir)
    errors: list[str] = []

    if not root.exists():
        return [f"Package directory does not exist: {root}"]
    if not root.is_dir():
        return [f"Package path is not a directory: {root}"]

    package_file = root / "package.json"
    if not package_file.exists():
        return ["Missing required file: package.json"]

    try:
        package_payload = _read_json(package_file)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    missing_package = _missing_fields(package_payload, PACKAGE_REQUIRED_FIELDS)
    if missing_package:
        errors.append(f"package.json missing fields: {', '.join(missing_package)}")

    file_payload = package_payload.get("files")
    if not isinstance(file_payload, dict):
        errors.append("package.json files must be an object")
        return errors

    missing_file_refs = _missing_fields(file_payload, PACKAGE_FILE_REQUIRED_FIELDS)
    if missing_file_refs:
        errors.append(f"package.json files missing fields: {', '.join(missing_file_refs)}")

    article_stub = package_payload.get("article")
    if not isinstance(article_stub, dict):
        errors.append("package.json article must be an object")
    else:
        missing_article_stub = _missing_fields(article_stub, PACKAGE_ARTICLE_REQUIRED_FIELDS)
        if missing_article_stub:
            errors.append(
                f"package.json article missing fields: {', '.join(missing_article_stub)}"
            )

    if errors:
        return errors

    referenced_paths = {
        name: root / str(file_payload[name])
        for name in PACKAGE_FILE_REQUIRED_FIELDS
    }
    for name, path in referenced_paths.items():
        if not path.exists():
            errors.append(f"Missing referenced file for {name}: {path.name}")

    assets_payload = package_payload.get("assets", {})
    assets_dir_rel = str(assets_payload.get("directory") or "")
    if assets_dir_rel:
        assets_dir = root / assets_dir_rel
        if not assets_dir.exists():
            errors.append(f"Missing referenced directory: {assets_dir_rel}")

    if errors:
        return errors

    try:
        _, article_payload, rights_payload = _load_payloads(root)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    missing_article = _missing_fields(article_payload, ARTICLE_REQUIRED_FIELDS)
    missing_rights = _missing_fields(rights_payload, RIGHTS_REQUIRED_FIELDS)

    if missing_article:
        errors.append(f"article.json missing fields: {', '.join(missing_article)}")
    if missing_rights:
        errors.append(f"rights.json missing fields: {', '.join(missing_rights)}")

    article_body = article_payload.get("article")
    if not isinstance(article_body, dict):
        errors.append("article.json article must be an object")
        return errors

    missing_article_fields = _missing_fields(article_body, ARTICLE_PAYLOAD_REQUIRED_FIELDS)
    if missing_article_fields:
        errors.append(
            f"article.json article missing fields: {', '.join(missing_article_fields)}"
        )

    if errors:
        return errors

    package_idxno = int(package_payload["article"]["idxno"])
    article_idxno = int(article_body["idxno"])
    rights_idxno = int(rights_payload["article_idxno"])

    if package_idxno != article_idxno:
        errors.append("package.json article idxno does not match article.json article idxno")
    if rights_idxno != article_idxno:
        errors.append("rights.json article_idxno does not match article.json article idxno")

    platforms = package_payload.get("platforms")
    if not isinstance(platforms, dict):
        errors.append("package.json platforms must be an object")

    if not isinstance(article_payload.get("assets"), list):
        errors.append("article.json assets must be a list")

    if not isinstance(rights_payload.get("media", []), list):
        errors.append("rights.json media must be a list")

    return errors


def load_package(package_dir: str | Path) -> SocialPackage:
    root = Path(package_dir)
    errors = validate_package_dir(root)
    if errors:
        raise ValueError("; ".join(errors))

    package_payload, article_payload, rights_payload = _load_payloads(root)
    article_data = article_payload["article"]
    rights_media = {
        int(item.get("ordinal") or 0): item for item in rights_payload.get("media", [])
    }
    file_refs = package_payload["files"]
    body_text_path = root / file_refs["body_text"]
    body_text = str(article_data.get("body_text") or "")
    if not body_text and body_text_path.exists():
        body_text = body_text_path.read_text(encoding="utf-8")

    article = Article(
        idxno=int(article_data["idxno"]),
        headline=str(article_data["headline"]),
        summary=str(article_data.get("summary") or ""),
        body_text=body_text,
        section_name=str(article_data.get("section_name") or ""),
        subsection_name=str(article_data.get("subsection_name") or ""),
        author_name=str(article_data.get("author_name") or ""),
        published_at=str(article_data.get("published_at") or ""),
        canonical_url=str(article_data.get("canonical_url") or ""),
        source_url=str(article_data.get("source_url") or ""),
        site_name=str(article_data.get("site_name") or ""),
        language=str(article_data.get("language") or ""),
        browser_title=str(article_data.get("browser_title") or ""),
        change_type=str(article_data.get("change_type") or ""),
        copyright_notice=str(article_data.get("copyright_notice") or ""),
    )
    media_review_required = any(
        bool(item.get("review_required", True)) for item in rights_payload.get("media", [])
    )
    rights = Rights(
        status=str(rights_payload.get("status") or ""),
        transformation_required=bool(
            rights_payload.get("article_text", {}).get("transformation_required", True)
        ),
        notes=list(rights_payload.get("article_text", {}).get("notes", [])),
        music_status=str(rights_payload.get("music", {}).get("status") or ""),
        music_license_required=bool(
            rights_payload.get("music", {}).get("license_required", True)
        ),
        review_required=media_review_required
        or bool(rights_payload.get("music", {}).get("review_required", True)),
    )

    assets = []
    for asset_payload in article_payload.get("assets", []):
        ordinal = int(asset_payload.get("ordinal") or 0)
        rights_payload_for_asset = rights_media.get(ordinal, {})
        assets.append(
            ArticleAsset(
                ordinal=ordinal,
                role=str(asset_payload.get("role") or ""),
                source_url=str(asset_payload.get("source_url") or ""),
                packaged_path=str(asset_payload.get("packaged_path") or ""),
                mime_type=str(asset_payload.get("mime_type") or ""),
                width=asset_payload.get("width"),
                height=asset_payload.get("height"),
                alt_text=str(asset_payload.get("alt_text") or ""),
                caption=str(asset_payload.get("caption") or ""),
                sha256=str(asset_payload.get("sha256") or ""),
                social_use_allowed=bool(
                    rights_payload_for_asset.get("social_use_allowed", False)
                ),
                credit_text=str(rights_payload_for_asset.get("credit_text") or ""),
                review_required=bool(rights_payload_for_asset.get("review_required", True)),
                license_type=str(rights_payload_for_asset.get("license_type") or "unknown"),
            )
        )

    platforms = {
        name: PlatformTarget(
            builder=str(payload.get("builder") or ""),
            publisher=str(payload.get("publisher") or ""),
            content_kind=str(payload.get("content_kind") or ""),
            delivery_mode=str(payload.get("delivery_mode") or ""),
            review_required=bool(payload.get("review_required", True)),
            status=str(payload.get("status") or ""),
            status_batch_path=str(payload.get("status_paths", {}).get("batch") or ""),
            status_article_path=str(payload.get("status_paths", {}).get("article") or ""),
        )
        for name, payload in package_payload.get("platforms", {}).items()
    }
    assets_dir = root / str(package_payload.get("assets", {}).get("directory") or "assets")
    return SocialPackage(
        schema_version=int(package_payload["schema_version"]),
        export_kind=str(package_payload["export_kind"]),
        exported_at=package_payload["exported_at"],
        package_dir=root,
        run=_as_run_info(package_payload["run"]),
        article=article,
        rights=rights,
        files=PackageFileRefs(
            article_json=str(file_refs["article_json"]),
            article_xml=str(file_refs["article_xml"]),
            source_html=str(file_refs["source_html"]),
            body_text=str(file_refs["body_text"]),
            rights=str(file_refs["rights"]),
        ),
        assets_dir=assets_dir,
        assets=assets,
        platforms=platforms,
        status_contract=dict(package_payload.get("status_contract", {})),
    )


def validate_batch_dir(batch_dir: str | Path) -> list[str]:
    root = Path(batch_dir)
    errors: list[str] = []

    if not root.exists():
        return [f"Batch directory does not exist: {root}"]
    if not root.is_dir():
        return [f"Batch path is not a directory: {root}"]

    batch_manifest = root / "batch.json"
    if not batch_manifest.exists():
        return ["Missing required file: batch.json"]

    try:
        batch_payload = _read_json(batch_manifest)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    missing_fields = _missing_fields(batch_payload, BATCH_REQUIRED_FIELDS)
    if missing_fields:
        errors.append(f"batch.json missing fields: {', '.join(missing_fields)}")
        return errors

    packages = batch_payload.get("packages")
    if not isinstance(packages, list):
        return ["batch.json packages must be a list"]

    if int(batch_payload.get("article_count") or 0) != len(packages):
        errors.append("batch.json article_count does not match packages length")

    for package_ref in packages:
        package_dir_rel = package_ref.get("package_dir")
        if not package_dir_rel:
            errors.append("batch.json package entry missing package_dir")
            continue
        package_path = root / str(package_dir_rel)
        if not package_path.exists():
            errors.append(f"Missing package directory from batch manifest: {package_dir_rel}")
            continue
        errors.extend(validate_package_dir(package_path))

    return errors


def load_batch(batch_dir: str | Path) -> SocialBatch:
    root = Path(batch_dir)
    errors = validate_batch_dir(root)
    if errors:
        raise ValueError("; ".join(errors))

    payload = _read_json(root / "batch.json")
    package_refs = [
        BatchPackageRef(
            article_idxno=int(item.get("article_idxno") or 0),
            headline=str(item.get("headline") or ""),
            change_type=str(item.get("change_type") or ""),
            package_dir=str(item.get("package_dir") or ""),
            package_path=str(item.get("package_path") or ""),
            article_json_path=str(item.get("article_json_path") or ""),
            rights_path=str(item.get("rights_path") or ""),
            asset_count=int(item.get("asset_count") or 0),
        )
        for item in payload.get("packages", [])
    ]
    return SocialBatch(
        schema_version=int(payload["schema_version"]),
        export_kind=str(payload["export_kind"]),
        exported_at=str(payload["exported_at"]),
        relative_dir=str(payload["relative_dir"]),
        batch_dir=root,
        batch_manifest_path=root / "batch.json",
        run=_as_run_info(payload["run"]),
        article_count=int(payload["article_count"]),
        packages=package_refs,
        status_contract=dict(payload.get("status_contract", {})),
    )


def validate_notification_file(
    notification_path: str | Path,
    inbox_root: str | Path | None = None,
) -> list[str]:
    path = Path(notification_path)
    if not path.exists():
        return [f"Notification file does not exist: {path}"]
    if not path.is_file():
        return [f"Notification path is not a file: {path}"]

    try:
        payload = _read_json(path)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    errors: list[str] = []
    missing_fields = _missing_fields(payload, NOTIFICATION_REQUIRED_FIELDS)
    if missing_fields:
        errors.append(f"notification missing fields: {', '.join(missing_fields)}")
        return errors

    if not isinstance(payload.get("publisher_targets"), list):
        errors.append("notification publisher_targets must be a list")
    if not isinstance(payload.get("packages"), list):
        errors.append("notification packages must be a list")

    if errors:
        return errors

    if inbox_root is not None:
        notification = load_notification(path)
        batch_dir = resolve_batch_dir(notification, inbox_root)
        errors.extend(validate_batch_dir(batch_dir))
    return errors


def load_notification(notification_path: str | Path) -> SocialNotification:
    path = Path(notification_path)
    errors = validate_notification_file(path)
    if errors:
        raise ValueError("; ".join(errors))

    payload = _read_json(path)
    package_refs = [
        NotificationPackageRef(
            article_idxno=int(item.get("article_idxno") or 0),
            headline=str(item.get("headline") or ""),
            change_type=str(item.get("change_type") or ""),
            package_dir=str(item.get("package_dir") or ""),
        )
        for item in payload.get("packages", [])
    ]
    return SocialNotification(
        schema_version=int(payload["schema_version"]),
        event_kind=str(payload["event_kind"]),
        exported_at=str(payload["exported_at"]),
        relative_dir=str(payload["relative_dir"]),
        batch_manifest=str(payload["batch_manifest"]),
        article_count=int(payload["article_count"]),
        review_required=bool(payload["review_required"]),
        run=_as_run_info(payload["run"]),
        publisher_targets=list(payload.get("publisher_targets", [])),
        packages=package_refs,
        notification_path=path,
        status_contract=dict(payload.get("status_contract", {})),
    )


def resolve_batch_dir(notification: SocialNotification, inbox_root: str | Path) -> Path:
    return Path(inbox_root) / notification.relative_dir


def load_batch_from_notification(
    notification_path: str | Path,
    inbox_root: str | Path,
) -> SocialBatch:
    notification = load_notification(notification_path)
    batch_dir = resolve_batch_dir(notification, inbox_root)
    return load_batch(batch_dir)
