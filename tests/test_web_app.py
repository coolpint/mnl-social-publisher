from io import BytesIO
import base64
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from mnl_social_publisher.settings import Settings
from mnl_social_publisher.web_app import create_web_app


FIXTURE_INBOX_ROOT = Path(__file__).parent / "fixtures" / "social_inbox"


def _invoke(app, method: str, path: str, query: dict | None = None, form: dict | None = None):
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method.upper()
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = urlencode(query or {})
    raw = urlencode(form or {}).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
    environ["wsgi.input"] = BytesIO(raw)

    result = {}

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = headers

    body = b"".join(app(environ, start_response)).decode("utf-8")
    return result, body


class WebAppTestCase(unittest.TestCase):
    def test_healthz_returns_ok_without_auth(self) -> None:
        app = create_web_app(
            Settings(
                web_basic_auth_username="desk",
                web_basic_auth_password="secret",
            )
        )

        response, body = _invoke(app, "GET", "/healthz")

        self.assertTrue(response["status"].startswith("200"))
        self.assertEqual(body, "ok\n")

    def test_dashboard_requires_basic_auth_when_configured(self) -> None:
        app = create_web_app(
            Settings(
                inbox_root=FIXTURE_INBOX_ROOT,
                web_basic_auth_username="desk",
                web_basic_auth_password="secret",
            )
        )

        response, body = _invoke(app, "GET", "/")

        self.assertTrue(response["status"].startswith("401"))
        self.assertIn("Authentication required", body)

    def test_dashboard_allows_basic_auth_when_credentials_match(self) -> None:
        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as approval_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            app = create_web_app(
                Settings(
                    inbox_root=FIXTURE_INBOX_ROOT,
                    review_root=Path(review_dir),
                    approval_root=Path(approval_dir),
                    outbox_root=Path(outbox_dir),
                    status_root=Path(status_dir),
                    web_basic_auth_username="desk",
                    web_basic_auth_password="secret",
                )
            )
            token = base64.b64encode(b"desk:secret").decode("ascii")
            environ = {}
            setup_testing_defaults(environ)
            environ["REQUEST_METHOD"] = "GET"
            environ["PATH_INFO"] = "/"
            environ["QUERY_STRING"] = ""
            environ["HTTP_AUTHORIZATION"] = f"Basic {token}"
            environ["CONTENT_LENGTH"] = "0"
            environ["wsgi.input"] = BytesIO(b"")

            result = {}

            def start_response(status, headers):
                result["status"] = status
                result["headers"] = headers

            body = b"".join(app(environ, start_response)).decode("utf-8")

            self.assertTrue(result["status"].startswith("200"))
            self.assertIn("오늘의 소셜 발행 관리판", body)

    def test_dashboard_renders_batch_link(self) -> None:
        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as approval_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            app = create_web_app(
                Settings(
                    inbox_root=FIXTURE_INBOX_ROOT,
                    review_root=Path(review_dir),
                    approval_root=Path(approval_dir),
                    outbox_root=Path(outbox_dir),
                    status_root=Path(status_dir),
                )
            )
            response, body = _invoke(app, "GET", "/")

            self.assertTrue(response["status"].startswith("200"))
            self.assertIn("오늘의 소셜 발행 관리판", body)
            self.assertIn("run-000123", body)
            self.assertIn("콘텐츠 초안 만들기", body)
            self.assertIn("승인 입력 방식: 브라우저 승인 입력", body)
            self.assertIn("승인 저장 방식: 로컬 JSON 파일", body)
            self.assertIn("오늘의 작업 요약", body)

    def test_build_review_all_action_creates_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as approval_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            app = create_web_app(
                Settings(
                    inbox_root=FIXTURE_INBOX_ROOT,
                    review_root=Path(review_dir),
                    approval_root=Path(approval_dir),
                    outbox_root=Path(outbox_dir),
                    status_root=Path(status_dir),
                )
            )
            response, _ = _invoke(
                app,
                "POST",
                "/actions/build-review-all",
                form={"relative_dir": "2026/03/14/run-000123"},
            )

            self.assertTrue(response["status"].startswith("303"))
            self.assertTrue(
                (
                    Path(review_dir)
                    / "2026/03/14/run-000123/article-000143/threads_post.txt"
                ).exists()
            )
            self.assertTrue(
                (
                    Path(review_dir)
                    / "2026/03/14/run-000123/article-000143/youtube_script.txt"
                ).exists()
            )

    def test_get_build_review_all_action_shows_confirm_page(self) -> None:
        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as approval_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            app = create_web_app(
                Settings(
                    inbox_root=FIXTURE_INBOX_ROOT,
                    review_root=Path(review_dir),
                    approval_root=Path(approval_dir),
                    outbox_root=Path(outbox_dir),
                    status_root=Path(status_dir),
                )
            )
            response, body = _invoke(
                app,
                "GET",
                "/actions/build-review-all",
                query={"relative_dir": "2026/03/14/run-000123"},
            )

            self.assertTrue(response["status"].startswith("200"))
            self.assertIn("콘텐츠 초안 만들기", body)
            self.assertIn("소셜미디어별 콘텐츠 초안 만들기", body)

    def test_get_action_without_required_params_shows_help(self) -> None:
        app = create_web_app(Settings(inbox_root=FIXTURE_INBOX_ROOT))

        response, body = _invoke(app, "GET", "/actions/create-publish-requests")

        self.assertTrue(response["status"].startswith("200"))
        self.assertIn("게시 준비", body)
        self.assertIn("대시보드로 가기", body)

    def test_approve_and_queue_publish_request_from_browser_flow(self) -> None:
        with tempfile.TemporaryDirectory() as review_dir, tempfile.TemporaryDirectory() as approval_dir, tempfile.TemporaryDirectory() as outbox_dir, tempfile.TemporaryDirectory() as status_dir:
            app = create_web_app(
                Settings(
                    inbox_root=FIXTURE_INBOX_ROOT,
                    review_root=Path(review_dir),
                    approval_root=Path(approval_dir),
                    outbox_root=Path(outbox_dir),
                    status_root=Path(status_dir),
                )
            )

            _invoke(
                app,
                "POST",
                "/actions/build-review-all",
                form={"relative_dir": "2026/03/14/run-000123"},
            )
            _invoke(
                app,
                "POST",
                "/actions/approve",
                form={
                    "relative_dir": "2026/03/14/run-000123",
                    "package_id": "article-000143",
                    "article_idxno": "143",
                    "platform": "threads",
                    "decision": "approve",
                    "decided_by": "editor@example.com",
                    "note": "웹 UI 승인",
                },
            )
            response, _ = _invoke(
                app,
                "POST",
                "/actions/create-publish-requests",
                form={
                    "relative_dir": "2026/03/14/run-000123",
                    "platform": "threads",
                },
            )

            self.assertTrue(response["status"].startswith("303"))
            approval_payload = json.loads(
                (
                    Path(approval_dir)
                    / "2026/03/14/run-000123/article-000143.json"
                ).read_text(encoding="utf-8")
            )
            outbox_payload = json.loads(
                (
                    Path(outbox_dir)
                    / "threads/2026/03/14/run-000123/article-000143.json"
                ).read_text(encoding="utf-8")
            )
            status_payload = json.loads(
                (
                    Path(status_dir)
                    / "threads/2026/03/14/run-000123/article-000143.json"
                ).read_text(encoding="utf-8")
            )

            self.assertTrue(approval_payload["platforms"]["threads"]["approved"])
            self.assertEqual(approval_payload["input_method"], "web_form")
            self.assertEqual(outbox_payload["request_kind"], "mnl/threads-publish-request")
            self.assertEqual(status_payload["state"], "publishing")


if __name__ == "__main__":
    unittest.main()
