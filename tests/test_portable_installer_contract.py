"""Static contract checks; real Windows x64 clean-machine QA is still required."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = (ROOT / "install_portable_runtime.cmd").read_text(encoding="utf-8")
MAIN = (ROOT / "install_windows.cmd").read_text(encoding="utf-8")
BUILD = (ROOT / "BUILD_PORTABLE_AND_TEST_WINDOWS.cmd").read_text(encoding="utf-8")


class TestPortableInstaller(unittest.TestCase):
    def test_pyinstaller_path_does_not_end_in_escaped_quote(self):
        """Quoted ROOT\\ trailing slash can consume the final script positional on Windows."""
        self.assertIn('--paths "%ROOT%."', BUILD)
        self.assertNotIn('--paths "%ROOT%"', BUILD)
        self.assertIn('tools\\worker_entry.py', BUILD)

    def test_no_execution_policy_or_defender_bypass(self):
        for data in (PORTABLE, MAIN):
            self.assertNotIn("ExecutionPolicy", data)
            self.assertNotIn("Add-MpPreference", data)
            self.assertNotIn("Set-MpPreference", data)

    def test_artifact_version_and_architecture(self):
        self.assertIn("go_anastruct_2d-runtime-windows-x64-v0.5.5.zip", PORTABLE)
        self.assertIn("PROCESSOR_ARCHITECTURE", PORTABLE)
        self.assertIn("AMD64", PORTABLE)
        self.assertIn("anaStruct 1[.]7[.]0 OK", PORTABLE)

    def test_checksum_precedes_execution(self):
        self.assertIn("Get-FileHash -Algorithm SHA256", PORTABLE)
        self.assertLess(PORTABLE.index("Get-FileHash"), PORTABLE.index("Expand-Archive"))
        self.assertLess(PORTABLE.index("Expand-Archive"), PORTABLE.index("& $exe --check"))
        self.assertIn("Runtime checksum mismatch", PORTABLE)

    def test_staging_and_rollback(self):
        self.assertIn("RUNTIME_STAGE=", PORTABLE)
        self.assertIn("RUNTIME_BACKUP=", PORTABLE)
        self.assertIn("Move-Item -LiteralPath $target -Destination $backup", PORTABLE)
        self.assertIn("Move-Item -LiteralPath $backup -Destination $target", PORTABLE)

    def test_no_network_installation(self):
        for word in ("Invoke-WebRequest", "DownloadFile(", "iwr ", "irm ", "curl ", "wget "):
            self.assertNotIn(word.lower(), PORTABLE.lower())

    def test_main_installer_calls_offline_runtime_first(self):
        self.assertIn('call "%ROOT%install_portable_runtime.cmd"', MAIN)
        self.assertLess(MAIN.index('call "%ROOT%install_portable_runtime.cmd"'),
                        MAIN.index('repair_runtime.cmd'))
        self.assertIn("if errorlevel 1 goto fail", MAIN)


if __name__ == "__main__":
    unittest.main()
