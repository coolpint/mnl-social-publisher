from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mnl_social_publisher.onedrive import OneDriveClient, OneDriveConfig, OneDriveError


class OneDriveConfigTestCase(unittest.TestCase):
    def test_required_placeholder_is_treated_as_missing(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MNL_ONEDRIVE_TENANT_ID": "__REQUIRED__",
                "MNL_ONEDRIVE_CLIENT_ID": "client-id",
                "MNL_ONEDRIVE_CLIENT_SECRET": "secret",
                "MNL_ONEDRIVE_DRIVE_ID": "drive-id",
            },
            clear=False,
        ):
            with self.assertRaises(OneDriveError):
                OneDriveConfig.from_env()


class CachedOneDriveClient(OneDriveClient):
    def __init__(self) -> None:
        super().__init__(
            OneDriveConfig(
                tenant_id="tenant",
                client_id="client",
                client_secret="secret",
                drive_id="drive",
            )
        )
        self.graph_calls: list[str] = []
        self.children_by_parent = {
            "root": [{"id": "social-id", "name": "social", "folder": {}}],
            "social-id": [{"id": "inbox-id", "name": "inbox", "folder": {}}],
            "inbox-id": [{"id": "2026-id", "name": "2026", "folder": {}}],
            "2026-id": [{"id": "03-id", "name": "03", "folder": {}}],
            "03-id": [{"id": "23-id", "name": "23", "folder": {}}],
            "23-id": [{"id": "run-id", "name": "run-000013", "folder": {}}],
            "run-id": [{"id": "batch-id", "name": "batch.json", "file": {}}],
        }

    def _get_access_token(self) -> str:
        return "token"

    def _graph_json(
        self,
        method: str,
        url: str,
        body: dict[str, object] | None = None,
        expected_status=(200,),
    ) -> dict[str, object]:
        self.graph_calls.append(url)
        if url.endswith("/special/approot"):
            return {"id": "root"}
        marker = "/items/"
        if marker not in url or not url.endswith("/children?$select=id,name,folder,file"):
            raise AssertionError(f"Unexpected Graph URL in test: {url}")
        parent_id = url.split(marker, 1)[1].split("/", 1)[0]
        return {"value": self.children_by_parent.get(parent_id, [])}


class OneDriveClientCacheTestCase(unittest.TestCase):
    def test_resolve_item_uses_cached_graph_path_lookups(self) -> None:
        client = CachedOneDriveClient()
        first = client.resolve_item("social/inbox/2026/03/23/run-000013/batch.json")
        second = client.resolve_item("social/inbox/2026/03/23/run-000013/batch.json")

        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        self.assertEqual(len(client.graph_calls), 8)


if __name__ == "__main__":
    unittest.main()
