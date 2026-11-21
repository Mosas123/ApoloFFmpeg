"""Source-level gates for ApoloFFmpeg's Apple deployment-target metadata.

The checked-in XCFrameworks are prebuilt and are validated separately after a
rebuild. These tests inspect the *policy* in build.sh and Package.swift without
requiring a Mac, Xcode, binary modification or upstream download.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "build.sh").read_text(encoding="utf-8")
PACKAGE = (ROOT / "Package.swift").read_text(encoding="utf-8")

PLATFORMS = {
    "ios": ("iOS", "16.0", "iPhoneOS"),
    "isimulator": ("iOS", "16.0", "iPhoneSimulator"),
    "tvos": ("tvOS", "16.0", "AppleTVOS"),
    "tvsimulator": ("tvOS", "16.0", "AppleTVSimulator"),
    "xros": ("visionOS", "1.0", "XROS"),
    "xrsimulator": ("visionOS", "1.0", "XRSimulator"),
    "macos": ("macOS", "14.0", "MacOSX"),
}
BUILDERS = {"build_one", "build_dav1d_one", "build_zimg_one", "build_zvbi_one"}


def framework_policy():
    blocks = re.findall(
        r"local MIN_OS SUPPORTED_PLATFORM\s+case \"\$\{PLATFORM\}\" in(.*?)^\s*esac",
        SCRIPT, flags=re.S | re.M,
    )
    if len(blocks) != 1:
        raise AssertionError(f"Expected exactly one framework MinimumOSVersion block; got {len(blocks)}")
    block = blocks[0]
    parsed = {}
    for platform, minimum, supported in re.findall(
        r'^\s*(\w+)\)\s+MIN_OS="(\d+\.\d+)";\s+SUPPORTED_PLATFORM="([^"]+)"\s*;;',
        block, flags=re.M,
    ):
        parsed[platform] = (minimum, supported)
    return block, parsed


class DeploymentMetadataPolicyTests(unittest.TestCase):
    def test_each_platform_has_exactly_one_explicit_plist_minimum(self):
        _, policy = framework_policy()
        self.assertEqual(set(policy), set(PLATFORMS))
        for platform, (_, minimum, supported) in PLATFORMS.items():
            with self.subTest(platform=platform):
                self.assertEqual(policy[platform], (minimum, supported))

    def test_swiftpm_floor_matches_framework_metadata(self):
        _, policy = framework_policy()
        for platform, (swift_name, expected, _) in PLATFORMS.items():
            with self.subTest(platform=platform):
                m = re.search(rf"\.{swift_name}\(\.v(\d+)(?:_(\d+))?\)", PACKAGE)
                self.assertIsNotNone(m, f"Missing Package.swift {swift_name} minimum")
                declared = m.group(1) + "." + (m.group(2) or "0")
                self.assertEqual(declared, expected)
                self.assertEqual(policy[platform][0], declared)

    def test_all_four_upstream_builders_compile_for_declared_minimum(self):
        rows = re.findall(
            r"^(build_(?:one|dav1d_one|zimg_one|zvbi_one))\s+"
            r"(ios|isimulator|tvos|tvsimulator|xros|xrsimulator|macos)-\S+"
            r"\s+\S+\s+\S+\s+(\S+)\s+(\d+\.\d+)\s*$",
            SCRIPT, flags=re.M,
        )
        per_builder = {builder: set() for builder in BUILDERS}
        self.assertEqual(len(rows), 40, f"Expected 4 builders x 10 architecture slices; got {len(rows)}")
        for builder, platform, triple, minimum in rows:
            with self.subTest(builder=builder, platform=platform, triple=triple):
                self.assertIn(builder, BUILDERS)
                per_builder[builder].add((platform, triple))
                self.assertEqual(minimum, PLATFORMS[platform][1])
                self.assertIn(minimum, triple)
        for builder, targets in per_builder.items():
            self.assertEqual(len(targets), 10, f"{builder} lost one or more Apple build slices")

    def test_unsupported_platform_is_error_not_default_to_ios(self):
        block, _ = framework_policy()
        fallback = re.search(r"^\s*\*\)\s+(.+)\s*;;\s*$", block, flags=re.M)
        self.assertIsNotNone(fallback)
        self.assertIn("return 1", fallback.group(1))
        self.assertNotIn('MIN_OS=', fallback.group(1))

    def test_packaging_writes_selected_minimum_into_info_plist(self):
        self.assertIn("<key>MinimumOSVersion</key><string>\${MIN_OS}</string>", SCRIPT)


if __name__ == "__main__":
    unittest.main()
