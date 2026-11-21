#!/usr/bin/env python3
"""Read-only baseline audit for the imported ApoloFFmpeg distribution.

Run on an ApoloFFmpeg checkout; no developer secrets, network,
Xcode installation, binary mutation or re-signing required.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import re
from pathlib import Path


REQUIRED_MODULES = (
    "AetherLibavcodec",
    "AetherLibavformat",
    "AetherLibavutil",
    "AetherLibswresample",
    "AetherLibswscale",
    "AetherLibavfilter",
    "AetherLibdav1d",
    "AetherLibzimg",
    "AetherLibzvbi",
)
REQUIRED_SLICES = {
    ("ios", None, "arm64"),
    ("ios", "simulator", "arm64"),
    ("tvos", None, "arm64"),
    ("tvos", "simulator", "arm64"),
    ("macos", None, "arm64"),
    ("xros", None, "arm64"),
    ("xros", "simulator", "arm64"),
}
PACKAGE_MINIMUM = {"ios": 16.0, "tvos": 16.0, "macos": 14.0, "xros": 1.0}


def audit(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    modules: list[dict] = []

    package_file = root / "Package.swift"
    build_file = root / "build.sh"
    record_file = root / "BUILD-INFO.txt"
    license_files = [
        root / "LICENSE",
        root / "LICENSES" / "README.md",
        root / "LICENSES" / "LGPL-2.1.txt",
    ]
    for path in [package_file, build_file, record_file, *license_files]:
        if not path.is_file():
            errors.append(f"missing required source/license file: {path.relative_to(root)}")
    if errors:
        return {"errors": errors, "warnings": warnings, "modules": modules}

    package = package_file.read_text(encoding="utf-8")
    build = build_file.read_text(encoding="utf-8")
    record = record_file.read_text(encoding="utf-8")
    version = re.search(r'^FFMPEG_VERSION="([^"]+)"', build, re.MULTILINE)
    ffmpeg_version = version.group(1) if version else "unknown"
    if version is None:
        errors.append("build.sh does not expose a pinned FFMPEG_VERSION")
    elif f"FFmpeg {ffmpeg_version} " not in record:
        errors.append(f"BUILD-INFO.txt has no matching FFmpeg {ffmpeg_version} provenance")

    targets = dict(re.findall(
        r'\.binaryTarget\(name:\s*"([^"]+)",\s*path:\s*"([^"]+)"\)', package
    ))
    for module in REQUIRED_MODULES:
        expected = f"Sources/{module}.xcframework"
        if targets.get(module) != expected:
            errors.append(f"{module}: missing/moved binaryTarget at {expected}")
            continue
        framework = root / expected
        try:
            with (framework / "Info.plist").open("rb") as source:
                info = plistlib.load(source)
        except (OSError, plistlib.InvalidFileException) as exc:
            errors.append(f"{module}: invalid XCFramework plist: {exc}")
            continue

        slices: list[dict] = []
        coverage: set[tuple[str, str | None, str]] = set()
        for item in info.get("AvailableLibraries", []):
            platform = item.get("SupportedPlatform", "unknown")
            variant = item.get("SupportedPlatformVariant")
            identifier = item.get("LibraryIdentifier")
            binary = item.get("BinaryPath")
            architectures = item.get("SupportedArchitectures", [])
            if not all(isinstance(x, str) and x for x in [identifier, binary]):
                errors.append(f"{module}: malformed XCFramework slice metadata")
                continue

            binary_path = framework / identifier / binary
            if not binary_path.is_file():
                errors.append(f"{module}/{identifier}: missing executable {binary}")
            else:
                if binary_path.stat().st_size == 0:
                    errors.append(f"{module}/{identifier}: empty executable")

            for arch in architectures:
                coverage.add((platform, variant, arch))

            bundle_path = framework / identifier / item["LibraryPath"]
            plist_path = (
                bundle_path / "Versions" / "A" / "Resources" / "Info.plist"
                if platform == "macos" else bundle_path / "Info.plist"
            )
            minimum = None
            bundle_id = None
            try:
                with plist_path.open("rb") as source:
                    bundle = plistlib.load(source)
                minimum = bundle.get("MinimumOSVersion")
                bundle_id = bundle.get("CFBundleIdentifier")
                if bundle.get("CFBundleExecutable") != module:
                    errors.append(f"{module}/{identifier}: executable name mismatch")
                if not bundle_id:
                    errors.append(f"{module}/{identifier}: missing bundle identifier")
            except (OSError, plistlib.InvalidFileException) as exc:
                errors.append(f"{module}/{identifier}: invalid embedded Info.plist: {exc}")

            expected_floor = PACKAGE_MINIMUM.get(platform)
            if minimum is not None and expected_floor is not None:
                try:
                    actual_floor = float(minimum)
                    if actual_floor > expected_floor:
                        warnings.append(
                            f"{module}/{identifier}: Info.plist minimum {minimum} > "
                            f"SwiftPM declared {platform} minimum {expected_floor:g}; "
                            "verify Mach-O minOS and consumer deployment policy"
                        )
                except (TypeError, ValueError):
                    errors.append(f"{module}/{identifier}: malformed MinimumOSVersion")
            slices.append({
                "identifier": identifier,
                "platform": platform,
                "variant": variant,
                "architectures": architectures,
                "minimum_os": minimum,
                "bundle_id": bundle_id,
            })

        missing = REQUIRED_SLICES - coverage
        for platform, variant, arch in sorted(
            missing, key=lambda item: (item[0], item[1] or "", item[2])
        ):
            errors.append(
                f"{module}: missing {platform} {variant or 'device'} {arch} slice"
            )
        modules.append({"module": module, "slices": slices})

    return {
        "source": "Mosas123/ApoloFFmpeg (imported FFmpegBuild/apolo-union baseline)",
        "ffmpeg_version": ffmpeg_version,
        "module_count": len(modules),
        "modules": modules,
        "warnings": warnings,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument(
        "--strict-deployment", action="store_true",
        help="fail when the legacy binary's platform minimum exceeds Package.swift"
    )
    args = parser.parse_args()
    result = audit(args.root.resolve())
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"ApoloFFmpeg baseline: FFmpeg {result.get('ffmpeg_version', '?')}, "
          f"{result.get('module_count', 0)} XCFramework targets")
    for item in result["warnings"]:
        print(f"WARNING: {item}")
    for item in result["errors"]:
        print(f"ERROR: {item}")
    if result["errors"]:
        return 1
    if args.strict_deployment and result["warnings"]:
        return 2
    print("PASS: package targets, binary slices, provenance and licenses present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
