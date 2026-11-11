# Computer use inside the SSH executor

Status: implementation authorized; CU-DESIGN review and focused experiments are
in progress. No capability has yet been enabled. Follow the
[planning workflow](../planning-workflow.md).
Planning baseline: branch `main`, commit
`e33e5ad5f741dc8ae283be32038e3bca25e041fa`. Plan path: `docs/plans/computer-use-support.md`.
Implementation baseline: branch `computer-use-support`, commit `d5287db`.

## Intent and current behavior

Enable structured desktop actions entirely inside the existing SSH executor.
The user requested this future design alongside disabling unsupported executor
browser and computer-use tools. In-browser previews separately follow
`WEBAPP_EXTERNAL_CONTENT` and are available only in `browser_native`. This plan
is now authorized for implementation by the user; exclusions may change only
with the associated qualification below.

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

## Investigation findings and option rationale

Read-only investigation on 2026-11-11 established the following; no desktop
runtime or Podman qualification was performed:

- [Docker Hub tag metadata](https://hub.docker.com/v2/repositories/nousresearch/hermes-sandbox/tags/desktop)
  reported compressed image sizes of 1,192,327,731 bytes for ARM64 and
  1,203,999,297 bytes for AMD64 at the index digest above. The existing local
  ARM64 `private-hermes-executor:local` image reported an unpacked size of
  229,682,455 bytes. These are different measurements: the desktop download
  alone exceeds five times the existing unpacked executor. The desktop's
  unpacked footprint and the final adapted image sizes remain unmeasured.
- The pinned Hermes checkout's `docker/sandbox-desktop.Dockerfile` describes a
  glibc-based `nikolaik/python-nodejs:python3.13-nodejs26` base, TigerVNC, Xfce
  components, Playwright Chromium, Pillow and cua-driver 0.28.2. It grants `pn`
  passwordless sudo. This source inventory is not verification of every package
  in the independently published image. Moving from Alpine also changes libc
  and potentially language/runtime versions, beyond adding desktop packages.
- [Upstream Bot Screen documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-screen)
  reports approximately 220 MB for Xvnc/Xfce and another 0.5–1 GB for headed
  Chromium. These are upstream measurements, not this stack's resource profile
  or grounds for new limits. Native sandbox screens start on demand and have
  idle shutdown; installed packages need not imply a desktop running at boot.
- At the pinned Hermes revision, `tools/environments/streams.py` runs SSH
  streams as the configured SSH login; its user-selection argument does not
  switch SSH users. `tools/bot_desktop/sandbox_host.py` probes for `pn`, but that
  does not grant or require sudo over SSH. Qualify desktop execution as `runner`
  rather than adding a user-switching mechanism.
- The candidate Dockerfile seeds `/tmp/.X11-unix` and `/tmp/hermes-runtime`.
  The existing executor's `/tmp` tmpfs hides build-time contents there. Runtime
  directory creation/ownership, SSH environment propagation, X/DBus sockets,
  caches and Chromium shared memory therefore need focused qualification.

Retaining a lean executor saves meaningful download/disk space and installed
components for deployments without computer use. The setting itself is modest
work; qualifying both images, preserving state across switches and supporting
both engines are the material maintenance costs. Secondary privilege switches
would multiply configurations without a demonstrated desktop requirement.

## Intended design and preserved boundaries

Add one root `.env` preference, `COMPUTER_USE_ENABLED=false` by default. False
selects the lean executor image and keeps `computer_use` excluded. True selects
the adapted desktop executor image and permits `computer_use` only when actual
executor requirements pass native availability checks. A profile may still
exclude the tool. Enabling this preference must not enable executor browser
tools, alter browser preview policy or select host/gateway desktop placement.
Missing dependencies must report a scoped reason, never install at runtime or
fall back to a weaker placement.

Use a small explicit build-target or Dockerfile selection through Compose and
the existing deployment helper, whichever proves simplest. Pins stay in tracked
Compose/Dockerfiles, not `.env`. There is still one executor service, not two
services selected by profiles or a generic executor registry. Apply the selection
consistently to builds, startup, effective-model inspection, maintenance and
tests. A preference change takes effect through the documented rebuild/recreate
workflow, not hot switching or an extra persisted eligibility marker. False must
actually avoid building/selecting the desktop image, rather than merely hiding
the tool while retaining its image cost.

Keep one executor service, its existing namespace, pinned SSH identity and
unprivileged runner UID/GID 10000. First evaluate deriving that executor from the
pinned desktop image and adding the existing SSH server configuration. Align the
image's `pn` account with `runner` during the build, remove its passwordless sudo
grant, and qualify native desktop execution as the SSH login. Retain
`no-new-privileges`, the read-only root filesystem, the current workspace/home
mounts and their ownership, and the read-only SSH identity mount. Create only
demonstrated writable desktop paths through the existing home and runtime
mounts or narrowly scoped additions. Preserve the SSH listener's narrow
privilege-separation capabilities; desktop/driver/model processes remain
unprivileged. Do not expose sudo, root execution, writable-root or capability
choices as secondary preferences. If the candidate cannot meet these
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
Switching the preference in either direction must preserve those files, even
while desktop tools are disabled. Alpine/glibc and runtime differences may make
dependencies installed in persistent home unusable after a switch; qualify and
document specific incompatibilities and repair without clearing saved state.

### Tor UID matching and rootless Podman

The current Tor boundary does not depend on keeping the executor from assuming
Tor's UID 101. `components/network/network.py` redirects incoming executor TCP
in the gateway's `PREROUTING` chain without a UID exemption. Its UID-101 TCP
allow rule is in the gateway's `OUTPUT` chain, for sockets created locally by
Tor. An executor socket using UID 101 cannot claim that rule: process UID is not
carried in network packets, and the
[iptables owner match](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html)
applies to local sockets. The gateway also drops forwarding. Separate namespaces,
no executor direct uplink, no gateway access and absence of executor `NET_ADMIN`
and `NET_RAW` are essential. Container root alone does not restore capabilities
removed by the runtime. Retain no-sudo for its distinct restriction on authority
over executor processes/files; do not present it as the Tor-routing mechanism.

Coordinate with [rootless Podman support](rootless-podman.md): the desktop must
preserve the same contract on both engines. With Podman's default rootless UID
mapping, container root maps to the invoking host user and other UIDs map to
subordinate IDs. Rootless limits host authority but does not erase differences
between root and `runner` over accessible processes and mounted data. It neither
inherently requires removing container sudo nor justifies enabling it. Existing
`no-new-privileges` already prevents ordinary setuid sudo elevation; useful
system package installation would also conflict with the read-only root. See
[Podman rootless mapping](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md#understanding-root-inside-and-outside-a-container)
and [kernel privilege semantics](https://docs.kernel.org/userspace-api/no_new_privs.html).

No desktop/rootless incompatibility has been established. UID/bind ownership,
runtime/socket paths, shared memory and Chromium's own sandbox under nested user
namespaces, seccomp and AppArmor remain unqualified. A non-root browser is not
proof that its sandbox works. Do not preemptively grant sudo, broaden container
capabilities or disable browser sandboxing to make startup succeed. The two
engines and two executor images require coverage without optional security modes;
Podman support and its plan gates remain pending.

## Decisions required before implementation

- Inspect the selected image, architecture-specific driver/browser versions,
  native SSH login execution, writable paths and capability needs. Keep the
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

### Selected implementation and design evidence

Use independent Dockerfile targets `executor-false` (existing Alpine) and
`executor-true` (the pinned desktop index), selected directly by Compose from
`COMPUTER_USE_ENABLED`. Keep the existing executor image tag and service so
existing fixture consumers continue to use the selected build. Native Compose
`extends` may select the corresponding security options from a small root
Compose fragment; no extra running service or host selection framework is needed.

Independent read-only review of `d5287db` conditionally accepted this approach,
with four material upstream paths to correct before enabling: Chromium's dock
launch explicitly passes `sandbox_bypass=True`; replay-safe MCP errors can invoke
a gateway-local CLI driver; nonstandard driver permission modes create a local
embedded daemon; and refused display placement can still advertise/install host
packages or fall back to a host RFB socket. Use standard driver permission mode,
reject unsupported modes before daemon construction, refuse local CLI fallback,
and enforce SSH-only placement across tool and display paths. Preserve native
approval/lease semantics and outcome-unknown handling; do not replay mutations.

A networkless ARM64 Docker Desktop experiment with the pinned desktop image
confirmed Debian 13.7, Python 3.13.16, Node 26.11.1 and cua-driver 0.28.2.
Chromium failed with `No usable sandbox` under the existing default seccomp
policy; `unshare -Ur` was denied. A diagnostic with seccomp disabled isolated
the cause; disabling seccomp is not a deployment solution. The published
[Playwright seccomp profile](https://github.com/microsoft/playwright/blob/ae935a43d9e376e4759548f6b3c6905c7b282333/utils/docker/seccomp_profile.json)
allowed a sandboxed headless Chromium `about:blank` render with the executor's
existing SETUID/SETGID/SYS_CHROOT bounding set, non-root user, read-only root and
`no-new-privileges`. No capabilities were added. This is an early compatibility
experiment, not full browser sandbox, GUI, SSH or network qualification.

The desktop target therefore requires a tracked, pinned seccomp profile allowing
the user-namespace syscalls needed by Chromium, following Playwright's published
profile. Apply it only to the desktop executor; lean retains the engine default.
This adds syscall-profile maintenance and exposes user-namespace kernel paths to
executor code. It does not grant authority over the parent network namespace or
remove its firewall; verify those boundaries with allowed/forbidden runtime
checks. Reconcile the profile with engine upgrades and qualify Podman separately.
Keep its upstream source/license and removal conditions in maintained docs.

Host Teep currently occupies `127.0.0.1:8337`. Existing disposable fixtures
already publish Teep on an ephemeral port. For normal operation use the existing
`TEEP_HOST_PORT` preference to select a free port; do not silently omit publication,
change the internal inference route or select the host Teep as fallback.
No port-selection framework is needed.

## Implementation phases and acceptance

### CU-1: executor desktop and structured actions

Adapt `components/executor/Dockerfile` and existing SSH startup only as required;
update `components/hermes/` availability/disablement hooks narrowly for
`computer_use`. Add the preference to `.env.example` and explicit Compose
mapping; trace `scripts/deployment.py`, `scripts/stack.py`, setup/configuration
rendering, Make/build callers and focused test fixtures so image selection and
tool availability agree. Leave executor browser tools disabled and preserve the
separate preview mode gate. Package dependencies
at build time and retain native driver transport. Use disposable executor/home
state to verify capture, click, type, scroll and key actions; create a marker via
a terminal in the executor desktop and prove it cannot access agent/host/wallet
canaries. Check process UID, capabilities, mounts, display/socket placement and
driver execution on both advertised architectures. Image manifest support alone
does not qualify the other architecture.

Check preference-off tool exclusion and lean builds, preference-on successful
actions and missing-dependency reasons, per-profile exclusions, and off/on/off
rebuild/recreation with unchanged SSH identity, home/workspace and browser state.
Verify desktop dependencies cannot accidentally enable tools when the preference
is off. Test writable paths after fresh tmpfs creation and failed/retried startup;
confirm sudo elevation fails, model/GUI processes have no capabilities and the
system filesystem and identity mount remain read-only. Verify Chromium's actual
sandbox behavior, not just a successful process launch.

Run effective Compose validation if Compose changes. Extend existing focused
SSH/network checks for allowed public Tor access, denied private/internal/host
destinations, no provider/MCP access, and Tor loss/recovery without direct
fallback. Qualify SSH disconnect, missing display/driver, executor restart and
recreation, native idle stop, retry and state preservation. Distinguish valid
slow Tor progress from connection or response inactivity; retain native budgets
unless a demonstrated failure requires a scoped change.

Include a controlled UID-101 connection attempt in a disposable executor,
launched by the test operator without giving model code sudo. Verify Tor egress
and no direct fallback during Tor loss. Run the affected checks for lean and
desktop variants on Docker and, with the Podman plan, rootless Podman; report
engine/architecture gaps explicitly. Preserve engine-specific UID mappings and
backup access without broadening mounts or treating rootless mode as proof of
network isolation.

Update `docs/architecture.md`, `docs/configuration.md` and
`docs/updates-and-plugins.md` with placement, persistence, image/patch contracts
and diagnosis. Document the preference, rebuild/recreate procedure, switch
limitations and backup scope; add the operator-facing README entry/link when
implemented. Commit coherent passing work and independently review this
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
and failure/restart behavior, including preference switching and the rootless
Podman intersection. Coordinate engine acceptance with that plan rather than
claiming its gates passed. Missing platform or surface checks remain pending;
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
