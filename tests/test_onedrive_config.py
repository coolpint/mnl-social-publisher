from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mnl_social_publisher.onedrive import OneDriveConfig, OneDriveError


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


if __name__ == "__main__":
    unittest.main()
