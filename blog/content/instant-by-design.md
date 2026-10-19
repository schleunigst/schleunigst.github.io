---
title: Instant by Design
dek: A design paper for instant_barcode_scanner — what two benchmark campaigns imply for a Flutter scanning package: session-scoped camera lifetimes, states priced in milliamps, truthful completion, and the parts we would refuse to build.
author: Schleunigst
org: Schleunigst
status: Design paper, implemented
date: 2026-10-19
slug: instant-by-design
sections:
  - The package the measurements asked for | The thesis, in bullets
  - Who this is for | A litmus test, not a mobile_scanner replacement
  - What the audit found | Reading the incumbent's lifecycle in source
  - The paths we rejected | Five ways to build it, four rejected on evidence
  - States are the API | The lifecycle, priced in milliamps and milliseconds
  - Mechanism in native, policy in Dart | The maintainability bet and the size budget
  - Truthful completion | Concurrency rules and the NFC handoff proof
  - The package, concretely | Name, ML Kit, iOS posture, and the API
  - Open questions | What would falsify this design
  - Sources | Contracts, source locations, and the repository
---

The previous two entries were measurements. The [first](../the-camera-was-never-slow/) fixed a blank second by keeping one camera warm for the app's lifetime; the [second](../warm-not-awake/) priced every way a camera can be held ready and found the state that is fast, dark, and half the power of streaming. This entry is different in kind: it is the design paper for the package those measurements imply. It was written before any of it existed, while the design could still be argued with. It has since been argued with and built: the repository is at [github.com/schleunigst/instant_barcode_scanner](https://github.com/schleunigst/instant_barcode_scanner) and the pub.dev page goes up with the first release. Where reality insisted — the handoff race below, the screen-toggle spam a host app produces — the code changed the paper's wording, not its shape; the addendum marks those places.

<figure class="hero-figure">
  <img src="../static/figures/state-machine.svg" alt="State diagram of four camera states with measured costs: closed at minus 165 milliamps, open at minus 197, parked (session held, repeating stopped) at minus 372 with the indicator dark, and live at minus 599 with the indicator lit. Forward transitions cost about 300 milliseconds to open the device, 0.4 to 0.8 seconds to configure the session, and 266 milliseconds to start repeating; stopRepeating returns to parked in about zero milliseconds and the indicator goes dark. An idle policy closes the parked state after a timeout.">
  <figcaption><span class="fig-num">Fig 1.</span> <strong>The lifecycle this package would expose.</strong> Four stable states, left to right, with measured steady-state currents and transition costs from the second campaign (Galaxy S24 FE, hot phone). Driving right costs time; driving left costs money and privacy. The parked state is the prize: a held session with repeating stopped, dark to the OS, and cheap to re-enter.</figcaption>
</figure>

## The package the measurements asked for

- **Session-scoped, not widget-scoped.** One controller lives for the app session; the camera lifecycle answers to the app, not to a widget's mount and unmount. Pages and dialogs ask the controller for a scan; they never own the camera.
- **The states are the API.** `closed → opening → open → parked → live`, with truthful completion on every transition. *Parked* — device and session held, repeating stopped — is the state the second entry measured at **266 ms resume, +207 mA over camera-off, indicator dark**.[^names]
- **The numbers are the requirements.** Resume under 300 ms after idle; release truthful within ~250 ms; battery math that finishes a nine-hour shift with charge to spare; ML decoding free in the stream path (Δ ≈ 7 mA, within noise).
- **Drop-in, or it will not be adopted.** One package, ML Kit included by default, a public analyzer SPI for everyone who wants something else. `flutter pub add instant_barcode_scanner`, and the first scan works.
- **Android first, iOS-ready by construction.** The public API, events, and capabilities are platform-neutral; nothing in the Dart policy assumes `camera2`. No iOS code until the Android contract is proven.
- **OSS from day one.** This paper precedes the code; the API is a public contract from 0.1.0.

## Who this is for

The litmus test is the shape of the session, not the app category:

| if your app… | reach for |
| --- | --- |
| shows a scanner page or modal, wants a result, moves on | [mobile_scanner](https://pub.dev/packages/mobile_scanner) |
| keeps a scanner hot across a shift, with reads arriving seconds to minutes apart | this package (when it exists) |

mobile_scanner is mature, well-maintained, and the right default for the first row — the audit below found limits, but they are lifecycle-shape limits, not regressions. This package is for the second row, where the camera is not a page you visit but a capability the session holds: checkout lanes, inventory walks, access points. The non-goals are everything else: no web or desktop, no attempt at barcode-format breadth, no overlay painter, no replacement of an ecosystem — one job, the camera device lifecycle across a session, done truthfully.

## What the audit found

We read mobile_scanner 7.4.2 from the pub cache, all ~2,200 lines of Android Kotlin and the ~7,400 lines of Dart around them.[^audit] The size is worth a sentence because it frames what "a new package" means here: the session controller and channel plumbing alone are ~2,000 lines, there is no pigeon anywhere (string-keyed method-channel maps), and most of the surface — overlay painters, web readers, format tables — is breadth this package would not reproduce. The lifecycle findings are the ones that matter:

- **`stop()` resolves long before the camera is free.** `stop()` (`MobileScanner.kt:609`) calls `releaseCamera()` (`:635`), which unbinds the use cases and releases the surface, and the handler answers `result.success()` (`MobileScannerHandler.kt:273`) in **4–11 ms measured** — while the OS did not report the camera available for **~1.29 s** in the first campaign's measurement. The API answers a different question than the one the caller is asking.
- **"Resume" is a restart.** The `resumeCamera()` path is commented out (`:626–633`) with a TODO at `:420–422`; there is no warm state to return to.
- **`isStopped()` is a null-field heuristic** (`:664`: `camera == null && preview == null`), not device truth.
- **CameraX underneath sets the ceiling.** CameraX manages repeating requests internally and exposes no `stopRepeating` equivalent. Pause means `unbindAll()`; resume means a full reconfigure. None of the middle "ready" states are expressible.

The conclusion that shaped everything below: the gap is not bugs, it is ownership. mobile_scanner models a *widget's* lifetime — the camera is open while a widget is mounted and torn down when it is not. The measurements want a package that models an *app session's* lifetime, where "warm" is a state the app chooses, prices, and governs.

## The paths we rejected

Five ways to build this, four rejected on evidence from the campaigns:

| path | verdict | why |
| --- | --- | --- |
| Vanilla mobile_scanner | rejected | 1.29 s true release, no park, camera held all session; measured in both campaigns |
| Fork-lite (patch mobile_scanner) | rejected | the CameraX ceiling still applies — no `stopRepeating` — plus a fork's merge tax |
| A "warm controller" that streams all session | rejected | measured −599 mA, 12.7 %/h: dies mid-shift, and lights the indicator the whole time |
| CameraX plus policy | rejected | every pause pays a full reconfigure; truthfulness still absent |
| **Raw `camera2` device + ML Kit decoder** | **chosen** | park resume 266 ms; parked −372 mA; closed 3.5 %/h; truthful release ~0.19 s; the P4 and p5 skeletons already exist |

The chosen row is the only one in which the measured golden path is expressible at all — and it is a commitment, not a free lunch: owning `camera2` means owning permission flows, device disconnects, and OEM behavior, all of which the skeleton apps so far have not exercised. That cost is the main risk in this design, and it lives in one module (§ mechanism/policy below).

## States are the API

The public lifecycle is a small set of stable states with transient edges; every transition is a measured quantity, not a guess:

| state | device | session | repeating | measured cost/evidence |
| --- | --- | --- | --- | --- |
| `closed` | — | — | — | −165 mA steady; 3.5 %/h |
| `opening` | opening | — | — | device open ≈ +300 ms over `open` (hot deltas) |
| `open` | open | — | — | reopen to frame: 658 ms cold / 1027 ms hot (n=8) |
| `parked` | open | configured | stopped | reopen 266 ms hot (250–295) / 280 ms cold; −372 mA |
| `live` | open | configured | on | −599 mA; 12.7 %/h |
| `closing` | closing | — | — | stop returns in ms; device free at ~0.19 s with availability callback |
| `failed` | — | — | — | carries the last stable state for recovery |

Policy is Dart-side and idempotent: `live → parked` immediately after a read burst; `parked → closed` after an idle timeout (the policy ladder from the second entry); `closed/parked → live` on a scan request; close on background; recover on disconnect. The LED behavior is part of the contract, not a side effect: `live` is the only state that lights the indicator, `parked` keeps the last frame frozen and the sensor quiet, and the README will say so in those words because users will notice.

## Mechanism in native, policy in Dart

One package, with a hard internal boundary:

```
lib/src/platform/   # states, events, capabilities, policy — pure Dart, testable headless
lib/src/android/    # pigeon binding to the camera2 mechanism
lib/src/mlkit/      # the default analyzer behind a public SPI
android/src/        # camera2 mechanism: one serial executor, no policy, ~600–800 lines
example/            # the drop-in demonstration app
```

The native side is deliberately thin and policy-free: open/close, session configuration, repeating control, frame-to-analyzer handoff, one serial executor. Everything a unit test can express without a camera — idle timers, park-vs-close decisions, event dedupe, handoff suppression, retry/backoff — lives in Dart. The p5 skeleton's `MainActivity` is 731 lines *including* bench scaffolding; the production core inside it is ~350–450, so the native budget below has evidence behind it.

The budget: **1,500–2,000 hand-written lines total**, against mobile_scanner's ≈11,700 shipped lines across four platforms (≈9,600 Dart + Kotlin alone; the rest is shared Darwin and a hand-ported web decoder). The point of the split is maintenance under churn. Flutter version bumps touch almost nothing — one `Texture`, pigeon bindings, plugin registration. OEM camera behavior varies inside `android/`, and where it varies in *time* (settle delays, park hysteresis) it surfaces as configurable policy in Dart, not constants compiled into Kotlin. A state machine that lives in Dart gets a unit test per transition in CI; the same logic scattered through camera callbacks gets an integration phone run per change.

## Truthful completion

The single hardest rule, and the one the audit's first finding is about: **futures resolve on confirmed state events, never on binder return.** `stop()` completing in 4 ms while the device stays busy for 1.29 s is exactly the lie this package exists not to tell. Concretely:

1. **One serial camera executor.** Every camera2 operation is queued there; callback ordering is the state machine's clock. No locks elsewhere.
2. **Target-state commands.** `driveTo(target)` converges; retargeting mid-transition is legal, idempotent, and cheap. Callers express where they want to be, not which verb to run.
3. **Snapshot events.** The platform emits state + capabilities + last error as whole snapshots; the Dart layer never has to reconstruct state from deltas.
4. **Named race rules.** The races already hit in the campaigns each get a policy: stop-while-opening retargets; hide-while-opening defers the close; double scan requests dedupe into one in-flight future; activity pause/resume re-drives the last target.

The NFC handoff is the proof of the thesis, because it is the case where the truth was the whole game. The contract: `beginNfcHandoff()` drives the scanner `closed`, waits for the `AvailabilityCallback` to declare the camera actually free (measured ~0.19 s with `camera2`, against 1.29 s of nominal-vanilla soak), applies a settle delay, and suppresses auto-resume; the app runs its reader session; `endNfcHandoff()` re-drives to the previous target. The scanner takes no NFC dependency and knows nothing about cards — it only guarantees release timing. Everything else in this design is an optimization; this is the part that makes the package honest.

*Addendum, 2026-10-19, from the build.* Two races the paper did not name arrived anyway, and each got its rule the same way: named, then ordered.

1. **Scan during a handoff waits, and times out only the scan window.** A host that navigates to the scan screen and calls `scan()` in the same frame as `endNfcHandoff()` must not race a handoff's close in flight. The scan joins the queue behind the handoff end; its timeout covers the scan window only, never the wait. An already-running scan that a handoff interrupts fails with a distinct `StateError` — the caller is told *why*, not just that it failed.
2. **A dispose reset cannot kill a warm-up behind it.** Host apps that tear their controller down per screen produce bursts where an old controller's `dispose()` lands in the call order after a newer controller's `warmUp()` has already fetched its texture id. The preview texture is engine-scoped, not controller-scoped: it survives a reset and dies only with the engine, so a burst of screen toggles ends settled on the requested state instead of throwing `configure_failed` at a controller that did nothing wrong. Every plugin-side command — including the activity-stopped close — joins one serialized queue; nothing retargets an in-flight drive out from under its caller.

Both rules exist because a burst-running device showed them: 40-cycle zero-sleep dispose and handoff toggles threw `ScannerException(configure_failed: preview surface is not available)` before the texture-ownership fix, and nothing after it. The regression tests are part of the repository.

## The package, concretely

**Name:** `instant_barcode_scanner`. The choice is marketing by search evidence: pub.dev ranks name matches hard (a deprecated `barcode_scanner` still leads "barcode scanner" results), and the length is proven in-category (`fast_barcode_scanner`, `lightweight_barcode_scanner` are fine). The name states the benefit — instant scanning — and keeps the keyword; the *warm* vocabulary stays in the README narrative, where it has a blog series behind it. Name and GitHub handles were checked free on 2026-10-17.[^name]

**Decoder:** ML Kit ships inside the package by default, unbundled variant (thin client; model via Google Play services), with a documented one-line switch to the bundled dependency for Play-free devices (~+2–3 MB per ABI).[^mlkit] The analyzer sits behind a public SPI — `setAnalyzer(...)` — so zxing-cpp or a custom pipeline is a supported swap, not a fork. Measured ML cost in the stream path was ≈ +7 mA, so there is no performance argument for splitting the decoder out; the argument for including it is that drop-in is the adoption lever on pub.dev, and every wiring step loses adopters.

**Result model:** small but byte-complete. Every hit carries `format` plus `rawBytes` — the payload exactly as encoded, passed through untouched from the decoder (Android `Barcode.getRawBytes()`, iOS `rawData`; ML Kit's `rawValue` is explicitly UTF-8-only, so bytes are the only honest carrier for everything else). Decoded text is best-effort convenience. Structured payload parsing — contact cards, Wi-Fi configs, calendar events — is future opt-in, not v1; a backend that works on raw payloads (ours does) never waits for it.

**iOS:** interface-only for v1. The API, events, and a `Capabilities` struct (`supportsPark`, `supportsTrueClose`, `supportsTorch`, …) are defined platform-neutral from day one; whether AVFoundation can park without teardown is an open research question. If it cannot, the capability is false and the Dart policy degrades gracefully to close/reopen — the same policy code, a worse ladder.

**Shape of the API** (sketch, not final):

```dart
final scanner = InstantBarcodeScanner();   // session-scoped

ValueListenable<InstantBarcodeScannerState> get state;
Stream<ScanEvent> get scans;

Future<void> warmUp();                     // drive to open/parked
Future<ScanResult> scan({Duration timeout});  // live, first hit, auto-park
Future<void> park();
Future<void> close();

Future<void> beginNfcHandoff();            // truthful release; resume suppressed
Future<void> endNfcHandoff();              // re-drive to the prior target
```

Pigeon carries the boundary: a host API of converging commands (`driveTo`, `setAnalyzer`, `getCapabilities`) and a platform-to-Dart event API of snapshots (state, barcodes, errors) — `FlutterApi` rather than the experimental `@EventChannel` annotation, which is what pigeon currently recommends for this shape.

## Open questions

A design paper should leave behind the list of things that could kill it:

- **OEM variance.** Every timing here comes from one device (SM-S721B). If park resume or release timing varies wildly across OEMs, the policy needs per-OEM calibration — or closed-loop adaptation (measure your own reopen, adjust the ladder). That is a research question, not a config.
- **`camera2` ownership debt.** Disconnect/recovery, multi-camera, permission edge cases: p5 never exercised them, and they are exactly where camera2 apps go to die. The budget assumes real time for this.
- **iOS park.** Whether AVFoundation has any honest equivalent of parked determines whether the iOS story is "the same ladder" or "close/reopen with a capability flag".
- **The adoption question.** If the hot-tab niche is just our product, internal-first would have been right; publishing makes that answer public instead of assumed.
- **Housekeeping, resolved in the build.** License: BSD-3, for the package and this site alike — the trace files shipped here carry the same notice. Repository: [github.com/schleunigst/instant_barcode_scanner](https://github.com/schleunigst/instant_barcode_scanner), branch model and quality gates written down in `CONTRIBUTING.md`. Maintainers: one, and the package is scoped so that stays honest.

What would falsify the design: if park resume cannot stay under ~400 ms across OEMs, the package narrows to a battery story; if mobile_scanner grows a `camera2` escape hatch and a park state, the wedge narrows to policy and truthfulness. Either would be a fine outcome — the measurements remain true either way.

## Sources

Every number above traces to the two campaigns and the audit; these are the contracts and the artifacts.

- **`camera2` session control** — [`CameraCaptureSession#stopRepeating()`](https://developer.android.com/reference/android/hardware/camera2/CameraCaptureSession#stopRepeating()) and [`#abortCaptures()`](https://developer.android.com/reference/android/hardware/camera2/CameraCaptureSession#abortCaptures()) are the parked state's primitive; the [device](https://developer.android.com/reference/android/hardware/camera2/CameraDevice) survives both.
- **Camera arbitration** — [`CameraManager.AvailabilityCallback`](https://developer.android.com/reference/android/hardware/camera2/CameraManager.AvailabilityCallback) is the truth source behind the NFC handoff timing.
- **Privacy indicators** — behavior documented with the [Android 12 privacy features](https://developer.android.com/about/versions/12/features#privacy-indicators); "frames, not handles" is the measured refinement from the second campaign.
- **ML Kit barcode bytes** — [`Barcode#getRawBytes()`](https://developers.google.com/ml-kit/reference/android/com/google/mlkit/vision/barcode/common/Barcode) on Android and [`MLKBarcode#rawData`](https://developers.google.com/ml-kit/reference/ios/mlkitbarcodescanning/api/reference/Classes/MLKBarcode) on iOS are the bytes contract; the iOS reference states `rawValue` is UTF-8-only and non-UTF-8 payloads require `rawData`.
- **Audited source** — [mobile_scanner](https://pub.dev/packages/mobile_scanner) 7.4.2, read from the local pub cache; line numbers are as of that version.
- **Campaign artifacts** — the design note is this paper; the power measurements are the [second entry](../warm-not-awake/) with raw traces [shipped with this site](../data/power/power_unplugged_9x80s.csv); the `p5_idle` skeleton stays in the private benchmark repository for now.

[^audit]: Audit copy: `~/.pub-cache/hosted/pub.dev/mobile_scanner-7.4.2`; Kotlin line references are as of 7.4.2 and will move in later versions.
[^names]: The second entry used bench names; the mapping is `open_nosession → open`, `idle_session → parked`, `stream → live`, `closed → closed`.
[^name]: Availability checked via the pub.dev package API and GitHub on 2026-10-17; availability is a snapshot, not a reservation.
[^mlkit]: ML Kit's barcode scanning ships as an unbundled client by default (model via Google Play services) or as a bundled dependency (~+2–3 MB per ABI) for Play-free devices; the package documents the switch, as mobile_scanner does.
