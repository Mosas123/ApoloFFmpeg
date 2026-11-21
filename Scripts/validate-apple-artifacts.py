#!/usr/bin/env python3
"""Inspect the *shipped* Apple binaries without changing their metadata.

This gate deliberately reports Package.swift vs Info.plist vs Mach-O minOS
mismatches without 'fixing' them. Use --strict-deployment only after the
project approves an explicit deployment-target policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import subprocess
from pathlib import Path


PLATFORMS = {
    "ios": "iOS",
    "tvos": "tvOS",
    "macos": "macOS",
    "xros": "visionOS",
}


def package_floors(package: str) -> dict[str, str]:
    result = {}
    for platform, swift_name in PLATFORMS.items():
        match = re.search(
            rf"\.{swift_name}\(\.v(\d+)(?:_(\d+))?\)", package
        )
        if not match:
            raise ValueError(f"Package.swift has no {swift_name} deployment floor")
        result[platform] = (
            match.group(1) + (f".{match.group(2)}" if match.group(2) else ".0")
        )
    return result


def version(value: str) -> tuple[int, ...]:
    numbers = tuple(int(n) for n in str(value).split("."))
    return numbers + (0,) * (3 - len(numbers))


def macho_build_version(binary: Path, arch: str) -> dict[str, str]:
    result = subprocess.run(
        ["otool", "-arch", arch, "-l", str(binary)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"otool -arch {arch} failed: {result.stderr.strip()[:300]}")
    for command in re.split(r"(?=Load command \d+\s*$)", result.stdout, flags=re.M):
        kind = re.search(r"^\s*cmd\s+(LC_BUILD_VERSION|LC_VERSION_MIN_\w+)\s*$",
                         command, flags=re.M)
        if not kind:
            continue
        minimum = re.search(r"^\s*(?:minos|version)\s+(\d+(?:\.\d+){1,2})\s*$",
                            command, flags=re.M)
        platform = re.search(r"^\s*platform\s+([A-Za-z0-9_]+)\s*$",
                             command, flags=re.M)
        sdk = re.search(r"^\s*sdk\s+(\d+(?:\.\d+){1,2})\s*$",
                        command, flags=re.M)
        if not minimum:
            raise RuntimeError(f"{kind.group(1)} has no minOS/version")
        return {
            "command": kind.group(1),
            "minimum": minimum.group(1),
            "platform": platform.group(1) if platform else "legacy",
            "sdk": sdk.group(1) if sdk else "",
        }
    raise RuntimeError(f"no Mach-O minimum OS load command for architecture {arch}")


def audit(root: Path, *, strict_deployment: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    details: list[dict] = []
    floors = package_floors((root / "Package.swift").read_text(encoding="utf-8"))
    info_text = (root / "BUILD-INFO.txt").read_text(encoding="utf-8")
    recorded = {
        rel: sha for sha, rel in re.findall(
            r"^([0-9a-f]{64})\s+(Sources/\S+)\s*$", info_text, flags=re.M
        )
    }
    seen_hashes: set[str] = set()
    xcframeworks = sorted((root / "Sources").glob("Aether*.xcframework"))
    if len(xcframeworks) != 9:
        errors.append(f"expected 9 XCFrameworks; found {len(xcframeworks)}")
    if not recorded:
        errors.append("BUILD-INFO.txt has no shipped Mach-O SHA-256 entries")

    for xc in xcframeworks:
        with (xc / "Info.plist").open("rb") as handle:
            slices = plistlib.load(handle).get("AvailableLibraries", [])
        for item in slices:
            platform = item.get("SupportedPlatform", "")
            identifier = item.get("LibraryIdentifier", "")
            label = f"{xc.name}/{identifier}"
            if platform not in floors:
                errors.append(f"{label}: unknown platform {platform}")
                continue
            binary = xc / identifier / item.get("BinaryPath", "")
            framework = xc / identifier / item.get("LibraryPath", "")
            embedded_info = (
                framework / "Versions/A/Resources/Info.plist" if platform == "macos"
                else framework / "Info.plist"
            )
            if not binary.is_file() or not embedded_info.is_file():
                errors.append(f"{label}: missing binary or embedded Info.plist")
                continue

            with embedded_info.open("rb") as handle:
                bundle = plistlib.load(handle)
            floor = floors[platform]
            bundle_floor = str(bundle.get("MinimumOSVersion", ""))
            if not bundle_floor:
                errors.append(f"{label}: framework has no MinimumOSVersion")
            elif version(bundle_floor) != version(floor):
                warnings.append(
                    f"{label}: Package.swift {floor} but bundle Info.plist {bundle_floor}"
                )

            rel = binary.relative_to(root).as_posix()
            expected_hash = recorded.get(rel)
            if not expected_hash:
                errors.append(f"{label}: binary missing from BUILD-INFO.txt: {rel}")
            else:
                seen_hashes.add(rel)
                real_hash = hashlib.file_digest(binary.open("rb"), "sha256").hexdigest()
                if real_hash != expected_hash:
                    errors.append(
                        f"{label}: SHA-256 differs from BUILD-INFO.txt "
                        f"(record {expected_hash}, actual {real_hash})"
                    )

            signature = subprocess.run(
                ["codesign", "--verify", "--strict", "--verbose=1", str(framework)],
                capture_output=True, text=True, check=False,
            )
            if signature.returncode:
                errors.append(
                    f"{label}: invalid framework signature: "
                    f"{signature.stderr.strip()[:250]}"
                )
            for arch in item.get("SupportedArchitectures", []):
                try:
                    macho = macho_build_version(binary, arch)
                except RuntimeError as exc:
                    errors.append(f"{label} [{arch}]: {exc}")
                    continue
                if version(macho["minimum"]) > version(floor):
                    errors.append(
                        f"{label} [{arch}]: Mach-O minimum {macho['minimum']} "
                        f"exceeds Package.swift minimum {floor}"
                    )
                if bundle_floor and version(macho["minimum"]) != version(bundle_floor):
                    warnings.append(
                        f"{label} [{arch}]: Mach-O minimum {macho['minimum']} "
                        f"but bundle metadata says {bundle_floor}"
                    )
                details.append({
                    "framework": xc.name,
                    "slice": identifier,
                    "architecture": arch,
                    "swiftpm_minimum": floor,
                    "bundle_minimum": bundle_floor,
                    "macho": macho,
                    "sha256": expected_hash,
                    "signature_valid": signature.returncode == 0,
                })

    missing = sorted(set(recorded) - seen_hashes)
    if missing:
        errors.append(
            f"{len(missing)} BUILD-INFO.txt binary entries were not verified: "
            + ", ".join(missing[:3])
        )
    if len(details) < 63:
        errors.append(f"expected at least 63 architecture audits, got {len(details)}")
    return {
        "package_minimums": floors,
        "xcframework_count": len(xcframeworks),
        "architecture_count": len(details),
        "recorded_binary_count": len(recorded),
        "verified_binary_count": len(seen_hashes),
        "warnings": warnings,
        "errors": errors,
        "strict_deployment": strict_deployment,
        "slices": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--strict-deployment", action="store_true")
    args = parser.parse_args()
    report = audit(args.root.resolve(), strict_deployment=args.strict_deployment)
    if args.report_json:
        args.report_json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        "Apple artifact audit: "
        f"{report['xcframework_count']} frameworks, "
        f"{report['architecture_count']} architecture checks, "
        f"{report['verified_binary_count']} verified binary hashes"
    )
    print(f"Deployment differences: {len(report['warnings'])}; errors: {len(report['errors'])}")
    for note in report["warnings"][:12]:
        print(f"WARNING: {note}")
    if len(report["warnings"]) > 12:
        print(f"WARNING: {len(report['warnings']) - 12} more differences in JSON report")
    for error in report["errors"]:
        print(f"ERROR: {error}")
    if report["errors"]:
        return 1
    if args.strict_deployment and report["warnings"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
