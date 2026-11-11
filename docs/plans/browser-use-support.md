# Browser automation and model Python inside the SSH executor

Status: proposed; executor browser tools remain disabled. Follow the
[planning workflow](../planning-workflow.md). Planning baseline: branch `main`,
commit `e33e5ad5f741dc8ae283be32038e3bca25e041fa`.
Plan path: `docs/plans/browser-use-support.md`.

## Intent and current behavior

Provide browser automation without executing model-written Python beside Hermes
state. The user requested this design and interim disabling of unsupported
browser/desktop tools. This plan is not authorization to execute its phases or
remove the interim exclusions.

Selected Hermes v0.23.0 source:
`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`; see the derived image in
`components/hermes/Dockerfile`. Native `tools/browser_use_cli.py` finds Hermes's
own interpreter and starts `browser_harness` via a local subprocess, sending
model code on stdin. Native `tools/browser_use_shot.py` adds helper functions
with a path-loaded launcher. Bot Desktop can put Chromium inside the SSH
executor, but that does not move the Python harness or its daemon there.
`bot_desktop.placement: terminal` alone therefore does not meet this plan.
The observed browser startup failure occurred before that execution because the
lean executor lacks the native desktop dependencies. The optional desktop variant
now supplies those packages under `COMPUTER_USE_ENABLED`; its computer-use
qualification does not qualify or relocate the model-written browser harness.
Executor browser tools remain disabled in both variants.

## Intended design and preserved boundaries

Use the existing SSH executor for Chromium, browser-harness, its Python daemon,
all model-generated Python, browser profiles, downloads and scratch files.
Hermes retains tool orchestration, native approvals and trusted result handling.
No model Python may execute in Hermes, including code that uses no browser
helpers or a different browser connection route.

Prefer the existing SSH backend's argv/stdio execution helpers and file-transfer
facilities. Add a narrow, revision-bound patch to the browser tool's launch and
result paths, not a new executor framework or alternate control service. Package
the harness, its locked dependencies and narrowly required public helper code
into the executor at build time. Do not mount the Hermes checkout, environment,
profile or agent data there or install dependencies automatically at startup.
Use an explicit small remote environment for display/harness paths, telemetry
defaults and executor-local browser addressing; do not copy Hermes's environment,
provider credentials or cloud-browser keys into the model process.

For the initial supported route, the harness and Chromium communicate locally
inside the executor. Keep CDP off published ports and do not widen executor
access to Hermes APIs, inference or MCP. A Python process outside the model's
SSH executor must not interpret code, even when cloud/CDP settings are changed.
Unsupported routes must fail visibly without selecting local Hermes execution,
cloud browsing, a real host browser or direct-network fallback.

Preserve the existing [architecture and isolation](../architecture.md): separate
Hermes/executor processes, mounts and namespaces; Tor-only public TCP/DNS; denial
of host/VM/private/unintended peer access, non-loopback IPv6 and unsupported UDP.
No host networking, Docker socket, privileged application container, provider or
wallet mounts, broad grants, SSH forwarding or host-browser CDP endpoint. The
executor remains shared between tasks/profiles, not a new tenant boundary.

## Design decisions and gate BU-DESIGN

Resolve these with exact packaged-source and disposable runtime evidence before
substantive implementation; obtain a fresh independent read-only design review:

- Select and pin the compatible harness/Python/Chromium image inputs on ARM64
  and AMD64. Reuse the desktop image contract from
  [computer use](computer-use-support.md) if it has passed CU-1; otherwise qualify
  the same required executor-image work here without assuming that plan ran.
  Reuse the existing lean/desktop choice; do not add a separate browser executor
  image or duplicate desktop lifecycle owner. Reconcile browser availability with
  that choice rather than introducing another overlapping image preference.
- Trace CLI and harness-daemon execution, named sessions, workspace overrides,
  profile paths, cloud/CDP/sidecar/real-profile routes, retries and cancellation.
  Choose the smallest supported route and explicitly reject the rest. A local
  client forwarding code to a Hermes-local daemon is not executor isolation.
- Preserve supported screenshot helper semantics and traceback line numbers.
  Audit every remote output consumer: stderr/redaction, screenshot detection,
  vision result attachment, native file APIs and downloads. Treat output and
  screenshot paths as untrusted executor data; reuse existing authenticated
  staging/file-transfer paths, without allowing remote output to select arbitrary
  Hermes files or introduce executable imports into Hermes.
- Decide native session persistence, daemon cleanup, retry and idle behavior.
  Cancellation must reach remote work without orphaning activity or killing
  unrelated sessions. Do not build a parallel process registry or add arbitrary
  work deadlines. Preserve browser profiles and useful completed downloads.
- Trace `browser_cdp`, `browser_dialog` and `browser_vault` separately. Re-enable
  CDP/dialog tools only when their endpoints and operations are executor-owned.
  Keep vault disabled until a reviewed credential flow meets the executor trust
  boundary; moving cloud/provider keys into the executor is not an acceptable
  shortcut. Native private settings are not permission to broaden that boundary.

## Implementation phases and acceptance

### BU-1: isolated harness and browser route

Package dependencies in `components/executor/`; patch native launch, environment,
daemon/session and result paths under `components/hermes/`. Follow the existing
derived-image patch/build procedure and copy every affected source file into the
final image. Tie patches to the packaged source, document removal conditions and
prefer an equivalent native capability if the selected upstream revision adds it.
Preserve the independent browser-native preview mode gate. Enable only the exact
executor browser tools whose
full execution routes meet the accepted design.

Use a controlled browser fixture and disposable data to verify navigation, DOM
read, click/type, named sessions, screenshots and downloads. Run model Python
that imports stdlib, spawns a child process and writes canaries: prove all run
inside the executor, cannot read agent/provider/wallet/host canaries, and cannot
reach forbidden services. Explicitly cover code without URL literals or browser
helper calls, changed cloud/CDP settings and stale sessions. Qualify screenshot
transfer and malicious/missing path handling with real file APIs. Successful
page navigation alone is insufficient evidence.

Extend focused SSH/network checks for public Tor access, denied private/host and
internal services, DNS, UDP/IPv6 and no direct fallback. Cover missing harness or
Chromium, invalid display, SSH interruption, Tor loss/recovery, cancellation,
daemon crash, executor restart/recreation and ordinary shutdown. Repeated setup
and retries preserve SSH identity, browser profiles and useful completed work.
Check both architectures; do not infer runtime support from a multiarch manifest.
Validate the effective Compose model if Compose changes.

Update `docs/architecture.md`, `docs/configuration.md` and
`docs/updates-and-plugins.md` for process placement, dependency ownership,
persistence, diagnosis, supported routes and narrow source patches. Commit
coherent passing work and independently review this execution-boundary change
before dependent UI integration.

### BU-2: webapp results and final combined qualification

Use the authenticated native file/image paths for remote screenshots and results.
Keep browser UI requests same-origin in private modes; execution inside the
executor does not authorize loading a remote website in the operator's browser.
Qualify result rendering, authentication/origin gates, output redaction, download
paths, stale tabs and dependency failure with disposable browser/network canaries.
Update `docs/webapp.md` and relevant operator instructions. A streamed view of the
executor's rendered pixels may reuse qualified computer-use transport; a live
iframe pointed at the destination URL does not satisfy this design.

Gate BU-FINAL: fresh independent read-only review of the combined revisions,
native discovery/direct/deferred/delegated execution consumers, maintained docs,
both intended architectures and allowed/forbidden plus failure/restart evidence.
Resolve material findings before claiming support. After acceptance, preserve
lasting evidence and limits in maintained guides, resolve plan links and remove
this plan according to the planning workflow.

## Related plans, deferrals and rollback

The [computer-use plan](computer-use-support.md) owns structured driver actions
and can be implemented independently of browser Python relocation. Share its
executor desktop work rather than making structured computer use depend on the
browser harness. Reconcile the [capability-reduction plan](capability-reduction.md)
for image/startup changes, without executing its unrelated phases.

`desktop_preview`, `drive_preview` and `annotate_preview` target the viewer's
renderer in the pinned source; they are available only in `browser_native`,
independently of executor tool exclusions. Their traffic uses the user's browser
connection. Preserve that opt-in and the private-mode restrictions; do not claim
these tools provide executor-isolated browsing. The
[interactive-content plan](webapp-interactive-content.md) concerns browser-origin
content and consent, not model Python placement, and must preserve this distinction.

Host/gateway browser control, external cloud browsers, real host profiles,
provider/cloud credentials in the executor, vault restoration, changes to preview
policy, live public ingress and real account/payment operations are deferred.
Fixture tests authorize none of these. Rollback restores tool exclusions and
prior images/patches while preserving workspace, home, SSH identities and saved
browser state. Report an incompatibility and deliberate repair action rather
than deleting private state or using a weaker execution route.
