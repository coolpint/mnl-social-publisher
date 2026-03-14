from __future__ import annotations

from .models import PlatformTarget, SocialPackage


DEFAULT_PLATFORM_TARGETS = {
    "youtube_shorts": PlatformTarget(
        builder="youtube_shorts_builder",
        publisher="youtube_publisher",
        content_kind="vertical_video",
        delivery_mode="private_review",
        review_required=True,
        status="pending",
        status_batch_path="",
        status_article_path="",
    ),
    "threads": PlatformTarget(
        builder="threads_builder",
        publisher="threads_publisher",
        content_kind="text_first",
        delivery_mode="review_required",
        review_required=True,
        status="pending",
        status_batch_path="",
        status_article_path="",
    ),
    "x": PlatformTarget(
        builder="x_builder",
        publisher="x_publisher",
        content_kind="text_first",
        delivery_mode="review_required",
        review_required=True,
        status="pending",
        status_batch_path="",
        status_article_path="",
    ),
    "facebook": PlatformTarget(
        builder="facebook_builder",
        publisher="facebook_publisher",
        content_kind="platform_specific",
        delivery_mode="review_required",
        review_required=True,
        status="pending",
        status_batch_path="",
        status_article_path="",
    ),
    "instagram": PlatformTarget(
        builder="instagram_builder",
        publisher="instagram_publisher",
        content_kind="platform_specific",
        delivery_mode="review_required",
        review_required=True,
        status="pending",
        status_batch_path="",
        status_article_path="",
    ),
}

REVIEW_DRAFT_FILENAMES = {
    "youtube_shorts": "youtube_draft.json",
    "threads": "threads_draft.json",
    "x": "x_draft.json",
    "facebook": "facebook_draft.json",
    "instagram": "instagram_draft.json",
}

REVIEW_BUILD_FILENAMES = {
    "youtube_shorts": "youtube_build.json",
    "threads": "threads_build.json",
    "x": "x_build.json",
    "facebook": "facebook_build.json",
    "instagram": "instagram_build.json",
}


def supported_platforms() -> list[str]:
    return list(DEFAULT_PLATFORM_TARGETS.keys())


def review_draft_filename(platform: str) -> str:
    return REVIEW_DRAFT_FILENAMES[platform]


def review_build_filename(platform: str) -> str:
    return REVIEW_BUILD_FILENAMES[platform]


def get_platform_target(package: SocialPackage, platform: str) -> PlatformTarget:
    return package.platforms.get(platform, DEFAULT_PLATFORM_TARGETS[platform])
