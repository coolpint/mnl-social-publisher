from __future__ import annotations

from ..models import PublishJob, PublishRequest


def build_youtube_publish_request(
    draft: dict,
    job: PublishJob,
    created_at: str,
) -> PublishRequest:
    payload = {
        "title": draft["title"],
        "description": draft["description"],
        "privacy_status": draft["privacy_status"],
        "tags": draft["tags"],
        "script_lines": draft["script_lines"],
        "scenes": draft.get("scenes", []),
        "total_duration_seconds": draft.get("total_duration_seconds", 0),
        "thumbnail": {
            "headline": draft.get("thumbnail_headline", ""),
            "subheadline": draft.get("thumbnail_subheadline", ""),
        },
        "prompt_templates": {
            "script": draft.get("script_prompt_template", ""),
            "description": draft.get("description_prompt_template", ""),
        },
        "profile": {
            "id": draft.get("profile_id", ""),
            "version": draft.get("profile_version", 0),
        },
        "visuals_mode": draft["visuals_mode"],
        "approved_asset_paths": draft["approved_asset_paths"],
    }
    return PublishRequest(
        schema_version=1,
        request_kind="mnl/youtube-publish-request",
        platform="youtube_shorts",
        package_id=job.package_id,
        article_idxno=job.article_idxno,
        headline=job.headline,
        publisher=job.publisher,
        delivery_mode=job.delivery_mode,
        created_at=created_at,
        review_draft_path=job.review_draft_path,
        approval_path=job.approval_path,
        source_canonical_url=job.source_canonical_url,
        payload=payload,
    )
