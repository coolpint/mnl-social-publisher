from pathlib import Path
import tempfile
import unittest

from mnl_social_publisher.package_loader import (
    load_batch,
    load_batch_from_notification,
    load_package,
    load_notification,
    resolve_batch_dir,
    validate_batch_dir,
    validate_notification_file,
    validate_package_dir,
)


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
FIXTURE_NOTIFICATION = Path(__file__).parent / "fixtures" / "social_notifications" / "latest.json"
FIXTURE_INBOX_ROOT = Path(__file__).parent / "fixtures" / "social_inbox"


class PackageLoaderTestCase(unittest.TestCase):
    def test_validate_fixture_package(self) -> None:
        self.assertEqual(validate_package_dir(FIXTURE_PACKAGE_DIR), [])

    def test_load_package_reads_core_fields(self) -> None:
        package = load_package(FIXTURE_PACKAGE_DIR)

        self.assertEqual(package.package_id, "article-000143")
        self.assertEqual(package.article.idxno, 143)
        self.assertEqual(package.article.section_name, "정책")
        self.assertEqual(package.run.id, 123)
        self.assertTrue(package.rights.transformation_required)
        self.assertEqual(len(package.assets), 1)
        self.assertFalse(package.assets[0].social_use_allowed)
        self.assertEqual(
            package.platforms["threads"].status_article_path,
            "social/status/threads/2026/03/14/run-000123/article-000143.json",
        )
        self.assertEqual(
            package.status_contract["root_dir"],
            "social/status",
        )

    def test_load_package_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing-package"
            missing.mkdir()

            with self.assertRaises(ValueError):
                load_package(missing)

    def test_validate_fixture_batch(self) -> None:
        self.assertEqual(validate_batch_dir(FIXTURE_BATCH_DIR), [])

    def test_load_batch_reads_manifest(self) -> None:
        batch = load_batch(FIXTURE_BATCH_DIR)

        self.assertEqual(batch.run.id, 123)
        self.assertEqual(batch.article_count, 1)
        self.assertEqual(batch.relative_dir, "2026/03/14/run-000123")
        self.assertEqual(batch.packages[0].package_dir, "article-000143")
        self.assertEqual(batch.status_contract["root_dir"], "social/status")

    def test_validate_fixture_notification(self) -> None:
        self.assertEqual(
            validate_notification_file(FIXTURE_NOTIFICATION, inbox_root=FIXTURE_INBOX_ROOT),
            [],
        )

    def test_notification_resolves_batch(self) -> None:
        notification = load_notification(FIXTURE_NOTIFICATION)
        batch_dir = resolve_batch_dir(notification, FIXTURE_INBOX_ROOT)
        batch = load_batch_from_notification(FIXTURE_NOTIFICATION, FIXTURE_INBOX_ROOT)

        self.assertEqual(batch_dir, FIXTURE_BATCH_DIR)
        self.assertEqual(batch.batch_dir, FIXTURE_BATCH_DIR)
        self.assertEqual(notification.status_contract["root_dir"], "social/status")


if __name__ == "__main__":
    unittest.main()
