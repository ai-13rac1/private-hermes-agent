# Browser automation and model Python inside the SSH executor

Status: implemented and qualified on Docker Desktop ARM64; final combined
independent acceptance is pending. The complete browser, desktop/network and
webapp regressions have passed, including harness Tor outage/recovery,
native cache sync, missing-harness recovery and actual Chromium sandbox layers.
BU-DESIGN was independently accepted. Follow the
[planning workflow](../planning-workflow.md). Planning baseline: branch `main`,
commit `e33e5ad5f741dc8ae283be32038e3bca25e041fa`.
Plan path: `docs/plans/browser-use-support.md`.
Implementation baseline: branch `browser-use-support`, commit `0a97899`.

## Intent and current behavior

Provide browser automation without executing model-written Python beside Hermes
state. The user requested this design and interim disabling of unsupported
browser/desktop tools. The user has now authorized implementation. Reuse the
single `COMPUTER_USE_ENABLED` preference for computer and browser tools; do not
add a browser-specific preference. Remove exclusions only for qualified routes.

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
The implementation now enables only `browser_exec` alongside `computer_use`
when the shared preference is on and actual SSH dependencies are available.
CDP/dialog/vault tools remain excluded. The lean variant excludes both tools.

## Progress inherited from computer use

Reconciled against completed computer-use work through `edd8186` and the same
packaged Hermes source revision. This is shared prerequisite evidence, not
acceptance of BU-DESIGN, BU-1 or BU-2:

- The optional Debian desktop image, SSH runner integration and existing
  `COMPUTER_USE_ENABLED` preference are implemented. Chromium runs with namespace
  and seccomp sandbox layers, without sudo elevation, writable system mounts or additional
  container capabilities. Reuse the desktop-only syscall profile; browser work
  has not demonstrated a need for further capabilities or syscall allowances.
- ARM64 fixtures passed desktop actions, browser-profile/localStorage/cookie
  persistence across image switches and restart, SSH dependency failure/recovery,
  and Tor allowed/forbidden paths, including UID-101 impersonation and outage.
  These establish a working desktop substrate. They do not qualify harness
  dependencies, arbitrary model Python, browser sessions or download handling.
- Authenticated same-origin screenshots and native RFB transport passed origin,
  ticket, takeover and private-mode browser-network checks. Reuse that transport
  if a streamed screen is needed. Harness screenshot paths, attachments and
  downloads still require their own transfer and rendering qualification.
- Chromium sandbox startup/discovery fixes and a webapp logout-test navigation
  race were resolved during computer-use qualification. They did not implement
  browser-harness relocation or enable any browser tool. The native browser CLI
  and screenshot launcher remain unchanged by this project's source patches.

See the [maintained evidence and limits](../development.md#executor-desktop-qualification).
Only one active default-profile desktop is qualified; concurrent profile screens
can collide on native display `:20` and the shared browser profile. Named harness
sessions must be traced rather than assumed to provide separate desktop profiles.
Full visual noVNC-pane interaction remains unqualified. Rootless Podman testing
belongs to its [own plan](rootless-podman.md).

The implementation moves Python as well as Chromium, rejects native gateway-local
and external-route fallbacks, and preserves native session, approval and output
contracts through the reviewed route below. The next action is final independent
acceptance against the passing runtime evidence and maintained guides.

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
  and AMD64. Reuse the implemented
  [desktop image contract](../configuration.md#optional-executor-desktop), observing
  its [qualification limits](../development.md#executor-desktop-qualification).
  Qualify the browser-specific image requirements on available targets and record
  gaps. Preserve AMD64-compatible inputs and launch paths; missing AMD64 runtime
  qualification does not block this plan's completion or establish AMD64 support.
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

### Current implementation evidence

Both images build reproducibly; 92 unit tests and twelve packaged networkless
policy combinations passed. A fresh read-only implementation review identified
replacement-owner IPC reuse, native literal/default tab sharing and EOF during
daemon startup; each was corrected before final qualification. Focused ARM64
checks pass remote stdlib/child execution, navigation/DOM/type, separate named
and unnamed tabs, concurrent cold startup, screenshot staging/native vision,
downloads, takeover denial, active-child cancellation, timeout/retry and native
cleanup. Model processes retain runner identity, empty effective/permitted
capabilities and no-new-privileges. The complete desktop/network run also passed
host/VM/private, UDP/IPv6 and embedded-DNS denial, SSH execution, exact MCP grants,
UID-101 Tor routing, image switching and actual harness Tor outage/recovery.
The corrected-image browser suite passed as Hermes UID 10000, including actual
native cache round-trip, startup cancellation, abrupt owner death and isolated
missing-harness refusal/restoration. Webapp qualification passed; final independent
acceptance remains pending.

Final qualification exposed a concrete native bulk-sync interaction:
Chromium's unmapped browser profile was archived before native sync-back selected
allowed mappings, and its absolute `SingletonSocket` symlink failed safe tar
extraction. The narrow SSH patch excludes exactly that persistent profile from
the archive; ordinary selected files and native safe extraction are preserved.
The profile is not deleted. A fresh independent reviewer accepted this correction;
corrected-image native cache round-trip passed. Running new fixtures through the
handler as container root also created an incorrectly owned native install lock;
the fixtures now use actual gateway UID 10000. Fresh webapp qualification passed
after those corrections: all 24 existing content cases, eight screen and eight
browser-result mode/ingress cases, and the remaining auth/restart/privacy/failure
fixtures passed. A focused check also verified actual automation Chromium's
sandbox layers. Final review acceptance remains pending.

The existing image-switch regression once failed its `file://` localStorage
assertion and passed an isolated repeat. The fixture now tests storage and an
HTTP-only cookie at a stable loopback HTTP origin rather than relying on file
origins. The complete regression passed with that fixture. This is a fixture
change; do not claim a production persistence fix.

### Accepted implementation decisions

A fresh read-only BU-DESIGN reviewer inspected the exact packaged Hermes source
and the SHA-256-verified locked browser-harness 0.1.13 wheel. Design acceptance
requires the following scoped implementation and runtime evidence:

- Initially enable only `browser_exec`; keep `browser_cdp`, `browser_dialog` and
  `browser_vault` excluded. Native raw CDP/dialog routes use gateway connections
  and a gateway supervisor; exposing them is separate work. The harness's CDP
  helper already runs within executor Python and needs no separate endpoint.
- Package a minimal isolated harness environment in the desktop executor. The
  wheel requires Python >=3.11; its metadata supports the existing Python 3.13.
  Hermes's Python >=3.14 dependency marker does not require another interpreter.
  Use the packaged lock's transitive versions/hashes, including its explicit
  Pillow 13 override, without installing the full Hermes runtime in the executor.
- Delegate the browser tool early to a narrow deployment helper. One persistent
  SSH stdio launcher per harness identity owns the native daemon and runs each
  model program in a separate executor process group. Serialize calls per identity,
  separate child output from control messages, and use the existing native
  owner-death supervisor for the local SSH process group. EOF/timeout/interruption
  stops the affected remote execution and daemon; never replay uncertain actions.
  Already-issued Chromium actions may have completed and must be reported as such.
- Use explicit remote display/CDP/runtime/workspace/telemetry values before harness
  imports, with `BH_REQUIRE_EXISTING_DAEMON=1` after serialized daemon startup.
  Workspace `.env` and `agent_helpers.py` remain executor code/data. Use native
  dedicated named tabs; do not prepend the redundant own-tab program that changes
  traceback lines and leaves an extra tab outside daemon ownership.
- Retain native browser-session and desktop approval/takeover/idle ownership.
  Reject cloud/CDP override/real-profile/alternate-engine routes before launching;
  constrain the local creation path to sandbox Chromium. Remove explicit browser
  sandbox-bypass extra arguments found in `browser_session_sandbox`, as the prior
  desktop patch only corrected the dock launch. Read CDP addressing inside the
  executor; never pass the gateway's forwarded endpoint to remote Python.
- Hook native per-session cleanup to close its harness owner: Chromium death alone
  does not stop this harness daemon. Refresh native session activity while an
  execution is active so the idle janitor cannot reap valid ongoing work.
- Transfer screenshot candidates only from the executor through native bounded
  file transfer to a generated Hermes cache destination. Never stat/open a printed
  path on the gateway. Preserve native screenshot helpers, redaction and vision
  attachment; downloads remain executor workspace files accessible through the
  existing authenticated remote file APIs. Qualify those consumers and malicious
  path cases rather than adding another download service.

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
Record tested architectures and preserve the ability to qualify AMD64; do not
infer runtime support from a multiarch manifest or block completion solely on
unavailable AMD64 runtime coverage. Rootless Podman acceptance remains with its
own plan.
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
tested architecture coverage, preserved AMD64 compatibility, and allowed/forbidden
plus failure/restart evidence. Record unavailable platform coverage explicitly.
Resolve material findings before claiming support. After acceptance, preserve
lasting evidence and limits in maintained guides, resolve plan links and remove
this plan according to the planning workflow.

## Related plans, deferrals and rollback

The implemented [optional desktop](../configuration.md#optional-executor-desktop)
provides structured driver actions independently of browser Python relocation.
Reuse its executor desktop rather than introducing another desktop lifecycle.
Reconcile the [capability-reduction plan](capability-reduction.md)
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
