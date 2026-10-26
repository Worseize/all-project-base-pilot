import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))

import manifest  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class ManifestEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conf = Path(self.tmp.name) / "project.conf"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        self.conf.write_text(text, encoding="utf-8")
        return self.conf

    def test_defaults_when_file_is_missing(self):
        self.assertEqual(manifest.entry(self.conf), ["run", "test.sh", "health"])

    def test_reads_declared_entry_points(self):
        self.write("run=app\ntest=check.sh\nhealth=ping\n")
        self.assertEqual(manifest.entry(self.conf), ["app", "check.sh", "ping"])

    def test_empty_test_is_allowed(self):
        self.write("test=\n")
        self.assertEqual(manifest.entry(self.conf)[1], "")

    def test_unknown_key_is_rejected(self):
        self.write("unknown=1\n")
        with self.assertRaises(ValueError):
            manifest.entry(self.conf)

    def test_absolute_run_is_rejected(self):
        self.write("run=/usr/bin/app\n")
        with self.assertRaises(ValueError):
            manifest.entry(self.conf)

    def test_parent_traversal_is_rejected(self):
        self.write("run=../app\n")
        with self.assertRaises(ValueError):
            manifest.entry(self.conf)

    def test_empty_run_is_rejected(self):
        self.write("run=\n")
        with self.assertRaises(ValueError):
            manifest.entry(self.conf)

    def test_cli_prints_tab_separated_entry_points(self):
        path = self.write("run=app\ntest=check.sh\nhealth=ping\n")
        result = subprocess.run(
            [sys.executable, str(DEPLOY / "manifest.py"), "entry", str(path)],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().split("\t"), ["app", "check.sh", "ping"])

    def test_cli_rejects_invalid_manifest(self):
        path = self.write("unknown=1\n")
        result = subprocess.run(
            [sys.executable, str(DEPLOY / "manifest.py"), "entry", str(path)],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown key", result.stderr)


if __name__ == "__main__":
    unittest.main()
