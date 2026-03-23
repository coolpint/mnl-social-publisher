import unittest
from unittest.mock import patch

from mnl_social_publisher.notifiers import build_operation_message, notify_operation_result
from mnl_social_publisher.settings import Settings


class NotifierTestCase(unittest.TestCase):
    def test_build_operation_message_renders_summary_text(self) -> None:
        message = build_operation_message(
            "build_review_all",
            {
                "source_relative_dir": "2026/03/22/run-000321",
                "platform_count": 5,
                "article_count": 2,
            },
        )

        self.assertIn("review draft build", message)
        self.assertIn("2026/03/22/run-000321", message)
        self.assertIn("5개 플랫폼", message)

    def test_notify_operation_result_posts_to_configured_targets(self) -> None:
        settings = Settings(
            notify_teams_webhook_url="https://example.com/teams",
            notify_slack_webhook_url="https://example.com/slack",
        )

        class Response:
            status = 200

            def read(self):
                return b"ok"

            def getcode(self):
                return 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("mnl_social_publisher.notifiers.request.urlopen", return_value=Response()) as mocked:
            summary = notify_operation_result(
                "queue_publish_requests",
                {
                    "source_relative_dir": "2026/03/22/run-000321",
                    "platform": "threads",
                    "request_count": 3,
                },
                settings,
            )

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(summary["sent_count"], 2)
        self.assertEqual(summary["failed_count"], 0)

    def test_notify_operation_result_returns_not_configured_when_disabled(self) -> None:
        summary = notify_operation_result(
            "build_review_all",
            {"source_relative_dir": "2026/03/22/run-000321", "platform_count": 5},
            Settings(),
        )

        self.assertEqual(summary["status"], "not_configured")
        self.assertEqual(summary["target_count"], 0)


if __name__ == "__main__":
    unittest.main()
