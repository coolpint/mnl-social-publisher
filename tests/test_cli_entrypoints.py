import os
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


class CliEntrypointTestCase(unittest.TestCase):
    def test_python_m_package_entrypoint_prints_help(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "mnl_social_publisher", "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("serve-web", result.stdout)

    def test_python_m_cli_module_entrypoint_prints_help(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "mnl_social_publisher.cli", "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("serve-web", result.stdout)


if __name__ == "__main__":
    unittest.main()
