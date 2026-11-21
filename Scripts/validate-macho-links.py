#!/usr/bin/env python3
"""Inspect shipped Apple framework Mach-O dynamic linkage without mutating binaries.

Run on a macOS runner with Xcode command line tools installed. An XCFramework
existing on disk is not enough: embedded dylibs must not bind to another
developer's temporary `build/thin` directory.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import shutil
import subprocess
from pathlib import Path


def audit(root: Path, platform: str = "macos") -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict] = []
    if not shutil.which("otool"):
        return {
            "errors": ["otool unavailable; run on a macOS host with Xcode tools"],
            "warnings": [],
            "libraries": [],
        }

    frameworks = sorted((root / "Sources").glob("Aether*.xcframework"))
    if len(frameworks) != 9:
        errors.append(f"expected 9 imported XCFramework targets, found {len(frameworks)}")

    for xcframework in frameworks:
        try:
            with (xcframework / "Info.plist").open("rb") as fp:
                slices = plistlib.load(fp)["AvailableLibraries"]
        except (OSError, KeyError, plistlib.InvalidFileException) as exc:
            errors.append(f"{xcframework.name}: bad XCFramework metadata: {exc}")
            continue
        matching = [
            sl for sl in slices if sl.get("SupportedPlatform") == platform
            and not sl.get("SupportedPlatformVariant")
        ]
        if not matching:
            errors.append(f"{xcframework.name}: missing {platform} device slice")
            continue
        for sl in matching:
            label = f"{xcframework.name}/{sl['LibraryIdentifier']}"
            binary = xcframework / sl["LibraryIdentifier"] / sl["BinaryPath"]
            if not binary.is_file():
                errors.append(f"{label}: missing binary")
                continue
            for arch in sl.get("SupportedArchitectures", []):
                proc = subprocess.run(
                    ["otool", "-arch", arch, "-L", str(binary)],
                    capture_output=True, text=True, check=False,
                )
                if proc.returncode:
                    errors.append(
                        f"{label} [{arch}]: otool failed: {proc.stderr.strip()[:200]}"
                    )
                    continue
                dependencies = []
                for line in proc.stdout.splitlines()[1:]:
                    name = line.strip().split(" (", 1)[0].strip()
                    if not name:
                        continue
                    dependencies.append(name)
                    # Absolute dependencies on SDK/system runtimes are normal.
                    # Absolute paths into a local build tree are NOT portable.
                    if name.startswith("/") and not name.startswith(
                        ("/usr/lib/", "/System/Library/")
                    ):
                        errors.append(
                            f"{label} [{arch}]: nonportable absolute dylib: {name}"
                        )
                    if "/build/thin/" in name or "/Users/runner/work/" in name:
                        errors.append(
                            f"{label} [{arch}]: dependency embeds temporary build path: {name}"
                        )
                results.append({
                    "framework": xcframework.name,
                    "slice": sl["LibraryIdentifier"],
                    "arch": arch,
                    "dependencies": dependencies,
                })

    return {"platform": platform, "errors": sorted(set(errors)),
            "warnings": warnings, "libraries": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--platform", choices=("macos", "ios", "tvos", "xros"),
                        default="macos")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(), args.platform)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"Audited {len(result['libraries'])} Mach-O architecture slices")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}")
    if result["errors"]:
        print("FAIL: nonportable Apple binary linkage; do not release")
        return 1
    print("PASS: inspected dynamic linkage without nonportable absolute paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
