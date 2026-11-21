# Moving ApoloFFmpeg into its own repository

**Status (21 Nov 2026):** staged in `Mosas123/FFmpegBuild`, branch
`bootstrap/apolo-ffmpeg-20261121`, based on `apolo-union`. The future
`Mosas123/ApoloFFmpeg` repository does **not** yet exist. These steps are a
planned migration; do not imply an import, release or consumer switch happened.

## The one account-owner action (works from iPhone)

The linked GitHub app can write files/branches/PRs but cannot create
repositories. Use GitHub's official [Importer](https://github.com/new/import)
in a mobile browser, signed into the `Mosas123` account:

1. **Source repository URL:** `https://github.com/Mosas123/FFmpegBuild.git`
2. **Owner:** `Mosas123`. **New repository name:** `ApoloFFmpeg`.
3. **Visibility:** public, as the source distribution is public and its
   third-party licenses and source/patch provenance need to stay available.
4. Import the repository with its Git commit history. GitHub Importer does
   **not** copy issues/PRs; it also does not transfer Git LFS objects. Verify
   binary files and every needed branch after import.
5. Check imported branches `apolo-union` and
   `bootstrap/apolo-ffmpeg-20261121`. The old repo's default `main` is not
   the desired Apolo baseline: choose `apolo-union` as default **temporarily**
   and check the bootstrap branch independently.
6. Once its read-only baseline CI succeeds, create an **Apolo-owned**
   `main` from the verified `apolo-union` state (not from the original
   fork's unrelated `main`). Only then plan branding/renaming. Avoid
   overwriting branches or tags until the import is verified.

Alternative for an environment with terminal access: GitHub's
[repository-duplication guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository)
uses `git clone --bare` and `git push --mirror`. GitHub Importer is
recommended here because the project owner currently uses a mobile device.

## Post-import technical checklist

- [ ] Repo exists independently (not another fork of the upstream project).
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
