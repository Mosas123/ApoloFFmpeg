# ApoloFFmpeg — migration status and release gates

**Verified 21 November 2026:** The independent [Mosas123/ApoloFFmpeg](https://github.com/Mosas123/ApoloFFmpeg) repository exists. Git history and branches `main`, `apolo-union`, and `bootstrap/apolo-ffmpeg-20261121` were imported. GitHub's default branch is `apolo-union`, which contains the ApoloFFmpeg README merged in PR #1. This is not a new binary release, and ApoloEngine still imports `Mosas123/FFmpegBuild`.

The account-owner import step has been completed. Preserve the old repository for rollback; do not repeat the import or create another fork.

**Known release blockers:**
- **Minimum OS**: the imported/staged binaries report iOS/tvOS `MinimumOSVersion=26.0`, but both `Package.swift` and their measured Mach-O `LC_BUILD_VERSION` say 16.0. The source-policy correction sets future packaging to 16.0. It is not retroactive: a new rebuild and independent strict-deployment CI must pass before publishing any corrected XCFrameworks; runtime support still requires device QA.
- On macOS, the imported `AetherLibavfilter.framework` was observed attempting to load `libswscale.9.dylib` using the original temporary absolute build path from `FFmpegBuild/build/thin/macos-arm64`. The full macOS test bundle could not launch in CI. This is **not** proof of an iOS runtime failure; resolve and rebuild packaging before claiming portable macOS binaries.
- The original FFmpegBuild macOS regression suite has not passed on a clean CI runner. Build success does not substitute for a test pass.
- **Build provenance:** the existing `BUILD-INFO.txt` is dated 16 November 2026, while the Apolo music-union `build.sh` was modified 18 November. The build script checksum in `BUILD-INFO.txt` must match the current `build.sh` before claiming the shipped binaries contain the current codec whitelist. Track in [issue #4](https://github.com/Mosas123/ApoloFFmpeg/issues/4).

## Post-import technical checklist

- [x] Repo exists independently (not another fork of the upstream project).
- [ ] `apolo-union` head, build script, 9 `Aether*.xcframework` outputs,
      `BUILD-INFO.txt`, dSYMs and `LICENSES/` match the source snapshot.
- [ ] `python3 Scripts/validate-apolo-baseline.py --report-json baseline.json`
      succeeds (the initial min OS mismatch is a **warning** until analyzed).
- [ ] iOS Simulator build and FFmpegBuild test suite pass against the actual
      shipped binaries; confirm device/simulator architecture coverage.
- [ ] Compare `otool -L`, `otool -l` (`LC_BUILD_VERSION`), `lipo -info`,
      `codesign --verify`, dSYM UUID and sample decode/seek results.
- [ ] Document native iOS/tvOS min OS support: `Package.swift` claims
      iOS/tvOS 16; embedded `Info.plist` says 26.0. This is pre-existing;
      do not assert iOS 16 binary compatibility without verifying Mach-O.
- [ ] Record source hashes, configure flags and patch inventory from
      `BUILD-INFO.txt`; retain unchanged FFmpeg and third-party copyrights.
- [ ] **No renaming binaries during import.** Keep `Aether*` module/product
      names until the ApoloEngine and Trop migration is tested in CI.
- [ ] Prefer an **immutable tag/commit** instead of a floating branch in
      ApoloEngine `Package.swift`; follow a distinct PR to switch the URL.
- [ ] Leave the older `FFmpegBuild/apolo-union` available for one full
      rollback cycle (or longer); do not delete existing binaries/branches.
- [ ] Confirm that the pre-existing ApoloEngine HTTP-cancellation draft PR
      #24 is fixed and green independently; it is **not** part of this
      extraction or new FFmpeg binary baseline.

## Development priorities after import

1. **Baseline parity** — exact current union behavior; no codec changes.
2. **Audio-oriented profile** — optional minimal whitelist for
   FLAC/Opus/E-AC-3/PCM/ALAC etc. Only after measuring IPA and CPU/RAM impact;
   keep shared union profile for video and other consumers.
3. **Native hardware gates** — use only public Apple APIs, opt-in per format,
   prefer Apple AVFoundation when it already handles the source correctly.
4. **Security & upstream** — document and minimize patch delta, monitor
   security fixes, test malformed media and resource limits.
5. **Consumer migration** — separate PR in ApoloEngine, then Trop smoke QA:
   local/remote FLAC, WebM/Opus, gapless, seek/pause/resume, radio,
   AirPods/AirPlay, interruptions, 60-second network stall and memory.
   Preserve existing playback when a feature is unverified.

## Project naming / license

Use **ApoloFFmpeg** as an independent distribution identity, with
“FFmpeg for ApoloEngine” as a description. State explicitly that it is
based on upstream FFmpeg and is **not** the official FFmpeg distribution.
`Mosas123/FFmpegBuild` was forked from
`superuser404notfound/FFmpegBuild`: preserve that attribution and the
`LICENSE`/`LICENSES/` texts, including FFmpeg LGPL and other libraries'
terms. Review the official FFmpeg trademark and licensing guidance before
shipping public branding.

## Rollback

At every point until the first validated ApoloFFmpeg release, ApoloEngine
continues importing `https://github.com/Mosas123/FFmpegBuild` on
`apolo-union`. If a new build fails compatibility/performance QA, stop
the migration and leave Trop untouched.
