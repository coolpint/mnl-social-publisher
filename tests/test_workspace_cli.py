import unittest
from unittest.mock import patch

from mnl_social_publisher import cli
from mnl_social_publisher.models import BatchPackageRef, RunInfo, SocialBatch


class FakeWorkspace:
    def __init__(self) -> None:
        self.last_build_relative_dir = ""
        self.last_publish_relative_dir = ""
        self.last_publish_platform = ""

    def describe_roots(self):
        return [("Mode", "fake"), ("Inbox", "social/inbox")]

    def list_recent_batches(self, limit: int = 10):
        return [
            SocialBatch(
                schema_version=1,
                export_kind="mnl/social-export-batch",
                exported_at="2026-03-22T00:00:00+00:00",
                relative_dir="2026/03/22/run-000321",
                batch_dir=None,  # type: ignore[arg-type]
                batch_manifest_path=None,  # type: ignore[arg-type]
                run=RunInfo(id=321),
                article_count=1,
                packages=[
                    BatchPackageRef(
                        article_idxno=1,
                        headline="headline",
                        change_type="created",
                        package_dir="article-000001",
                    )
                ],
            )
        ][:limit]

    def build_review_all(self, relative_dir: str):
        self.last_build_relative_dir = relative_dir
        return {
            "schema_version": 1,
            "build_kind": "mnl/all-platform-review-batch",
            "source_relative_dir": relative_dir,
            "platform_count": 5,
        }

    def create_publish_requests(self, relative_dir: str, platform: str):
        self.last_publish_relative_dir = relative_dir
        self.last_publish_platform = platform
        return {
            "schema_version": 1,
            "request_batch_kind": f"mnl/{platform}-request-batch",
            "source_relative_dir": relative_dir,
            "platform": platform,
            "request_count": 1,
        }


class WorkspaceCliTestCase(unittest.TestCase):
    def test_workspace_list_batches_uses_workspace(self) -> None:
        workspace = FakeWorkspace()
        with patch("mnl_social_publisher.cli.workspace_from_settings", return_value=workspace), patch(
            "builtins.print"
        ) as mocked_print:
            exit_code = cli.main(["workspace-list-batches", "--limit", "1", "--pretty"])

        self.assertEqual(exit_code, 0)
        rendered = mocked_print.call_args[0][0]
        self.assertIn("2026/03/22/run-000321", rendered)
        self.assertIn("social/inbox", rendered)

    def test_workspace_build_review_all_defaults_to_latest_batch(self) -> None:
        workspace = FakeWorkspace()
        with patch("mnl_social_publisher.cli.workspace_from_settings", return_value=workspace), patch(
            "builtins.print"
        ):
            exit_code = cli.main(["workspace-build-review-all", "--pretty"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(workspace.last_build_relative_dir, "2026/03/22/run-000321")

    def test_workspace_build_review_all_can_notify(self) -> None:
        workspace = FakeWorkspace()
        with patch("mnl_social_publisher.cli.workspace_from_settings", return_value=workspace), patch(
            "mnl_social_publisher.cli.notify_operation_result",
            return_value={"status": "completed", "sent_count": 1},
        ) as mocked_notify, patch("builtins.print"):
            exit_code = cli.main(["workspace-build-review-all", "--notify", "--pretty"])

        self.assertEqual(exit_code, 0)
        mocked_notify.assert_called_once()

    def test_workspace_create_publish_requests_defaults_to_latest_batch(self) -> None:
        workspace = FakeWorkspace()
        with patch("mnl_social_publisher.cli.workspace_from_settings", return_value=workspace), patch(
            "builtins.print"
        ):
            exit_code = cli.main(["workspace-create-publish-requests", "threads", "--pretty"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(workspace.last_publish_relative_dir, "2026/03/22/run-000321")
        self.assertEqual(workspace.last_publish_platform, "threads")

    def test_workspace_create_publish_requests_can_notify(self) -> None:
        workspace = FakeWorkspace()
        with patch("mnl_social_publisher.cli.workspace_from_settings", return_value=workspace), patch(
            "mnl_social_publisher.cli.notify_operation_result",
            return_value={"status": "completed", "sent_count": 1},
        ) as mocked_notify, patch("builtins.print"):
            exit_code = cli.main(
                ["workspace-create-publish-requests", "threads", "--notify", "--pretty"]
            )

        self.assertEqual(exit_code, 0)
        mocked_notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
