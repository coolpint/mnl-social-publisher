from __future__ import annotations

import argparse
import json
from pathlib import Path

from .approval_loader import validate_approval_file
from .builders.registry import get_platform_builder
from .builders.youtube import build_youtube_draft
from .notifiers import notify_operation_result
from .package_loader import (
    load_batch,
    load_batch_from_notification,
    load_notification,
    load_package,
    validate_batch_dir,
    validate_notification_file,
    validate_package_dir,
)
from .platforms import supported_platforms
from .publishers.requests import create_publish_requests
from .publishers.status import prepare_publish_batch
from .review_builds import build_review_all_batch, build_review_batch, build_youtube_review_batch
from .settings import Settings
from .web_app import serve_web_app
from .workspace import workspace_from_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mnl-social-publisher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-package")
    validate_parser.add_argument("package_dir", type=Path)

    validate_batch_parser = subparsers.add_parser("validate-batch")
    validate_batch_parser.add_argument("batch_dir", type=Path)

    validate_notification_parser = subparsers.add_parser("validate-notification")
    validate_notification_parser.add_argument("notification_path", type=Path)
    validate_notification_parser.add_argument("--inbox-root", type=Path)

    validate_approval_parser = subparsers.add_parser("validate-approval")
    validate_approval_parser.add_argument("approval_path", type=Path)

    serve_web_parser = subparsers.add_parser("serve-web")
    serve_web_parser.add_argument("--host", default="127.0.0.1")
    serve_web_parser.add_argument("--port", type=int, default=8420)

    workspace_list_parser = subparsers.add_parser("workspace-list-batches")
    workspace_list_parser.add_argument("--limit", type=int, default=10)
    workspace_list_parser.add_argument("--pretty", action="store_true")

    workspace_build_review_parser = subparsers.add_parser("workspace-build-review-all")
    workspace_build_review_parser.add_argument("--relative-dir")
    workspace_build_review_parser.add_argument("--latest", action="store_true")
    workspace_build_review_parser.add_argument("--notify", action="store_true")
    workspace_build_review_parser.add_argument("--pretty", action="store_true")

    workspace_publish_parser = subparsers.add_parser("workspace-create-publish-requests")
    workspace_publish_parser.add_argument("platform", choices=supported_platforms())
    workspace_publish_parser.add_argument("--relative-dir")
    workspace_publish_parser.add_argument("--latest", action="store_true")
    workspace_publish_parser.add_argument("--notify", action="store_true")
    workspace_publish_parser.add_argument("--pretty", action="store_true")

    youtube_parser = subparsers.add_parser("build-youtube")
    youtube_parser.add_argument("package_dir", type=Path)
    youtube_parser.add_argument("--output", type=Path)
    youtube_parser.add_argument("--pretty", action="store_true")

    youtube_batch_parser = subparsers.add_parser("build-youtube-batch")
    youtube_batch_parser.add_argument("batch_dir", type=Path)
    youtube_batch_parser.add_argument("--output-root", type=Path)
    youtube_batch_parser.add_argument("--pretty", action="store_true")

    youtube_notification_parser = subparsers.add_parser("build-youtube-notification")
    youtube_notification_parser.add_argument("notification_path", type=Path)
    youtube_notification_parser.add_argument("--inbox-root", type=Path)
    youtube_notification_parser.add_argument("--output-root", type=Path)
    youtube_notification_parser.add_argument("--pretty", action="store_true")

    build_platform_parser = subparsers.add_parser("build-platform")
    build_platform_parser.add_argument("platform", choices=supported_platforms())
    build_platform_parser.add_argument("package_dir", type=Path)
    build_platform_parser.add_argument("--output", type=Path)
    build_platform_parser.add_argument("--pretty", action="store_true")

    build_review_batch_parser = subparsers.add_parser("build-review-batch")
    build_review_batch_parser.add_argument("platform", choices=supported_platforms())
    build_review_batch_parser.add_argument("batch_dir", type=Path)
    build_review_batch_parser.add_argument("--output-root", type=Path)
    build_review_batch_parser.add_argument("--pretty", action="store_true")

    build_review_notification_parser = subparsers.add_parser("build-review-notification")
    build_review_notification_parser.add_argument("platform", choices=supported_platforms())
    build_review_notification_parser.add_argument("notification_path", type=Path)
    build_review_notification_parser.add_argument("--inbox-root", type=Path)
    build_review_notification_parser.add_argument("--output-root", type=Path)
    build_review_notification_parser.add_argument("--pretty", action="store_true")

    build_review_all_batch_parser = subparsers.add_parser("build-review-all-batch")
    build_review_all_batch_parser.add_argument("batch_dir", type=Path)
    build_review_all_batch_parser.add_argument("--output-root", type=Path)
    build_review_all_batch_parser.add_argument("--pretty", action="store_true")

    build_review_all_notification_parser = subparsers.add_parser("build-review-all-notification")
    build_review_all_notification_parser.add_argument("notification_path", type=Path)
    build_review_all_notification_parser.add_argument("--inbox-root", type=Path)
    build_review_all_notification_parser.add_argument("--output-root", type=Path)
    build_review_all_notification_parser.add_argument("--pretty", action="store_true")

    prepare_publish_batch_parser = subparsers.add_parser("prepare-publish-batch")
    prepare_publish_batch_parser.add_argument("platform", choices=supported_platforms())
    prepare_publish_batch_parser.add_argument("batch_dir", type=Path)
    prepare_publish_batch_parser.add_argument("--review-root", type=Path)
    prepare_publish_batch_parser.add_argument("--approval-root", type=Path)
    prepare_publish_batch_parser.add_argument("--status-root", type=Path)
    prepare_publish_batch_parser.add_argument("--pretty", action="store_true")

    prepare_publish_notification_parser = subparsers.add_parser("prepare-publish-notification")
    prepare_publish_notification_parser.add_argument("platform", choices=supported_platforms())
    prepare_publish_notification_parser.add_argument("notification_path", type=Path)
    prepare_publish_notification_parser.add_argument("--inbox-root", type=Path)
    prepare_publish_notification_parser.add_argument("--review-root", type=Path)
    prepare_publish_notification_parser.add_argument("--approval-root", type=Path)
    prepare_publish_notification_parser.add_argument("--status-root", type=Path)
    prepare_publish_notification_parser.add_argument("--pretty", action="store_true")

    publish_requests_batch_parser = subparsers.add_parser("create-publish-requests-batch")
    publish_requests_batch_parser.add_argument("platform", choices=supported_platforms())
    publish_requests_batch_parser.add_argument("batch_dir", type=Path)
    publish_requests_batch_parser.add_argument("--review-root", type=Path)
    publish_requests_batch_parser.add_argument("--approval-root", type=Path)
    publish_requests_batch_parser.add_argument("--outbox-root", type=Path)
    publish_requests_batch_parser.add_argument("--status-root", type=Path)
    publish_requests_batch_parser.add_argument("--pretty", action="store_true")

    publish_requests_notification_parser = subparsers.add_parser("create-publish-requests-notification")
    publish_requests_notification_parser.add_argument("platform", choices=supported_platforms())
    publish_requests_notification_parser.add_argument("notification_path", type=Path)
    publish_requests_notification_parser.add_argument("--inbox-root", type=Path)
    publish_requests_notification_parser.add_argument("--review-root", type=Path)
    publish_requests_notification_parser.add_argument("--approval-root", type=Path)
    publish_requests_notification_parser.add_argument("--outbox-root", type=Path)
    publish_requests_notification_parser.add_argument("--status-root", type=Path)
    publish_requests_notification_parser.add_argument("--pretty", action="store_true")

    build_all_parser = subparsers.add_parser("build-all")
    build_all_parser.add_argument("package_dir", type=Path)
    build_all_parser.add_argument("--output-dir", type=Path)
    build_all_parser.add_argument("--pretty", action="store_true")

    return parser


def _dump_json(payload: dict, pretty: bool) -> str:
    if pretty:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return json.dumps(payload, ensure_ascii=False)


def _write_or_print(payload: dict, output_path: Path | None, pretty: bool) -> None:
    rendered = _dump_json(payload, pretty=pretty)
    if output_path is None:
        print(rendered)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")


def _resolve_workspace_relative_dir(workspace, requested_relative_dir: str | None, latest: bool) -> str:
    relative_dir = "" if latest else (requested_relative_dir or "").strip()
    if relative_dir:
        return relative_dir

    batches = workspace.list_recent_batches(limit=1)
    if not batches:
        raise ValueError("No batches are available in the configured workspace")
    return batches[0].relative_dir


def _workspace_roots_payload(workspace) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in workspace.describe_roots()]


def main(argv: list[str] | None = None) -> int:
    settings = Settings.from_env()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-package":
        errors = validate_package_dir(args.package_dir)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("Package is valid")
        return 0

    if args.command == "validate-batch":
        errors = validate_batch_dir(args.batch_dir)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("Batch is valid")
        return 0

    if args.command == "validate-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        errors = validate_notification_file(args.notification_path, inbox_root=inbox_root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("Notification is valid")
        return 0

    if args.command == "validate-approval":
        errors = validate_approval_file(args.approval_path)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("Approval is valid")
        return 0

    if args.command == "serve-web":
        serve_web_app(settings, host=args.host, port=args.port)
        return 0

    if args.command == "workspace-list-batches":
        workspace = workspace_from_settings(settings)
        payload = {
            "schema_version": 1,
            "workspace_kind": settings.storage_backend,
            "roots": _workspace_roots_payload(workspace),
            "batch_count": 0,
            "batches": [],
        }
        for batch in workspace.list_recent_batches(limit=args.limit):
            payload["batches"].append(
                {
                    "relative_dir": batch.relative_dir,
                    "run_id": batch.run.id,
                    "article_count": batch.article_count,
                    "exported_at": batch.exported_at,
                }
            )
        payload["batch_count"] = len(payload["batches"])
        print(_dump_json(payload, pretty=args.pretty))
        return 0

    if args.command == "workspace-build-review-all":
        workspace = workspace_from_settings(settings)
        relative_dir = _resolve_workspace_relative_dir(workspace, args.relative_dir, args.latest)
        summary = workspace.build_review_all(relative_dir)
        summary["roots"] = _workspace_roots_payload(workspace)
        if args.notify:
            summary["notification"] = notify_operation_result("build_review_all", summary, settings)
        print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "workspace-create-publish-requests":
        workspace = workspace_from_settings(settings)
        relative_dir = _resolve_workspace_relative_dir(workspace, args.relative_dir, args.latest)
        summary = workspace.create_publish_requests(relative_dir, args.platform)
        summary["roots"] = _workspace_roots_payload(workspace)
        if args.notify:
            summary["notification"] = notify_operation_result(
                "queue_publish_requests",
                summary,
                settings,
            )
        print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-youtube":
        package = load_package(args.package_dir)
        draft = build_youtube_draft(package)
        _write_or_print(draft.to_dict(), args.output, pretty=args.pretty)
        return 0

    if args.command == "build-platform":
        package = load_package(args.package_dir)
        draft = get_platform_builder(args.platform)(package)
        _write_or_print(draft.to_dict(), args.output, pretty=args.pretty)
        return 0

    if args.command == "build-youtube-batch":
        batch = load_batch(args.batch_dir)
        summary = build_youtube_review_batch(
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-review-batch":
        batch = load_batch(args.batch_dir)
        summary = build_review_batch(
            args.platform,
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-review-all-batch":
        batch = load_batch(args.batch_dir)
        summary = build_review_all_batch(
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-youtube-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        if inbox_root is None:
            print("build-youtube-notification requires --inbox-root or MNL_SOCIAL_INBOX_ROOT")
            return 2
        notification = load_notification(args.notification_path)
        batch = load_batch_from_notification(args.notification_path, inbox_root)
        summary = build_youtube_review_batch(
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
            source_notification=notification,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-review-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        if inbox_root is None:
            print("build-review-notification requires --inbox-root or MNL_SOCIAL_INBOX_ROOT")
            return 2
        notification = load_notification(args.notification_path)
        batch = load_batch_from_notification(args.notification_path, inbox_root)
        summary = build_review_batch(
            args.platform,
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
            source_notification=notification,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-review-all-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        if inbox_root is None:
            print("build-review-all-notification requires --inbox-root or MNL_SOCIAL_INBOX_ROOT")
            return 2
        notification = load_notification(args.notification_path)
        batch = load_batch_from_notification(args.notification_path, inbox_root)
        summary = build_review_all_batch(
            batch,
            output_root=args.output_root or settings.review_root,
            pretty=args.pretty,
            source_notification=notification,
        )
        if args.output_root is None and settings.review_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "prepare-publish-batch":
        review_root = args.review_root or settings.review_root
        approval_root = args.approval_root or settings.approval_root
        status_root = args.status_root or settings.status_root
        if review_root is None:
            print("prepare-publish-batch requires --review-root or MNL_SOCIAL_REVIEW_ROOT")
            return 2
        batch = load_batch(args.batch_dir)
        summary = prepare_publish_batch(
            args.platform,
            batch,
            review_root=review_root,
            approval_root=approval_root,
            status_root=status_root,
            pretty=args.pretty,
        )
        if status_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "prepare-publish-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        review_root = args.review_root or settings.review_root
        approval_root = args.approval_root or settings.approval_root
        status_root = args.status_root or settings.status_root
        if inbox_root is None:
            print("prepare-publish-notification requires --inbox-root or MNL_SOCIAL_INBOX_ROOT")
            return 2
        if review_root is None:
            print("prepare-publish-notification requires --review-root or MNL_SOCIAL_REVIEW_ROOT")
            return 2
        notification = load_notification(args.notification_path)
        batch = load_batch_from_notification(args.notification_path, inbox_root)
        summary = prepare_publish_batch(
            args.platform,
            batch,
            review_root=review_root,
            approval_root=approval_root,
            status_root=status_root,
            pretty=args.pretty,
            source_notification=notification,
        )
        if status_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "create-publish-requests-batch":
        review_root = args.review_root or settings.review_root
        approval_root = args.approval_root or settings.approval_root
        outbox_root = args.outbox_root or settings.outbox_root
        status_root = args.status_root or settings.status_root
        if review_root is None:
            print("create-publish-requests-batch requires --review-root or MNL_SOCIAL_REVIEW_ROOT")
            return 2
        batch = load_batch(args.batch_dir)
        summary = create_publish_requests(
            args.platform,
            batch,
            review_root=review_root,
            approval_root=approval_root,
            outbox_root=outbox_root,
            status_root=status_root,
            pretty=args.pretty,
        )
        if outbox_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "create-publish-requests-notification":
        inbox_root = args.inbox_root or settings.inbox_root
        review_root = args.review_root or settings.review_root
        approval_root = args.approval_root or settings.approval_root
        outbox_root = args.outbox_root or settings.outbox_root
        status_root = args.status_root or settings.status_root
        if inbox_root is None:
            print("create-publish-requests-notification requires --inbox-root or MNL_SOCIAL_INBOX_ROOT")
            return 2
        if review_root is None:
            print("create-publish-requests-notification requires --review-root or MNL_SOCIAL_REVIEW_ROOT")
            return 2
        notification = load_notification(args.notification_path)
        batch = load_batch_from_notification(args.notification_path, inbox_root)
        summary = create_publish_requests(
            args.platform,
            batch,
            review_root=review_root,
            approval_root=approval_root,
            outbox_root=outbox_root,
            status_root=status_root,
            pretty=args.pretty,
            source_notification=notification,
        )
        if outbox_root is None:
            print(_dump_json(summary, pretty=args.pretty))
        return 0

    if args.command == "build-all":
        package = load_package(args.package_dir)
        payload = {
            platform: get_platform_builder(platform)(package).to_dict()
            for platform in supported_platforms()
        }
        if args.output_dir is None:
            print(_dump_json(payload, pretty=args.pretty))
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for platform, draft in payload.items():
                filename = f"{platform}_draft.json"
                if platform == "youtube_shorts":
                    filename = "youtube_draft.json"
                _write_or_print(draft, args.output_dir / filename, pretty=args.pretty)
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
