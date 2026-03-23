from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlencode
import urllib.error
import urllib.request


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


class OneDriveError(RuntimeError):
    pass


@dataclass(frozen=True)
class OneDriveEntry:
    name: str
    is_folder: bool


@dataclass
class OneDriveConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    drive_id: str

    @classmethod
    def from_env(cls) -> "OneDriveConfig":
        tenant_id = _clean_env_value(os.environ.get("MNL_ONEDRIVE_TENANT_ID", ""))
        client_id = _clean_env_value(os.environ.get("MNL_ONEDRIVE_CLIENT_ID", ""))
        client_secret = _clean_env_value(os.environ.get("MNL_ONEDRIVE_CLIENT_SECRET", ""))
        drive_id = _clean_env_value(os.environ.get("MNL_ONEDRIVE_DRIVE_ID", ""))
        missing = [
            name
            for name, value in (
                ("MNL_ONEDRIVE_TENANT_ID", tenant_id),
                ("MNL_ONEDRIVE_CLIENT_ID", client_id),
                ("MNL_ONEDRIVE_CLIENT_SECRET", client_secret),
                ("MNL_ONEDRIVE_DRIVE_ID", drive_id),
            )
            if not value
        ]
        if missing:
            raise OneDriveError(f"Missing OneDrive configuration: {', '.join(missing)}")
        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            drive_id=drive_id,
        )


class OneDriveClient:
    def __init__(self, config: OneDriveConfig) -> None:
        self.config = config
        self._access_token: Optional[str] = None
        self._approot_id: Optional[str] = None
        self._children_cache: dict[str, list[dict[str, object]]] = {}
        self._item_cache: dict[str, dict[str, object] | None] = {}

    def exists(self, remote_path: str) -> bool:
        return self.resolve_item(remote_path) is not None

    def list_children(self, remote_path: str) -> list[OneDriveEntry]:
        parent_id = self.get_approot_id() if not remote_path.strip("/") else self._resolve_folder_id(remote_path)
        entries: list[OneDriveEntry] = []
        for item in self._list_child_items(parent_id):
            name = str(item.get("name") or "")
            if not name:
                continue
            entries.append(OneDriveEntry(name=name, is_folder="folder" in item))
        return entries

    def read_bytes(self, remote_path: str) -> bytes:
        item = self.resolve_item(remote_path)
        if item is None:
            raise OneDriveError(f"Remote OneDrive path does not exist: {remote_path}")
        if "folder" in item:
            raise OneDriveError(f"Remote OneDrive path is a folder, not a file: {remote_path}")
        item_id = item.get("id")
        if not item_id:
            raise OneDriveError(f"Remote OneDrive item does not include id: {remote_path}")
        metadata = self._graph_json(
            "GET",
            f"{GRAPH_BASE_URL}/drives/{quote(self.config.drive_id)}/items/{quote(str(item_id))}",
        )
        download_url = metadata.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise OneDriveError(f"Missing download URL for remote path: {remote_path}")
        request = urllib.request.Request(str(download_url), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise OneDriveError(
                f"Failed to download OneDrive file: {exc.read().decode('utf-8', 'replace')}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OneDriveError(f"Failed to download OneDrive file: {exc}") from exc

    def write_bytes(self, remote_path: str, data: bytes) -> dict[str, object]:
        parts = _split_remote_path(remote_path)
        if not parts:
            raise OneDriveError("remote_path must include a file name")
        parent_id = self.ensure_folder("/".join(parts[:-1]))
        file_name = parts[-1]
        url = (
            f"{GRAPH_BASE_URL}/drives/{quote(self.config.drive_id)}/items/{quote(parent_id)}:/"
            f"{quote(file_name)}:/content"
        )
        raw = self._raw_request(
            "PUT",
            url,
            data=data,
            headers={"Content-Type": "application/octet-stream"},
            include_bearer=True,
            expected_status=(200, 201),
        )
        self._invalidate_path_cache(remote_path)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def resolve_item(self, remote_path: str) -> dict[str, object] | None:
        normalized_path = _normalize_remote_path(remote_path)
        parts = _split_remote_path(normalized_path)
        if not parts:
            return None
        if normalized_path in self._item_cache:
            return self._item_cache[normalized_path]
        parent_id = self.get_approot_id()
        item: dict[str, object] | None = None
        current_parts: list[str] = []
        for index, part in enumerate(parts):
            current_parts.append(part)
            current_path = "/".join(current_parts)
            if current_path in self._item_cache:
                item = self._item_cache[current_path]
            else:
                item = self._find_child_by_name(parent_id=parent_id, name=part)
                self._item_cache[current_path] = item
            if item is None:
                self._item_cache[normalized_path] = None
                return None
            if index != len(parts) - 1:
                if "folder" not in item:
                    raise OneDriveError(f"Remote path segment is not a folder: {part}")
                parent_id = str(item["id"])
        return item

    def ensure_folder(self, remote_path: str) -> str:
        parts = _split_remote_path(remote_path)
        parent_id = self.get_approot_id()
        for part in parts:
            parent_id = self._ensure_child_folder(parent_id, part)
        return parent_id

    def get_approot_id(self) -> str:
        if self._approot_id:
            return self._approot_id
        payload = self._graph_json(
            "GET",
            f"{GRAPH_BASE_URL}/drives/{quote(self.config.drive_id)}/special/approot",
        )
        item_id = payload.get("id")
        if not item_id:
            raise OneDriveError("Could not resolve OneDrive approot id")
        self._approot_id = str(item_id)
        return self._approot_id

    def _resolve_folder_id(self, remote_path: str) -> str:
        item = self.resolve_item(remote_path)
        if item is None:
            raise OneDriveError(f"Remote OneDrive folder does not exist: {remote_path}")
        if "folder" not in item:
            raise OneDriveError(f"Remote OneDrive path is not a folder: {remote_path}")
        item_id = item.get("id")
        if not item_id:
            raise OneDriveError(f"Remote OneDrive folder does not include id: {remote_path}")
        return str(item_id)

    def _ensure_child_folder(self, parent_id: str, folder_name: str) -> str:
        child = self._find_child_by_name(parent_id, folder_name)
        if child is not None:
            if "folder" not in child:
                raise OneDriveError(f"OneDrive item already exists and is not a folder: {folder_name}")
            return str(child["id"])

        payload = self._graph_json(
            "POST",
            f"{GRAPH_BASE_URL}/drives/{quote(self.config.drive_id)}/items/{quote(parent_id)}/children",
            body={
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace",
            },
            expected_status=(200, 201),
        )
        item_id = payload.get("id")
        if not item_id:
            raise OneDriveError(f"Failed to create OneDrive folder: {folder_name}")
        self._children_cache.pop(parent_id, None)
        self._item_cache.clear()
        return str(item_id)

    def _find_child_by_name(self, parent_id: str, name: str) -> dict[str, object] | None:
        for item in self._list_child_items(parent_id):
            if item.get("name") == name:
                return item
        return None

    def _list_child_items(self, parent_id: str) -> list[dict[str, object]]:
        if parent_id in self._children_cache:
            return self._children_cache[parent_id]
        payload = self._graph_json(
            "GET",
            f"{GRAPH_BASE_URL}/drives/{quote(self.config.drive_id)}/items/{quote(parent_id)}/children"
            "?$select=id,name,folder,file",
        )
        items = list(payload.get("value", []))
        self._children_cache[parent_id] = items
        return items

    def _invalidate_path_cache(self, remote_path: str) -> None:
        self._item_cache.clear()
        parts = _split_remote_path(remote_path)
        if parts:
            parent_path = "/".join(parts[:-1])
            parent = self.resolve_item(parent_path) if parent_path else {"id": self.get_approot_id()}
            if parent is not None:
                self._children_cache.pop(str(parent.get("id") or ""), None)

    def _graph_json(
        self,
        method: str,
        url: str,
        body: dict[str, object] | None = None,
        expected_status=(200,),
    ) -> dict[str, object]:
        raw = self._raw_request(
            method=method,
            url=url,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            headers={} if body is None else {"Content-Type": "application/json"},
            include_bearer=True,
            expected_status=expected_status,
        )
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _raw_request(
        self,
        method: str,
        url: str,
        data: bytes | None,
        headers: dict[str, str],
        include_bearer: bool,
        expected_status=(200,),
    ) -> bytes:
        request_headers = dict(headers)
        if include_bearer:
            request_headers["Authorization"] = f"Bearer {self._get_access_token()}"

        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                status_code = response.getcode() or 200
                payload = response.read()
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            payload = exc.read()
            if status_code not in expected_status:
                raise OneDriveError(
                    f"OneDrive request failed ({status_code}) for {method} {url}: "
                    f"{payload.decode('utf-8', 'replace')}"
                ) from exc
        except urllib.error.URLError as exc:
            raise OneDriveError(f"OneDrive request failed for {method} {url}: {exc}") from exc

        if status_code not in expected_status:
            raise OneDriveError(
                f"Unexpected status {status_code} for {method} {url}: {payload.decode('utf-8', 'replace')}"
            )
        return payload

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        token_url = TOKEN_URL_TEMPLATE.format(tenant_id=quote(self.config.tenant_id))
        body = urlencode(
            {
                "client_id": self.config.client_id,
                "scope": "https://graph.microsoft.com/.default",
                "client_secret": self.config.client_secret,
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise OneDriveError(
                f"Failed to acquire OneDrive access token: {exc.read().decode('utf-8', 'replace')}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OneDriveError(f"Failed to acquire OneDrive access token: {exc}") from exc

        token = payload.get("access_token")
        if not token:
            raise OneDriveError("Token response did not include access_token")
        self._access_token = str(token)
        return self._access_token


def _clean_env_value(value: str) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    if cleaned.upper() in {"__REQUIRED__", "REQUIRED", "CHANGEME", "TODO"}:
        return ""
    return cleaned


def _split_remote_path(remote_path: str) -> list[str]:
    return [part for part in str(remote_path).split("/") if part.strip("/")]


def _normalize_remote_path(remote_path: str) -> str:
    return "/".join(_split_remote_path(remote_path))
