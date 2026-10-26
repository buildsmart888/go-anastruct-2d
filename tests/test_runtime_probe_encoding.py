"""Regression: Windows PyInstaller console can emit CP1252, while host uses UTF-8."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from go_anastruct_2d import runtime


class PortableWorkerEncodingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.exe = Path(self.tempdir.name) / "dummy_worker.exe"
        self.exe.write_bytes(b"mock")
        self.expected = f"anaStruct {runtime.SOLVER_VERSION} OK".encode("ascii")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_legacy_windows_cp1252_em_dash(self):
        response = subprocess.CompletedProcess([], 0, self.expected + b" \x97 GO worker", b"")
        with patch.object(runtime.subprocess, "run", return_value=response):
            healthy, message = runtime.probe_worker_exe(self.exe)
        self.assertTrue(healthy)
        self.assertIn("GO worker", message)
        self.assertIn("\u2014", message)

    def test_utf8_banner(self):
        response = subprocess.CompletedProcess(
            [], 0, self.expected + " — GO worker".encode("utf-8"), b""
        )
        with patch.object(runtime.subprocess, "run", return_value=response):
            healthy, message = runtime.probe_worker_exe(self.exe)
        self.assertTrue(healthy)
        self.assertIn("\u2014", message)

    def test_check_token_missing(self):
        response = subprocess.CompletedProcess([], 0, b"anaStruct INVALID OK", b"")
        with patch.object(runtime.subprocess, "run", return_value=response):
            healthy, _ = runtime.probe_worker_exe(self.exe)
        self.assertFalse(healthy)

    def test_nonzero_exit_cannot_be_healthy(self):
        response = subprocess.CompletedProcess([], 1, self.expected, b"error")
        with patch.object(runtime.subprocess, "run", return_value=response):
            healthy, _ = runtime.probe_worker_exe(self.exe)
        self.assertFalse(healthy)

    def test_invalid_diagnostic_bytes_do_not_crash(self):
        response = subprocess.CompletedProcess([], 1, b"", b"fatal: \x81")
        with patch.object(runtime.subprocess, "run", return_value=response):
            healthy, message = runtime.probe_worker_exe(self.exe)
        self.assertFalse(healthy)
        self.assertIn("fatal", message)

    def test_probe_uses_binary_capture(self):
        response = subprocess.CompletedProcess([], 0, self.expected, b"")
        with patch.object(runtime.subprocess, "run", return_value=response) as call:
            runtime.probe_worker_exe(self.exe)
        kwargs = call.call_args.kwargs
        self.assertTrue(kwargs["capture_output"])
        self.assertNotIn("text", kwargs)
        self.assertNotIn("encoding", kwargs)


if __name__ == "__main__":
    unittest.main()
