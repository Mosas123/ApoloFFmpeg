#!/usr/bin/env python3
"""Rewrite locally-built FFmpeg dylib references to the shipped Apple frameworks.

Packaging helper, not a runtime workaround: operates on the framework binary
in the build staging directory, before stripping/signing. For tests, operate
on a disposable copy, never on the repository's published XCFramework slices.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


DEPENDENCY_FRAMEWORKS = {
    "libavcodec": "AetherLibavcodec",
    "libavformat": "AetherLibavformat",
    "libavutil": "AetherLibavutil",
    "libswresample": "AetherLibswresample",
    "libswscale": "AetherLibswscale",
    "libavfilter": "AetherLibavfilter",
    "libdav1d": "AetherLibdav1d",
    "libzimg": "AetherLibzimg",
    "libzvbi": "AetherLibzvbi",
}
SYSTEM_PREFIXES = ("/usr/lib/", "/System/Library/")


def run(*command: str) -> str:
    process = subprocess.run(
        command, capture_output=True, text=True, check=False
    )
    if process.returncode:
        raise RuntimeError(
            f"{' '.join(command[:2])} failed (exit {process.returncode}): "
            f"{process.stderr.strip()[:500]}"
        )
    return process.stdout


def framework_subpath(name: str, platform: str) -> str:
    if platform == "macos":
        return f"{name}.framework/Versions/A/{name}"
    return f"{name}.framework/{name}"


def arches(binary: Path) -> list[str]:
    return run("lipo", "-archs", str(binary)).strip().split()


def dependencies(binary: Path, arch: str) -> list[str]:
    output = run("otool", "-arch", arch, "-L", str(binary))
    # The first line names the inspected binary/architecture, not a dependency.
    return [
        line.strip().split(" (", 1)[0].strip()
        for line in output.splitlines()[1:]
        if line.strip()
    ]


def known_dep(name: str) -> str | None:
    base = name.rsplit("/", 1)[-1]
    for library, framework in DEPENDENCY_FRAMEWORKS.items():
        if re.fullmatch(rf"{re.escape(library)}(?:\.[0-9]+)*\.dylib", base):
            return framework
    return None


def relocate(binary: Path, module: str, platform: str) -> int:
    archs = arches(binary)
    if not archs:
        raise RuntimeError(f"{binary}: lipo found no architectures")

    replacements: dict[str, str] = {}
    for arch in archs:
        for old in dependencies(binary, arch):
            destination = known_dep(old)
            if destination:
                replacements[old] = f"@rpath/{framework_subpath(destination, platform)}"

    # Existing FFmpegBuild uses a unique Aether install name to coexist with
    # mpv/other FFmpeg distributions; preserve it while the consumer is stable.
    run(
        "install_name_tool", "-id",
        f"@rpath/{framework_subpath(module, platform)}", str(binary)
    )
    for old, new in sorted(replacements.items()):
        run("install_name_tool", "-change", old, new, str(binary))
        print(f"{module}: {old} -> {new}")

    errors: list[str] = []
    for arch in archs:
        for loaded in dependencies(binary, arch):
            if loaded.startswith("/") and not loaded.startswith(SYSTEM_PREFIXES):
                errors.append(f"{module}[{arch}]: nonportable dylib {loaded}")
            if known_dep(loaded) is not None:
                errors.append(
                    f"{module}[{arch}]: FFmpeg sibling was not relocated: {loaded}"
                )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(
        f"OK: {module}, {len(archs)} architecture(s), "
        f"{len(replacements)} sibling install-name replacement(s)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--framework-name", required=True,
                        choices=sorted(DEPENDENCY_FRAMEWORKS.values()))
    parser.add_argument("--platform", choices=("ios", "isimulator", "tvos",
                        "tvsimulator", "xros", "xrsimulator", "macos"),
                        required=True)
    args = parser.parse_args()
    if not args.binary.is_file():
        parser.error(f"binary not found: {args.binary}")
    try:
        return relocate(args.binary, args.framework_name, args.platform)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
