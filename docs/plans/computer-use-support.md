# Computer use inside the SSH executor

Status: proposed; no desktop dependencies or computer-use capability enabled by
this plan. Follow the [planning workflow](../planning-workflow.md).
Planning baseline: branch `main`, commit
`e33e5ad5f741dc8ae283be32038e3bca25e041fa`. Plan path: `docs/plans/computer-use-support.md`.

## Intent and current behavior

Enable structured desktop actions entirely inside the existing SSH executor.
The user requested this future design alongside disabling unsupported executor
browser and computer-use tools. In-browser previews separately follow
`WEBAPP_EXTERNAL_CONTENT` and are available only in `browser_native`. This plan
does not authorize executing these phases or removing the executor exclusions.

The selected Hermes v0.23.0 source is
`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`, packaged by
`components/hermes/Dockerfile`. Its `computer_use` tool accepts structured capture,
click, type, scroll and key actions, not model-written Python. Native
`tools/bot_desktop/placement.py` follows `terminal.backend: ssh`; native stream
helpers run `cua-driver mcp` and the desktop inside that SSH backend. The current
Alpine executor lacks Xvnc, Xfce, Chromium and the compatible driver environment.
Native documentation states that cua-driver has no musl build. A Python package
or a host-side driver alone does not establish executor support.

The independently published `nousresearch/hermes-sandbox:desktop` image includes
the desktop and driver. Registry inspection on 2026-11-11 found Linux ARM64 and
AMD64 at index digest
`sha256:c7d8607d076f26a64e0bd6828f74e1764af43fe3281368188459bb693bfa7567`.
This is candidate availability evidence, not package, filesystem or runtime
qualification. Its published revision may differ from the pinned Hermes source;
inspect both before selecting it.

## Intended design and preserved boundaries

Keep one executor service, its existing namespace, pinned SSH identity and
unprivileged runner UID/GID 10000. First evaluate deriving that executor from the
pinned desktop image and adding the existing SSH server configuration. Align the
image's `pn` account with `runner` during the build, remove its passwordless sudo
grant, and qualify native desktop user selection over SSH. Retain the current
workspace/home mounts and their ownership. If the candidate cannot meet these
contracts reasonably, build the required desktop packages on a small glibc base;
do not introduce a second executor, desktop service or runtime installer merely
to avoid adapting the owning image.

Reuse Hermes's native SSH stdio streams for the driver and, if supported by the
webapp, authenticated screen transport. The screen and its X/DBus sockets,
Chromium profile, cookies and temporary files belong inside the executor. Hermes
keeps orchestration and result presentation only. Model actions may open a
terminal and type commands; these must still affect only the executor.

Preserve all accepted [architecture boundaries](../architecture.md): no agent,
provider, wallet or host mounts in the executor; Tor-only public TCP and DNS;
denial of direct egress, unsupported UDP, non-loopback IPv6, host/VM/private
targets and unintended peers. Keep exact SSH, inference and MCP grants. No Docker
socket, host networking, privileged application container, X11/SSH forwarding or
additional published VNC/CDP port. Do not switch `bot_desktop.placement` to
`gateway` on dependency or connection failure. No new quotas, lifecycle records,
supervisor or recovery framework; use native desktop lifecycle where qualified.

This remains one shared executor, not per-task or per-profile security isolation.
Browser logins are sensitive executor state and need a documented persistence and
backup choice. Preserve current data and identities on retries, rebuilds and
ordinary shutdown; do not delete a browser profile to repair readiness.

## Decisions required before implementation

- Inspect the selected image, architecture-specific driver/browser versions,
  native SSH user switching, writable paths and capability needs. Keep the
  executor root listener's existing narrow privilege-separation contract; do not
  grant sudo or extra application capabilities to satisfy a desktop startup.
- Establish native `computer_use` availability checks against actual executor
  requirements. Missing binaries/display/SSH must produce a scoped reason and
  keep the tool unavailable; Hermes-host binaries are not corroboration.
- Trace authenticated webapp Bot Screen routes, frames and screenshot responses
  against the existing private-content policy and CSP. Prefer same-origin screen
  pixels over active web previews; if that surface cannot be qualified, deliver
  authenticated captures and explicitly defer interactive viewing.
- Decide the driver permission mode and native approval/human-takeover behavior.
  Preserve native financial/user approvals; fixture approval is not permission
  to use real accounts, logins, payments or funded tools.

Gate CU-DESIGN: fresh independent read-only review of the selected design, exact
image/source pins, affected consumers and focused experiments before substantive
implementation. Resolve material findings before dependent work.

## Implementation phases and acceptance

### CU-1: executor desktop and structured actions

Adapt `components/executor/Dockerfile` and existing SSH startup only as required;
update `components/hermes/` availability/disablement hooks narrowly for
`computer_use`. Leave executor browser tools disabled and preserve the separate
preview mode gate. Package dependencies
at build time and retain native driver transport. Use disposable executor/home
state to verify capture, click, type, scroll and key actions; create a marker via
a terminal in the executor desktop and prove it cannot access agent/host/wallet
canaries. Check process UID, capabilities, mounts, display/socket placement and
driver execution on both advertised architectures. Image manifest support alone
does not qualify the other architecture.

Run effective Compose validation if Compose changes. Extend existing focused
SSH/network checks for allowed public Tor access, denied private/internal/host
destinations, no provider/MCP access, and Tor loss/recovery without direct
fallback. Qualify SSH disconnect, missing display/driver, executor restart and
recreation, native idle stop, retry and state preservation. Distinguish valid
slow Tor progress from connection or response inactivity; retain native budgets
unless a demonstrated failure requires a scoped change.

Update `docs/architecture.md`, `docs/configuration.md` and
`docs/updates-and-plugins.md` with placement, persistence, image/patch contracts
and diagnosis. Commit coherent passing work and independently review this
meaningful boundary change before enabling a user-facing surface.

### CU-2: supported webapp surface and final qualification

Qualify the chosen authenticated capture/screen surface with dummy inference and
disposable GUI fixtures. Verify unauthenticated rejection, exact host/origin
checks, browser network canaries in private modes, display tickets, takeover,
stale sessions and dependency loss. No external resource fetch may be introduced
by the viewing browser. Keep the established private-preview fallback and
external-content ceiling intact. Update `docs/webapp.md` with supported behavior,
platform coverage and practical limits; link from the README only if operator
setup needs a new user-facing entry point.

Gate CU-FINAL: a fresh independent read-only review of the combined commits,
allowed/forbidden runtime evidence, both intended CPU targets, maintained guides
and failure/restart behavior. Missing platform or surface checks remain pending;
do not claim support from source inspection. After acceptance, move lasting
evidence into maintained guides, resolve plan links and remove this plan using
the planning workflow.

## Related work, deferrals and rollback

[Browser use](browser-use-support.md) may reuse the qualified executor desktop,
but must separately relocate model-written Python before enabling `browser_exec`.
Computer use need not wait for that browser harness work. `desktop_preview`,
`drive_preview` and `annotate_preview` target the viewer's preview renderer and
are independently available in `browser_native`, not disabled by the executor
policy. They are not an executor screen or evidence of isolated computer use.
Preserve that explicit browser-origin opt-in and its private-mode restrictions;
their [interactive-content plan](webapp-interactive-content.md) must not use
viewer-side loading as a substitute for executor isolation.
Reconcile the [capability-reduction plan](capability-reduction.md) if image or
startup changes affect its executor inventory; do not claim its gates passed.

Cloud desktops, host/gateway desktop control, per-task sandboxes, browser vaults,
changes to preview policy, live Funnel enrollment and real-account operations
are deferred. This plan authorizes none of those operations. Rollback restores
the tool exclusion and prior image/startup configuration while preserving keys,
workspace, home and any established browser state. Preserve incompatible state
for deliberate repair; do not silently initialize or discard it.
