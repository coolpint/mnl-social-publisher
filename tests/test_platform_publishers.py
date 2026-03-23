from pathlib import Path
import json
import tempfile
import unittest

from mnl_social_publisher.approval_loader import load_approval, validate_approval_file
from mnl_social_publisher.package_loader import load_batch, load_package
from mnl_social_publisher.platforms import supported_platforms
from mnl_social_publisher.publishers.requests import create_publish_requests
from mnl_social_publisher.publishers.status import prepare_publish_batch
from mnl_social_publisher.review_builds import build_review_batch


FIXTURE_BATCH_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "social_inbox"
    / "2026"
    / "03"
    / "14"
    / "run-000123"
)
FIXTURE_PACKAGE_DIR = FIXTURE_BATCH_DIR / "article-000143"
FIXTURE_APPROVAL_ROOT = Path(__file__).parent / "fixtures" / "social_approval"
FIXTURE_APPROVAL_PATH = (
    FIXTURE_APPROVAL_ROOT / "2026" / "03" / "14" / "run-000123" / "article-000143.json"
)


class PlatformDraftAndPublisherTestCase(unittest.TestCase):
    def test_validate_and_load_approval_fixture(self) -> None:
        self.assertEqual(validate_approval_file(FIXTURE_APPROVAL_PATH), [])
        approval = load_approval(FIXTURE_APPROVAL_PATH)

        self.assertEqual(approval.package_id, "article-000143")
        self.assertTrue(approval.platforms["threads"].approved)
        self.assertFalse(approval.platforms["facebook"].approved)

    def test_build_all_supported_platforms_for_single_package(self) -> None:
        package = load_package(FIXTURE_PACKAGE_DIR)

        payload = {}
        for platform in supported_platforms():
            from mnl_social_publisher.builders.registry import get_platform_builder

            payload[platform] = get_platform_builder(platform)(package).to_dict()

        self.assertIn("threads", payload)
        self.assertIn("x", payload)
        self.assertIn("facebook", payload)
        self.assertIn("instagram", payload)
        self.assertLessEqual(payload["x"]["character_count"], 260)
        self.assertEqual(payload["x"]["publisher"], "x_publisher")
        self.assertEqual(payload["threads"]["publisher"], "threads_publisher")
        self.assertEqual(payload["instagram"]["visual_mode"], "brand_reel_or_card_template_required")
        self.assertEqual(payload["threads"]["prompt_template"], "builders/threads.txt")
        self.assertEqual(payload["x"]["prompt_template"], "builders/x.txt")
        self.assertEqual(payload["facebook"]["prompt_template"], "builders/facebook.txt")
        self.assertEqual(payload["instagram"]["prompt_template"], "builders/instagram.txt")
        self.assertEqual(payload["threads"]["profile_id"], "threads-issue-brief-v1")
        self.assertEqual(payload["x"]["profile_id"], "x-fast-news-v1")
        self.assertEqual(payload["facebook"]["profile_id"], "facebook-explainer-v1")
        self.assertEqual(payload["instagram"]["profile_id"], "instagram-saveable-brief-v1")

    def test_build_review_batch_for_threads_and_x(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as tmp_dir:
            threads_summary = build_review_batch("threads", batch, output_root=tmp_dir, pretty=True)
            x_summary = build_review_batch("x", batch, output_root=tmp_dir, pretty=True)

            output_root = Path(tmp_dir) / "2026" / "03" / "14" / "run-000123"
            self.assertTrue((output_root / "threads_build.json").exists())
            self.assertTrue((output_root / "x_build.json").exists())
            self.assertTrue((output_root / "article-000143" / "threads_draft.json").exists())
            self.assertTrue((output_root / "article-000143" / "threads_post.txt").exists())
            self.assertTrue((output_root / "article-000143" / "x_draft.json").exists())
            self.assertTrue((output_root / "article-000143" / "x_post.txt").exists())
            self.assertEqual(threads_summary["drafts"][0]["status"], "built")
            self.assertEqual(x_summary["drafts"][0]["status"], "built")

    def test_prepare_publish_batch_writes_status_files(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as status_dir:
            build_review_batch("threads", batch, output_root=review_dir, pretty=True)

            summary = prepare_publish_batch(
                "threads",
                batch,
                review_root=review_dir,
                status_root=status_dir,
                pretty=True,
            )

            status_base = (
                Path(status_dir) / "threads" / "2026" / "03" / "14" / "run-000123"
            )
            batch_status_path = status_base / "batch.json"
            article_status_path = status_base / "article-000143.json"
            self.assertTrue(batch_status_path.exists())
            self.assertTrue(article_status_path.exists())
            self.assertEqual(summary["jobs"][0]["status"], "awaiting_review")
            self.assertFalse(summary["jobs"][0]["ready_for_publish"])
            batch_payload = json.loads(batch_status_path.read_text(encoding="utf-8"))
            article_payload = json.loads(article_status_path.read_text(encoding="utf-8"))
            self.assertEqual(batch_payload["status_kind"], "mnl/social-batch-status")
            self.assertEqual(batch_payload["state"], "review_required")
            self.assertEqual(article_payload["status_kind"], "mnl/social-article-status")
            self.assertEqual(article_payload["state"], "review_required")

    def test_prepare_publish_batch_uses_approval_when_present(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as review_dir:
            build_review_batch("threads", batch, output_root=review_dir, pretty=True)
            summary = prepare_publish_batch(
                "threads",
                batch,
                review_root=review_dir,
                approval_root=FIXTURE_APPROVAL_ROOT,
                status_root=None,
                pretty=True,
            )

            self.assertEqual(summary["jobs"][0]["status"], "approved_for_publish")
            self.assertTrue(summary["jobs"][0]["ready_for_publish"])
            self.assertEqual(summary["jobs"][0]["approved_by"], "editor@example.com")

    def test_prepare_publish_batch_flags_missing_review_draft(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as review_dir:
            summary = prepare_publish_batch(
                "facebook",
                batch,
                review_root=review_dir,
                status_root=None,
                pretty=True,
            )

            self.assertEqual(summary["jobs"][0]["status"], "blocked_missing_review_draft")

    def test_create_publish_requests_writes_outbox_for_approved_platform(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            build_review_batch("threads", batch, output_root=review_dir, pretty=True)
            summary = create_publish_requests(
                "threads",
                batch,
                review_root=review_dir,
                approval_root=FIXTURE_APPROVAL_ROOT,
                outbox_root=outbox_dir,
                status_root=status_dir,
                pretty=True,
            )

            outbox_base = Path(outbox_dir) / "threads" / "2026" / "03" / "14" / "run-000123"
            status_base = Path(status_dir) / "threads" / "2026" / "03" / "14" / "run-000123"
            self.assertTrue((outbox_base / "publish_requests.json").exists())
            self.assertTrue((outbox_base / "article-000143.json").exists())
            self.assertTrue((status_base / "batch.json").exists())
            self.assertTrue((status_base / "article-000143.json").exists())
            self.assertEqual(summary["request_count"], 1)
            self.assertEqual(summary["requests"][0]["status"], "queued_in_outbox")
            outbox_payload = json.loads(
                (outbox_base / "article-000143.json").read_text(encoding="utf-8")
            )
            article_status_payload = json.loads(
                (status_base / "article-000143.json").read_text(encoding="utf-8")
            )
            self.assertEqual(outbox_payload["payload"]["profile"]["id"], "threads-issue-brief-v1")
            self.assertEqual(article_status_payload["state"], "publishing")

    def test_create_publish_requests_skips_rejected_platform(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as review_dir:
            build_review_batch("facebook", batch, output_root=review_dir, pretty=True)
            summary = create_publish_requests(
                "facebook",
                batch,
                review_root=review_dir,
                approval_root=FIXTURE_APPROVAL_ROOT,
                outbox_root=None,
                status_root=None,
                pretty=True,
            )

            self.assertEqual(summary["request_count"], 0)


if __name__ == "__main__":
    unittest.main()
