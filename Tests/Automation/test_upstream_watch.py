"""Offline regression tests for the ApoloFFmpeg upstream update watcher.

No GitHub token, network, Xcode or installed third-party packages are required.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
WATCH_PATH = ROOT / "Scripts" / "check-upstream.py"
SPEC = importlib.util.spec_from_file_location("apolo_upstream_watch", WATCH_PATH)
assert SPEC and SPEC.loader
watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watch)


class UpstreamWatchTests(unittest.TestCase):
    pinned = {
        "FFmpeg": ("n8.1.3", "8.1.3"),
        "dav1d": ("1.5.4", "1.5.4"),
        "zimg": ("release-3.0.6", "3.0.6"),
        "libzvbi": ("v0.2.46", "0.2.46"),
        "dolby_vision": ("libdovi-3.3.2", "3.3.2"),
    }

    def check(self, newest=None, fail=None, missing_source=False, missing_pin=False):
        newest = newest or {}
        fail = set(fail or ())
        with tempfile.TemporaryDirectory() as directory:
            ffmpeg = Path(directory) / "build.sh"
            dovi = Path(directory) / "libdovi.sh"
            ffmpeg.write_text(
                "\n".join([
                    'FFMPEG_VERSION="n8.1.3"',
                    'DAV1D_VERSION="1.5.4"',
                    'ZIMG_VERSION="release-3.0.6"',
                    'ZVBI_VERSION="v0.2.46"',
                ] if not missing_pin else [
                    'FFMPEG_VERSION="n8.1.3"',
                    'DAV1D_VERSION="1.5.4"',
                    'ZIMG_VERSION="release-3.0.6"',
                ]) + "\n", encoding="utf-8"
            )
            if not missing_source:
                dovi.write_text('DOVI_TAG="libdovi-3.3.2"\n', encoding="utf-8")

            def fake_latest(component):
                name = component["name"]
                if name in fail:
                    raise urllib.error.URLError("simulated network outage")
                prefix = component["prefix"]
                version = newest.get(name, self.pinned[name][1])
                return (watch.version_key(version), prefix + version, version)

            output = io.StringIO()
            with (mock.patch.object(watch, "latest_tag", side_effect=fake_latest),
                  mock.patch.object(watch, "advisories", return_value=[]),
                  mock.patch.object(sys, "argv", [
                      "check-upstream.py", "--build-sh", str(ffmpeg),
                      "--libdovi", str(dovi)
                  ]),
                  contextlib.redirect_stdout(output)):
                result = watch.main()
        return result, output.getvalue()

    def test_all_current_returns_zero(self):
        code, report = self.check()
        self.assertEqual(code, 0)
        self.assertIn("Current:", report)

    def test_newer_patch_returns_one(self):
        code, report = self.check(newest={"FFmpeg": "8.1.4"})
        self.assertEqual(code, 1)
        self.assertIn("FFmpeg: 8.1.3 -> 8.1.4", report)

    def test_network_failure_returns_two_not_all_clear(self):
        code, report = self.check(fail={"dav1d"})
        self.assertEqual(code, 2)
        self.assertIn("Could not be checked:", report)

    def test_missing_pin_returns_two(self):
        code, report = self.check(missing_pin=True)
        self.assertEqual(code, 2)
        self.assertIn("libzvbi", report)

    def test_missing_sibling_source_returns_two(self):
        code, report = self.check(missing_source=True)
        self.assertEqual(code, 2)
        self.assertIn("dolby_vision", report)

    def test_partial_failure_takes_priority_over_outdated_source(self):
        code, report = self.check(newest={"FFmpeg": "8.1.4"}, fail={"dav1d"})
        self.assertEqual(code, 2)
        self.assertIn("FFmpeg: 8.1.3 -> 8.1.4", report)
        self.assertIn("Could not be checked:", report)


if __name__ == "__main__":
    unittest.main()
