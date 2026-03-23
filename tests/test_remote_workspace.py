from io import BytesIO
import json
from pathlib import Path
import unittest
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from mnl_social_publisher.settings import Settings
from mnl_social_publisher.web_app import create_web_app
from mnl_social_publisher.workspace import RemoteWorkspace


FIXTURE_INBOX_ROOT = Path(__file__).parent / "fixtures" / "social_inbox"


class FakeRemoteClient:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def exists(self, remote_path: str) -> bool:
        remote_path = _clean(remote_path)
        if remote_path in self.files:
            return True
        prefix = f"{remote_path}/"
        return any(path.startswith(prefix) for path in self.files)

    def list_children(self, remote_path: str):
        remote_path = _clean(remote_path)
        prefix = f"{remote_path}/" if remote_path else ""
        seen: dict[str, bool] = {}
        for path in self.files:
            if prefix and not path.startswith(prefix):
                continue
            remainder = path[len(prefix) :] if prefix else path
            if not remainder:
                continue
            head, _, tail = remainder.partition("/")
            is_folder = bool(tail)
            seen[head] = seen.get(head, False) or is_folder
        return [FakeEntry(name=name, is_folder=is_folder) for name, is_folder in seen.items()]

    def read_bytes(self, remote_path: str) -> bytes:
        return self.files[_clean(remote_path)]

    def write_bytes(self, remote_path: str, data: bytes) -> dict[str, object]:
        self.files[_clean(remote_path)] = data
        return {"name": Path(remote_path).name}


class FakeEntry:
    def __init__(self, name: str, is_folder: bool) -> None:
        self.name = name
        self.is_folder = is_folder


def _clean(path: str) -> str:
    return str(path).strip("/")


def _load_fixture_into_remote(client: FakeRemoteClient, remote_root: str) -> None:
    for path in FIXTURE_INBOX_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(FIXTURE_INBOX_ROOT).as_posix()
        client.write_bytes(f"{remote_root}/{relative_path}", path.read_bytes())


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


class RemoteWorkspaceTestCase(unittest.TestCase):
    def _build_workspace(self) -> RemoteWorkspace:
        client = FakeRemoteClient()
        _load_fixture_into_remote(client, "social/inbox")
        settings = Settings(
            storage_backend="onedrive",
            inbox_remote_root="social/inbox",
            review_remote_root="social/review",
            approval_remote_root="social/approval",
            outbox_remote_root="social/outbox",
            status_remote_root="social/status",
        )
        workspace = RemoteWorkspace(settings, client)
        workspace._fake_client = client  # type: ignore[attr-defined]
        return workspace

    def test_remote_workspace_builds_review_and_publish_requests(self) -> None:
        workspace = self._build_workspace()
        summary = workspace.build_review_all("2026/03/14/run-000123")
        self.assertEqual(summary["platform_count"], 5)

        client = workspace._fake_client  # type: ignore[attr-defined]
        self.assertIn(
            "social/review/2026/03/14/run-000123/article-000143/threads_post.txt",
            client.files,
        )
        self.assertIn(
            "social/review/2026/03/14/run-000123/article-000143/youtube_script.txt",
            client.files,
        )

        workspace.save_approval(
            relative_dir="2026/03/14/run-000123",
            package_id="article-000143",
            article_idxno=143,
            platform="threads",
            approved=True,
            decided_by="editor@example.com",
            note="remote approval",
        )
        request_summary = workspace.create_publish_requests("2026/03/14/run-000123", "threads")
        self.assertEqual(request_summary["request_count"], 1)
        self.assertIn(
            "social/outbox/threads/2026/03/14/run-000123/article-000143.json",
            client.files,
        )
        self.assertIn(
            "social/status/threads/2026/03/14/run-000123/article-000143.json",
            client.files,
        )

    def test_remote_web_app_flow_uses_remote_workspace(self) -> None:
        workspace = self._build_workspace()
        app = create_web_app(Settings(), workspace=workspace)

        response, body = _invoke(app, "GET", "/")
        self.assertTrue(response["status"].startswith("200"))
        self.assertIn("run-000123", body)
        self.assertIn("onedrive remote", body)

        response, _ = _invoke(
            app,
            "POST",
            "/actions/build-review-all",
            form={"relative_dir": "2026/03/14/run-000123"},
        )
        self.assertTrue(response["status"].startswith("303"))

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
                "decided_by": "remote-reviewer@example.com",
                "note": "browser remote approve",
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

        client = workspace._fake_client  # type: ignore[attr-defined]
        approval_payload = json.loads(
            client.files["social/approval/2026/03/14/run-000123/article-000143.json"].decode("utf-8")
        )
        outbox_payload = json.loads(
            client.files["social/outbox/threads/2026/03/14/run-000123/article-000143.json"].decode("utf-8")
        )
        self.assertTrue(approval_payload["platforms"]["threads"]["approved"])
        self.assertEqual(approval_payload["input_method"], "web_form")
        self.assertEqual(outbox_payload["request_kind"], "mnl/threads-publish-request")


if __name__ == "__main__":
    unittest.main()
