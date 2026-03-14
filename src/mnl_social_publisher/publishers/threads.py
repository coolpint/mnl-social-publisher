from __future__ import annotations

from ..models import PublishJob, PublishRequest


def build_threads_publish_request(
    draft: dict,
    job: PublishJob,
    created_at: str,
) -> PublishRequest:
    payload = {
        "text": draft["text"],
        "hashtags": draft["hashtags"],
        "source_canonical_url": draft["source_canonical_url"],
        "visual_mode": draft["visual_mode"],
        "approved_asset_paths": draft["approved_asset_paths"],
    }
    return PublishRequest(
        schema_version=1,
        request_kind="mnl/threads-publish-request",
        platform="threads",
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
