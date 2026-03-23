import unittest

from mnl_social_publisher.approval_inputs import (
    ApprovalInputError,
    WebFormApprovalInputHandler,
)


class ApprovalInputHandlerTestCase(unittest.TestCase):
    def test_web_form_handler_parses_submission(self) -> None:
        handler = WebFormApprovalInputHandler()

        submission = handler.parse_submission(
            {
                "relative_dir": "2026/03/23/run-000013",
                "package_id": "article-000182",
                "article_idxno": "182",
                "platform": "threads",
                "decision": "approve",
                "decided_by": "editor@example.com",
                "note": "승인 테스트",
            }
        )

        self.assertEqual(submission.relative_dir, "2026/03/23/run-000013")
        self.assertEqual(submission.package_id, "article-000182")
        self.assertEqual(submission.article_idxno, 182)
        self.assertTrue(submission.approved)
        self.assertEqual(submission.input_method, "web_form")

    def test_web_form_handler_rejects_invalid_decision(self) -> None:
        handler = WebFormApprovalInputHandler()

        with self.assertRaises(ApprovalInputError):
            handler.parse_submission(
                {
                    "relative_dir": "2026/03/23/run-000013",
                    "package_id": "article-000182",
                    "article_idxno": "182",
                    "platform": "threads",
                    "decision": "maybe",
                }
            )


if __name__ == "__main__":
    unittest.main()
