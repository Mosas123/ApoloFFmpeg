<h1 align="center">ApoloFFmpeg</h1>

<p align="center">
  <strong>FFmpeg for ApoloEngine — built for Apple's media platforms.</strong><br>
  Upstream-powered multimedia libraries, carefully packaged for native iOS, tvOS, macOS and visionOS integration.
</p>

<p align="center">
  <a href="https://github.com/Mosas123/ApoloEngine">ApoloEngine</a> ·
  <a href="https://github.com/Mosas123/FFmpegBuild">Previous distribution</a> ·
  <a href="https://ffmpeg.org/">FFmpeg upstream</a> ·
  <a href="LICENSES/README.md">Third-party licenses</a>
</p>

> [!IMPORTANT]
> **Independent distribution · migration in progress.** ApoloFFmpeg is not the official FFmpeg project and is not yet a drop-in, separately versioned replacement for ApoloEngine's production dependency. The imported `apolo-union` baseline uses existing `Aether*` SwiftPM products and binary names. We will preserve those until a separately tested consumer migration is ready.

## Why ApoloFFmpeg?

**Decode what Apple does not; let Apple handle what Apple does best.**

ApoloFFmpeg is a maintained, FFmpeg-based distribution for [ApoloEngine](https://github.com/Mosas123/ApoloEngine). Its purpose is to extend media format support **without replacing iOS's audio infrastructure**.

- **FFmpeg** provides demuxing, parsing, software decoding and resampling where needed.
- **AVFoundation / Core Media** handle Apple's supported rendering and timeline interfaces in the consuming engine.
- **URLSession** supplies HTTP transport to custom FFmpeg AVIO callbacks; FFmpeg's built-in network stack is disabled in this build.
- **AudioToolbox / VideoToolbox** remain available for supported platform-specific processing and hardware acceleration.
- **ApoloEngine** owns playback orchestration, audio session interaction, DSP, gapless behavior, and interruption/route handling.

This is an architectural division of responsibilities, **not** a claim of universal Atmos, DRM, AirPlay, lossless-output or hardware decoding support. Actual behavior depends on the codec, operating system, output device and publicly available Apple APIs.

## Current baseline

| Area | Imported distribution |
| --- | --- |
| Upstream FFmpeg | `n8.1.3` (pinned in `build.sh`) |
| Additional libraries | dav1d 1.5.4, zimg release-3.0.6, libzvbi v0.2.46 |
| Packaging | Dynamic XCFrameworks consumed through Swift Package Manager |
| Apple platforms | iOS, tvOS, macOS and visionOS; device and simulator slices |
| Included | `libavcodec`, `libavformat`, `libavutil`, `libswresample`, `libswscale`, `libavfilter`, dav1d, zimg and libzvbi |
| Network / executable | No FFmpeg networking/TLS stack; no `ffmpeg`, `ffplay` or `ffprobe` CLI executables |
| Build provenance | `BUILD-INFO.txt`, pinned upstream sources, local patches, configure flags, dSYMs |

The current full build includes both **audio and video** support inherited from FFmpegBuild. A smaller audio-only distribution is a **future experiment**, not an implemented or benchmarked product.

### Media support

The shipped build includes decoders and demuxers for formats such as **FLAC, Opus, Vorbis, AAC, ALAC, MP3, PCM, AC-3, E-AC-3, DTS, TrueHD and Matroska/WebM**, plus video/subtitle functionality needed by other consumers. Inclusion of a decoder does not guarantee that every profile, bitstream, container or protected source will play on every Apple device.

### Compatibility notice

The imported `Package.swift` declares an **iOS/tvOS 16** deployment floor, but the bundled iOS/tvOS frameworks currently report **`MinimumOSVersion=26.0`** in their `Info.plist` files. Compiler targets and embedded framework metadata must be reconciled and verified against Mach-O load commands and supported deployment targets **before** any wider compatibility claim or new release. This inconsistency was inherited; no metadata has been silently changed.

## Integration with ApoloEngine

ApoloEngine currently uses the production baseline from:

```text
https://github.com/Mosas123/FFmpegBuild
branch: apolo-union
```

The imported ApoloFFmpeg repository contains that same source history and its `apolo-union` branch, but **ApoloEngine and Trop have not been switched**. The migration will use a tested, pinned release or commit with a straightforward rollback.

> [!NOTE]
> The imported `Package.swift` still names the package `FFmpegBuild`, and the products/frameworks still use `AetherFFmpegBuild`, `AetherLibavcodec`, `AetherLibavformat`, etc. They are compatibility names, **not** the final Apolo branding. Do not rename `.framework` bundles or SwiftPM products without rebuilding, reviewing install names, and updating consumer imports in a coordinated change.

## Build from source

The imported build script uses Xcode, the Apple SDKs and standard cross-compilation tools. Run on a supported macOS build runner:

```bash
./build.sh
```

Other supported script options inherited from FFmpegBuild:

```bash
./build.sh package                 # Package existing compiled outputs
./build.sh clean                   # Clear generated build products
./build.sh --without-dtsx-heights  # Omit the optional DTS:X heights patch
```

`./build.sh static` is also present for specialized consumers with their **own** LGPL compliance plan. The distributed baseline uses **dynamic** frameworks.

For auditing the imported binaries (no compilation required):

```bash
python3 Scripts/validate-apolo-baseline.py --report-json apolo-baseline.json
```

The baseline audit checks SwiftPM product paths, Apple framework slice metadata, embedded binaries, licensing and source provenance. It warns about the inherited minimum-OS mismatch. Use `--strict-deployment` to fail on such warnings.

**Builds, signatures and tests require independent validation on each Apple platform.** The audit itself is not proof of runtime compatibility or bit-perfect playback.

## Roadmap

| Stage | Focus |
| --- | --- |
| A0 — Preserve | Import provenance, patches, licenses, existing binary names and baseline behavior |
| A1 — Validate | Reproducible builds, Apple slices, signing, dSYMs, SwiftPM resolution and deployment targets |
| A2 — Integrate | AVIO cancellation, safe ownership, EOF/seek/interruptions and native Apple playback contracts |
| A3 — Optimize | Measure optional audio-focused codec profile, memory, CPU, energy, package size and latency |
| A4 — Migrate | Pin an ApoloFFmpeg release in ApoloEngine; verify Trop on physical iPhone; preserve rollback |
| A5 — Maintain | Track FFmpeg/security updates, minimize local patches, submit general fixes upstream |

See our [technical charter](docs/APOLOFFMPEG_CHARTER.md), [migration and release gates](docs/APOLOFFMPEG_MIGRATION.md), and the [A1 macOS portability blocker](https://github.com/Mosas123/ApoloFFmpeg/issues/2). This release remains unvalidated until both iOS and macOS packaging gates pass.

## Upstream, patches and attribution

ApoloFFmpeg is derived from [superuser404notfound/FFmpegBuild](https://github.com/superuser404notfound/FFmpegBuild), maintained in our previous [Mosas123/FFmpegBuild](https://github.com/Mosas123/FFmpegBuild) fork. **We did not author upstream FFmpeg or the inherited FFmpegBuild distribution.** Their copyright notices, authorship and code history remain intact.

- The original imported README, including its detailed decoder matrix, build instructions, local patch inventory and original maintainer credits, is preserved as [FFmpegBuild upstream documentation](docs/FFMPEGBUILD_UPSTREAM_README.md).
- `build.sh`, `patches/` and `BUILD-INFO.txt` document the actual source modifications, versions and build configuration.
- FFmpeg upstream: [ffmpeg.org](https://ffmpeg.org/).
- This distribution does not represent, endorse or speak for the official FFmpeg project.

### Licensing

FFmpeg libraries in this build are configured under **LGPL-2.1-or-later**; bundled components have their own licenses. See [LICENSE](LICENSE) and [LICENSES/README.md](LICENSES/README.md), and retain applicable copyright notices and license texts when redistributing.

Dynamic linking helps support the LGPL library-replacement/relinking requirements, but is **not** a substitute for all distribution obligations. Source availability for the exact build, attribution and other conditions still apply. Consult legal counsel for production distribution decisions when needed.

---

<p align="center"><sub>ApoloFFmpeg · An independent FFmpeg distribution for the ApoloEngine ecosystem · Built on upstream open-source work.</sub></p>
