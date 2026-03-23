from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib import error, request

from .prompt_templates import render_prompt_template
from .settings import Settings


def _utcnow_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _operation_label(operation: str) -> str:
    return {
        "build_review_all": "review draft build",
        "queue_publish_requests": "publish request queue",
    }.get(operation, operation)


def _result_line(operation: str, summary: dict) -> str:
    if operation == "build_review_all":
        return (
            f"{summary.get('platform_count', 0)}개 플랫폼, "
            f"{summary.get('source_relative_dir', 'unknown batch')} review 산출물 생성"
        )
    if operation == "queue_publish_requests":
        return (
            f"{summary.get('request_count', 0)}건 발행 요청 큐잉 "
            f"({summary.get('platform', 'unknown platform')})"
        )
    return f"요약 데이터: {summary.get('schema_version', 1)}"


def build_operation_message(operation: str, summary: dict) -> str:
    return render_prompt_template(
        "notifiers/operation_summary.txt",
        operation_label=_operation_label(operation),
        relative_dir=summary.get("source_relative_dir", "unknown"),
        platform_label=summary.get("platform", "all"),
        result_line=_result_line(operation, summary),
        review_count=summary.get("article_count", 0),
        request_count=summary.get("request_count", 0),
        generated_at=_utcnow_seconds(),
    )


def _post_json(url: str, payload: dict) -> int:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=10) as response:
        response.read()
        return getattr(response, "status", response.getcode())


def notify_operation_result(operation: str, summary: dict, settings: Settings) -> dict:
    message = build_operation_message(operation, summary)
    targets = []
    configured_targets = [
        ("teams", settings.notify_teams_webhook_url),
        ("slack", settings.notify_slack_webhook_url),
    ]
    for channel, url in configured_targets:
        if not url:
            continue
        try:
            status_code = _post_json(url, {"text": message})
            targets.append(
                {
                    "channel": channel,
                    "status": "sent",
                    "status_code": status_code,
                }
            )
        except (OSError, ValueError, error.URLError) as exc:
            targets.append(
                {
                    "channel": channel,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return {
        "notification_kind": "mnl/social-operation-notification",
        "operation": operation,
        "message": message,
        "target_count": len(targets),
        "sent_count": len([target for target in targets if target["status"] == "sent"]),
        "failed_count": len([target for target in targets if target["status"] == "failed"]),
        "targets": targets,
        "status": "not_configured" if not targets and not any(url for _, url in configured_targets) else "completed",
    }
