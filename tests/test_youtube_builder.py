from pathlib import Path
import tempfile
import unittest

from mnl_social_publisher.builders.youtube import build_youtube_draft
from mnl_social_publisher.package_loader import load_batch, load_package
from mnl_social_publisher.review_builds import build_youtube_review_batch


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


class YouTubeBuilderTestCase(unittest.TestCase):
    def test_build_youtube_draft_uses_private_review_flow(self) -> None:
        package = load_package(FIXTURE_PACKAGE_DIR)

        draft = build_youtube_draft(package)

        self.assertEqual(draft.privacy_status, "private")
        self.assertTrue(draft.review_required)
        self.assertEqual(draft.visuals_mode, "brand_kinetic_typography")
        self.assertEqual(draft.delivery_mode, "private_review")
        self.assertEqual(draft.builder, "youtube_shorts_builder")
        self.assertEqual(draft.publisher, "youtube_publisher")
        self.assertEqual(draft.approved_asset_paths, [])
        self.assertEqual(draft.blocked_asset_paths, ["assets/source-media/01.jpg"])
        self.assertTrue(draft.script_lines[0].startswith("플랫폼 규제 점검 강화"))
        self.assertIn("머니앤로", draft.tags)

    def test_build_youtube_review_batch_writes_review_outputs(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = build_youtube_review_batch(batch, output_root=tmp_dir, pretty=True)

            output_root = Path(tmp_dir) / "2026" / "03" / "14" / "run-000123"
            draft_path = output_root / "article-000143" / "youtube_draft.json"
            summary_path = output_root / "youtube_build.json"

            self.assertTrue(draft_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertEqual(summary["article_count"], 1)
            self.assertEqual(summary["drafts"][0]["status"], "built")
            self.assertEqual(
                summary["drafts"][0]["output_path"],
                "2026/03/14/run-000123/article-000143/youtube_draft.json",
            )


if __name__ == "__main__":
    unittest.main()
