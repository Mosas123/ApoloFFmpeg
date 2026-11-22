# ApoloFFmpeg — technical charter

> **Status (21 Nov 2026):** independent `Mosas123/ApoloFFmpeg` repository imported with Git history; `apolo-union` is its default branch. The current baseline is inherited from `Mosas123/FFmpegBuild`; **no production dependency has been switched**. Binary release verification remains in progress.

## Mission

Maintain an **upstream-based FFmpeg distribution for Apple platforms**, focused on
ApoloEngine's audio requirements without reimplementing FFmpeg decoders.

- **FFmpeg**: demuxing, codec parsing/decoding, resampling when required.
- **Apple frameworks**: network transport (`URLSession`), media rendering/clock
  (`AVFoundation`/`CoreMedia`), audio routes and interruptions
  (`AVAudioSession`), supported hardware acceleration (`VideoToolbox` and
  `AudioToolbox` where appropriate).
- **ApoloEngine**: source routing, FFmpeg AVIO ownership, DSP, gapless queue,
  playback state, Now Playing and safety checks.
- **Trop**: the consumer UI and user-facing playback orchestration.

A native Apple integration **does not** mean private APIs, simulated Atmos,
unverified bit-perfect output, or FFmpeg replacing iOS's audio system.

## Imported baseline (source verified; runtime validation ongoing)

| Item | Baseline |
| --- | --- |
| Source repository | `Mosas123/FFmpegBuild` (fork of `superuser404notfound/FFmpegBuild`) |
| Source branch | `apolo-union` |
| Snapshot checked | `c12701ebf9b51fab0940948dd630c22f041fcfe9` |
| FFmpeg sources | `n8.1.3` pinned in `build.sh` |
| Other upstream sources | dav1d 1.5.4; zimg release-3.0.6; libzvbi v0.2.46 |
| Packaging | 9 `Aether*.xcframework` binary targets, dynamic-framework distribution |
| Apple targets | iOS, tvOS, macOS, visionOS (+ simulators) |
| Transport policy | FFmpeg built without its network stack; custom AVIO supplied by ApoloEngine |

**Minimum-OS metadata under review:** The inherited binaries declare
`MinimumOSVersion=26.0` for iOS/tvOS although `Package.swift` and the
actual Mach-O `LC_BUILD_VERSION` inspection of the 21 November staged rebuild
report 16.0. The follow-up source policy sets the generated framework plist
floor to 16.0, matching compiler targets and SwiftPM. **The already staged
binaries are not silently edited**: they need a new full rebuild, signature
verification, CI, consumer validation and device QA before release.
This is not a claim that iOS/tvOS 16 runtime compatibility is established.

## Non-negotiable engineering rules

1. **No decoder rewrite as a branding exercise.** Start with upstream FFmpeg,
   preserve provenance, carry only justified, auditable patches.
2. **Do not rename exported modules/install names in phase 0.** ApoloEngine
   currently imports `AetherLibavcodec`, `AetherLibavformat`,
   `AetherLibavutil`, and `AetherLibswresample`. Renaming these requires a
   coordinated build/package/import migration, with rollback.
3. **Never switch Trop or ApoloEngine to an unvalidated binary.**
4. **Don't destroy old FFmpeg or SwiftPM provenance.** Keep licenses, original
   copyright notices, tags, source hashes, patch inventories and toolchain logs.
5. **No private Apple APIs, patched system frameworks or forced hardware
   behavior.** Only publicly supported media capabilities.
6. **Keep FFmpeg's LGPL obligations enforceable.** Dynamic linking is one
   implementation detail, not a substitute for source availability, license
   notices, proper attribution, and relinking/replacement rights.
7. **Security and performance before features.** Harden size bounds,
   cancellation/ownership, malformed streams and decoder memory. Measure
   energy, peak RSS, decode latency and acoustic continuity on devices.
8. **Distinguish build profiles.** The existing full Aether-compatible union
   stays the reference. A future `audio-minimal` profile is an additional
   measured build, never an in-place deletion of shared video features.
9. **Do not make FFmpeg responsible for Trop's YouTube catalog/resolver.**
   Provider lookup belongs in the application layer.

## Milestones

- **A0 — Provenance and baseline:** own repo exists, source history imported,
  immutable source snapshot recorded, read-only baseline checks green, license
  texts and patch inventory verified.
- **A1 — Reproducible packaging:** same compiler/source hashes produce the
  expected framework names and iOS/tvOS/visionOS/macOS slices. Compare
  binaries, `otool -L`, architecture, min OS, SDK, signatures, and dSYM UUIDs.
- **A2 — Native integration:** test custom AVIO cancellation, EOF/seek, route
  change, pause/interruption semantics without modifying Apple frameworks.
- **A3 — Audio profile experiment:** explicit codec/demuxer/filter whitelist;
  benchmark versus the union across startup, memory, binary size and fidelity.
- **A4 — Controlled consumption:** ApoloEngine uses a pinned tag/commit with
  rollback; Trop remains unchanged until its IPA smoke tests pass.
- **A5 — Upstream maintenance:** security-release monitoring, documented
  rebases and minimized patch delta; propose general fixes upstream.

## Acceptance gates

All changes require macOS CI for iOS Simulator build/tests where applicable,
real iPhone FLAC/Opus playback QA, correct pause/next/seek/gapless/route
behavior, source and binary license audit, and a rollback plan. **No automatic
merge or deployment to Trop.**

## Attribution

ApoloFFmpeg is **not the official FFmpeg project**. It incorporates LGPL
FFmpeg and third-party software. Preserve `LICENSE`, `LICENSES/`, original
copyright notices, and the source attribution to
`superuser404notfound/FFmpegBuild`. Review FFmpeg trademark guidance before
any external branding or distribution.
