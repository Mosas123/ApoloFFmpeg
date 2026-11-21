# ApoloFFmpeg — technical charter (bootstrap)

> **Status:** proposed independent repository `Mosas123/ApoloFFmpeg`. This file is staged on an isolated branch of `Mosas123/FFmpegBuild` until a separate repository exists. No production dependency has been switched.

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

## Verified initial baseline

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

**Important baseline inconsistency to audit before publishing a new release:**
`Package.swift` declares a minimum iOS/tvOS 16, while the currently packaged
iOS/tvOS framework `Info.plist` files declare `MinimumOSVersion=26.0`.
The build script sets those 26.0 values deliberately, even though its compiler
target is iOS/tvOS 16. Do not silently lower or raise these fields: determine
the effective supported deployment target, check Mach-O deployment load
commands on the actual binaries, and validate App Store deployment semantics.

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
