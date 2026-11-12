# Capability reduction and network isolation design

Status: proposed; implementation, runtime qualification and independent design
acceptance are pending. This revision updates the plan only.
Planning baseline: branch `main`, commit
`0f19d8ee88a383f0e6de7eb72291761015136711`.
Scope expansion baseline: branch `main`, commit
`e2fc80057bc2aa8906a3a6623f640009d0e3a5a8`.
Plan path: `docs/plans/capability-reduction.md`.
Follow the [planning workflow](../planning-workflow.md) before implementation.

## Intent and scope

Reduce unnecessary Linux capabilities and retained root authority while preserving
startup, execution, maintenance, ingress and shutdown. Address the concrete
exposure of long-lived processes retaining initialization authority after their
privileged work ends. Do not select grants merely because another deployment
calls them minimal, or claim that changing UID removes every capability.

Use the lifecycle evidence to compare retaining GRE, sharing Hermes's namespace
with Tor while keeping an explicitly proxied executor separate, and connecting
separate namespaces with veth pairs. Determine whether removing the GRE kernel
dependency justifies the security, compatibility and operational costs. Retaining
GRE is an acceptable outcome. No alternative has been selected or qualified.

Prefer native privilege dropping and small explicit startup changes. Preserve Make
workflows; retain existing services and namespace ownership until G1 accepts a
specific design and its required changes. Add no runtime privilege broker,
state marker, recovery engine or generic privilege-management framework. Retain
justified root processes and grants where the owning component requires them;
this plan does not promise an entirely rootless stack.

Resource/storage limits, a read-only Hermes root filesystem, image upgrades,
filesystem redesign, production replacement of supervision/SSH backends and
financial-policy changes are outside scope. P1 may assess whether an alternative
would require replacing supervision; such a dependency must be reported and
separately scoped before implementation. No CPU, memory, PID, disk,
temporary-storage or log-size limits are included. Live Funnel enrollment/publication, payments, funded wallet
operations and destructive private-state changes are not authorized by this plan.

## Current baseline

The source of truth is [base Compose](../../compose.yaml), including inherited
fields, and [the optional Funnel overlay](../../compose.funnel.yaml). These tables
record source and packaged-startup inspection, not a live process/capability
snapshot or a qualified reduction.

### Root inventory

| Service | Starts as root? | Drop point and retained root processes |
| --- | --- | --- |
| `hermes` | Yes | The official dispatcher invokes `/init`; after bootstrap, `main-wrapper.sh` uses `s6-setuidgid hermes` for the requested gateway/CLI command (UID/GID 10000). Profile supervision also drops to Hermes. Outer s6 supervision and its no-op `main-hermes` sleep remain root; enabled dashboard code drops separately. |
| `executor` | Yes | OpenSSH drops authenticated sessions/commands to runner UID/GID 10000. The listener retains root for privilege separation and session creation. |
| `agent-net`, `executor-net` | Yes | No drop. After firewall, GRE and route installation, Python waits for signals as root with `NET_ADMIN`. |
| `tor` | Yes | After network setup, state ownership repair and SOCKS-directory preparation, `su-exec 101:102` executes Tor. Full post-drop capability sets remain to be measured. |
| `webapp-proxy` | Yes | After firewall installation, `setpriv` switches to UID/GID 10005, clears supplementary groups and removes bounding, inheritable and ambient capabilities before HAProxy. Its maintained contract also requires empty effective/permitted sets. |
| Optional `tailscale` | Yes | No drop configured. The Python wrapper starts upstream `containerboot` in userspace networking mode; qualification must inspect the complete child tree. |
| `setup`, `setup-storage`, `mcp-config` | Yes | No drop. Short networkless jobs exit after ownership/provisioning work; they bypass native image bootstrap. |
| `teep` | No | Starts as UID/GID 10002. |
| `x402_treazury`, `x402_treazury-setup`, `x402_treazury-inspect`, `x402_treazury-admin` | No | Start as UID/GID 10003; serving and online setup also receive group 102 for the private Tor socket. |
| `hermes-config` | No | Starts the native configuration CLI directly as UID/GID 10000, independently of privileged setup. |

### Capability grants

| Service | Current container capability configuration |
| --- | --- |
| `hermes` | Docker defaults minus `NET_ADMIN` and `NET_RAW` |
| `setup`, `setup-storage`, `mcp-config` | All dropped; `CHOWN`, `FOWNER`, `DAC_OVERRIDE` added |
| `executor` | All dropped; `SETUID`, `SETGID`, `SYS_CHROOT` added |
| `agent-net`, `executor-net` | All dropped; `NET_ADMIN` added |
| `tor` | All dropped; `NET_ADMIN`, `SETUID`, `SETGID`, `CHOWN`, `FOWNER`, `DAC_OVERRIDE` added |
| `webapp-proxy` | All dropped; `NET_ADMIN`, `SETUID`, `SETGID`, `SETPCAP` added for startup, then irreversibly removed from serving processes |
| Optional `tailscale`, `teep`, all `x402_treazury` services/jobs, `hermes-config` | All dropped |

The earlier setup description is superseded: setup neither receives `SETUID`/
`SETGID` nor runs native configuration after a UID transition. Preserve the
[operation-scoped maintenance contracts](../configuration.md), including separate
unprivileged configuration and profile-only disconnect paths.

### Packaged contracts and evidence limits

- Historical Hermes inspection (before the v0.23.1 update): official v0.23.0, source
  `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`, base digest
  `adb7890916de63245523492be8f68f9d2095fecbec4e2a6dab7960381f0fc002`.
  See the [current image contract](../updates-and-plugins.md#derived-hermes-build-and-patch-maintenance)
  and recheck these capability assumptions against the selected revision.
  Packaged dispatcher, stage2 hook, main wrapper and profile supervision scripts
  were inspected. Root bootstrap and service drops are distinct; Compose
  `user: 10000` is not an established equivalent lifecycle.
- Network/Tor: `dockurr/tor:0.4.9.16`, digest
  `5b5c9e5036fff91bdf021ef225fdb0fc9ba4222425b9cbc1858a15681d220590`.
  Our `components/network/network.py` owns setup and the Tor handoff.
- HAProxy: `haproxy:3.4-alpine`, digest
  `5312d37032c079c4937d45ef63758852434351f3b425a3703521fd999837abcf`.
  `components/webapp/proxy-start.py` already demonstrates irreversible privilege
  removal; preserve its [ingress contract](../webapp.md).
- Optional Tailscale: digest
  `ed6480b33c6eb67c9cbd203ed42b9fb57e361986725b6856def71b7a3d9e276c`
  (recorded as 1.104.4). Userspace networking uses no capabilities, but
  `data/tailscale` is root-owned mode 0700. Non-root `containerboot` behavior,
  scratch paths and state access remain investigation items.
- Executor: Alpine 3.24 with OpenSSH. Teep source:
  `789918ea606826650447a7f1930b917521d3d135`; treasury source:
  `4346421a1a4d0d53fc31e246ff6fde27f634a9f6`. Record actual built image IDs and
  package versions for qualification; mutable tags are not exact build identities.

Earlier networkless help-command evidence does not establish minimum grants or
qualify supervision/shutdown. The general smoke override bypasses native Hermes
startup; use production entrypoints for lifecycle claims. No new runtime
qualification has been performed for this proposal.

### Executor evidence from computer-use implementation

The user requested that this work minimize capabilities as it qualifies the
optional desktop. On 2026-11-11, networkless Docker Desktop ARM64 experiments
against the pinned desktop-derived executor tested each existing SSH grant
independently. With root listener, fixture keys, `UsePAM=no`, read-only root,
writable `/run` and `/tmp`, `no-new-privileges` and all other capabilities dropped:

| Omitted grant | Reproduced native failure |
| --- | --- |
| `SYS_CHROOT` | `chroot("/run/sshd"): Operation not permitted [preauth]` |
| `SETUID` | `setresuid 997: Operation not permitted [preauth]` |
| `SETGID` | `setgroups: Operation not permitted [preauth]` |
| None of those three | Key-only SSH login returned runner UID 10000 |

Desktop base index:
`c7d8607d076f26a64e0bd6828f74e1764af43fe3281368188459bb693bfa7567`;
Debian OpenSSH `1:10.0p1-7+deb13u4`. These results establish the existing
root-listener contract for that tested image, not Alpine/AMD64/Podman coverage or
a proof that a different account/key model could not work. Preserve the current
listener grants unless a concrete alternative is separately designed and
qualified; do not repeat capability omission experiments without a changed
owning contract. Permanent rationale is in
[architecture](../architecture.md#executor-capability-requirements) and
[development](../development.md#executor-desktop-qualification).

The desktop's Chromium sandbox needs namespace syscalls denied by Docker's
default seccomp policy. A desktop-only profile based on pinned modern Moby policy
adds `clone`, `setns`, `unshare`; this adds no container capabilities but exposes
user-namespace kernel paths. Child-namespace capabilities are not parent-network
namespace authority. Keep lean on the engine default: this syscall allowance is
not itself a capability reduction that justifies changing the lean default.
Browser/GUI/driver/model processes must have no effective/permitted capabilities
in the executor's original user namespace. ARM64 runtime checks found Xvnc,
xfwm4, xfdesktop, xfce4-panel and cua-driver at UID 10000 with empty effective,
permitted, inheritable and ambient sets and `NoNewPrivs=1`. Chromium reported
namespace and seccomp sandbox layers enabled. Nested user-namespace root could
neither join the parent-owned network namespace nor create raw sockets there;
UID 101 still used Tor and failed during its outage, then recovered through Tor.
The [development guide](../development.md#executor-desktop-qualification) records
platform and surface limits. Further process-tree/capability qualification belongs
to this plan; these focused SSH experiments do not satisfy G1–G5 or authorize
topology changes.

Browser-use implementation reuses that executor and desktop profile. The Python
harness and its SSH-owned session launcher introduce no additional capabilities,
syscall allowances, published ports or peer grants. The separate browser Chromium
startup path also contained explicit sandbox-bypass arguments; those are removed
by the browser patch rather than expanding capabilities. Its runtime qualification
is recorded in [development](../development.md#browser-harness-and-results); the existing listener
omission evidence remains applicable and need not be repeated for Python packages.

## Preserved boundaries and intended behavior

- Keep Hermes/executor mounts, processes and network namespaces separate. Neither
  application receives `NET_ADMIN`, `NET_RAW`, host networking, privileged mode or
  Docker engine access. Preserve exact SSH, inference and selected MCP grants.
- Preserve executor denial of Hermes listeners, inference and MCP services,
  including access indirectly through any proposed proxy. Keep wallet mounts,
  tokens and Tor's private filesystem-backed SOCKS/control sockets scoped to
  their existing owners.
- Preserve Tor-only public TCP/DNS paths, prohibited host/VM/private destinations,
  unsupported UDP/non-loopback IPv6 denial and no direct fallback. Namespace owners
  must stay alive after dropping privilege; do not replace them with exiting jobs.
- Preserve official Hermes bootstrap, profile reconciliation, unprivileged gateway/
  CLI services, supervision and termination. Minimize capabilities available to
  retained root supervision without replacing the native lifecycle.
- Preserve SSH identities, key-only login and unprivileged execution. Retain the
  root listener if required by native OpenSSH privilege separation/session creation.
- Keep trusted offline setup separate from execution. Inspection, backup, repair,
  disconnect and shutdown must not acquire unrelated startup prerequisites.
- Preserve Teep uplink/attestation behavior, wallet isolation, group-102 private
  SOCKS access, authenticated ingress and exact-host/origin checks. Tailscale stays
  userspace-only with no TUN or network capabilities. Preserve browser-content
  controls and the authenticated operator's administrative authority.
- Preserve current-format credentials, Tor guards, enrollment identity, wallets,
  configuration and retry-safe initialization. Any ownership adjustment must
  preserve existing state and have a concrete reverse operation for rollback.
- Measure real/effective/saved UID/GID, supplementary groups and effective,
  permitted, inheritable, ambient and bounding sets across process trees. A UID
  drop or `no-new-privileges` alone is not proof of empty sets. Distinguish service
  descendants from operator-controlled Docker exec.

The current separate Tor namespace and independent endpoint/router firewalls are
the comparison baseline. The shared Hermes/Tor candidate deliberately changes
that boundary. Identify every weakened property and compensating mechanism;
independent review alone does not authorize accepting a weaker trust boundary.
Obtain explicit operator acceptance of any such change and reconcile governing
instructions and maintained architecture before implementation. Preserve host/VM
denial, Tor-only public egress and executor separation in every candidate. Exact
existing service grants remain the default; any proposed host grant must name its
destination and port and requires separate authorization.

## Phases, commits and gates

Commit this plan before implementation. Each phase includes affected consumers,
tests, maintained guides and concise evidence; commit coherent passing work at
phase boundaries. Commit scopes below describe outcomes, not mandatory extra
commits or permission to commit failing intermediate work.

### P1 — Establish lifecycle evidence and compare isolation designs

Capture effective base/Funnel Compose grants without retaining secrets, exact
built images, packaged startup scripts and process identity/capability snapshots
in disposable resources. Trace bootstrap, steady state, subprocess creation,
profile operations, SSH authentication and shutdown. Check native guarantees
before adding wrapper enforcement. Resolve these decisions before affected edits:

- Which Hermes/maintenance operations need each capability? Hermes candidates
  include `CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`; investigate `FOWNER`, `KILL`
  and other grants only against concrete uses and reproducing checks.
- Distinguish ordinary UID-10000 application code from retained root supervision.
  Trace whether any Hermes process can assume Tor's UID, including service
  restart and profile creation paths, and whether authority can be irreversibly
  removed while preserving the native lifecycle. Identify actual failure paths
  rather than treating a container grant as proof that all children retain it.
- Can network owners irreversibly drop UID/groups/all capabilities after setup
  while retaining readiness, namespace ownership and restart behavior? Prefer an
  existing tool such as the proxy's `setpriv`; justify any startup `SETUID`,
  `SETGID` or `SETPCAP` additions against the reduced steady-state authority.
- What does Tor retain after `su-exec`? Can irreversible removal preserve state,
  health/control paths and private socket ownership/access?
- Does pinned Tailscale `containerboot` support a fully non-root userspace lifecycle?
  Trace scratch paths, CLI socket permissions, state contents/ownership, child
  cleanup and enrollment reuse. Select a fixed image user only after this check.
  If unavailable, record the concrete blocker and deferral; do not add privileges
  or replace upstream orchestration to force it.

#### Required comparative assessment

Record the assessment in this plan, with concise evidence and unresolved
questions. Compare these three concrete candidates against the current behavior:

| Candidate | Required design detail and evidence |
| --- | --- |
| Retain GRE and separate Hermes, executor and Tor namespaces | Establish which startup and steady-state privileges can be reduced without changing topology. Record the kernel dependency, current fail-closed behavior and maintenance cost. |
| Share Hermes and Tor networking; retain a separate executor with an explicit HTTP proxy | Specify the proxy owner, exact executor grant, HTTP/CONNECT transport through Tor and remote DNS handling. Trace Tor-UID exemption risks, shared loopback/listeners and internal grants. Specify enforcement and checks demonstrating the proxy cannot reach prohibited host/VM/private or agent-only destinations on the executor's behalf. |
| Retain separate namespaces and connect them with veth pairs | Specify who creates and places each endpoint, how it obtains namespace access, actual capability requirements and Docker Desktop VM implications. Trace link recreation, namespace destruction, firewall ordering and startup failure cleanup without a generic recovery service. |

For each candidate, identify affected Compose services, images, helpers,
configuration, maintenance consumers, tests and permanent guides. Explain setup
and steady-state authority, added/removed dependencies and components, and native
component guarantees. Assess gains and risks relative to retaining GRE, including
independent enforcement, Tor outage behavior, local service availability,
restart/recreation, shutdown and state preservation. Include shared port binding
and abstract Unix socket exposure where namespaces are shared.

Assess representative executor workloads through the real SSH entry point:
terminal/Python execution, curl, Git over HTTPS, package downloads and clients
using direct sockets or ignoring proxy variables. Distinguish supported behavior
from proposed compatibility losses. Environment variables are client configuration;
the network firewall must deny direct bypass. Check destination policy for literal
addresses, DNS answers and redirects, plus Docker embedded DNS, TCP/UDP rpcbind,
non-loopback IPv6 and unsupported UDP. Include permitted-path controls so an
unavailable target cannot masquerade as successful isolation.

Use narrow disposable experiments only where an uncertainty could change the
decision. Name the question, candidate, supported target and acceptance evidence
before running each experiment. Leave production topology and private state
untouched; no full implementation or exhaustive prototype of every candidate is
required. The workload and security checks above define the comparison and future
implementation acceptance; run them in P1 only as needed to resolve a material
design uncertainty. Full runtime qualification belongs to the selected approach's
implementation phases. Reference repositories supply techniques to assess against exact pins:
`torproxy` at `2a538fd2ad8a09caa7282dffc7d528d6e59d1db1` and `rootless-hermes`
at `4bda68620b261ab68f3ce06c7cdbdc015308917a`. The latter runs container UID 0
under a rootless engine and replaces startup; it does not qualify a capability-free
Hermes lifecycle or this stack's network policy.

P1 must recommend an approach with reasons and retain the other candidates as
analysis in this plan. Provide implementation phases and acceptance criteria for
the preferred approach only, including capability reductions, coherent commits,
review gates, rollback and permanent documentation. Revise P2–P5 to fit that
proposal before G1 acceptance; their current text is the GRE baseline, not a
decision to retain it. Reconcile affected plans, particularly MCP listener and
browser-content work. If material evidence is missing, record a concrete bounded
experiment and keep the affected decision pending rather than selecting by
assumption. Avoid separate implementation plans for discarded alternatives.

Commit scope: focused qualification support, comparative assessment and the
evidence-backed implementation proposal, without production privilege or topology
changes. Update development guidance for reusable checks; add no evidence subsystem.

**G1 — Independent design gate:** a fresh read-only reviewer inspects this plan,
the exact baseline/evidence snapshot and native contracts. Review all three
candidates, the recommendation and the revised phases for the preferred approach.
Confirm that gains justify complexity and any compatibility cost, authority is
supported by lifecycle evidence, and security claims have sufficient focused
evidence. Challenge added services, namespace access and duplicate enforcement.
Record boundary changes requiring operator acceptance, retained root
justifications, state preservation and allowed/forbidden checks. Retaining GRE
may pass; unresolved decision-critical evidence keeps the affected gate pending.
Resolve material findings and required boundary acceptance before production
edits; commit and re-review material design changes that invalidate acceptance.

### P2 — Reduce application and maintenance capability grants

Replace Hermes's Docker-default set with `cap_drop: [ALL]` and an experimentally
justified explicit list. Audit root s6 supervision, ownership/profile operations,
children and termination together. Review executor and offline maintenance sets
separately; remove grants only when native lifecycle evidence supports doing so.
Preserve unprivileged jobs and their mount scope; do not merge repair into setup.

Consumers: `compose.yaml`, Hermes bootstrap/profile services, executor SSH,
provisioning and maintenance callers. Commit scope: reductions, focused checks
and retained-grant rationale in `docs/architecture.md`, `docs/configuration.md`
and `docs/development.md` as applicable.

Acceptance: fresh/repeated setup, representative existing permissions, CLI and
gateway/profile lifecycle, SSH terminal/Python execution, repair/disconnect,
restart/recreation and clean shutdown pass. Record retained root processes/grants
and what fails without them. Executed code has empty effective, permitted,
inheritable and ambient sets; measure and justify any bounding-set inheritance
from native SSH rather than implying every set is cleared by the UID transition.

**G2 — Application/maintenance gate:** fresh independent review of the phase
snapshot, supervision/SSH failure paths and focused evidence before dependent
work. Retaining a justified capability is acceptable.

### P3 — End network initialization authority before steady state

This phase describes the existing GRE topology. P1 must adapt its consumers,
handoffs and checks if another design is recommended; G1 reviews that revision
before implementation.

After installing firewall/GRE/routes, have `agent-net` and `executor-net` switch
to an unprivileged identity, clear groups and irreversibly remove all capability
sets while continuing to own namespaces and wait for signals. Initialization stays
fail-closed. Verify Tor's post-drop sets and remove initialization authority where
necessary using the simplest qualified handoff. Preserve the existing HAProxy drop.

Consumers: network image/startup, Compose startup grants/tmpfs permissions, Tor
health/control/SOCKS paths, dependency readiness and ingress. Commit scope:
qualified handoffs, needed tools/grants, focused checks and architecture/development
guidance. Justify temporary privilege additions; add no shared management framework.

Acceptance: steady-state network owners and Tor are non-root with every capability
set empty; readiness and clean stop work. Show allowed SSH/Teep/MCP/Tor/ingress
paths and forbidden host/VM/private, embedded-DNS, unsupported UDP/IPv6 and direct
egress paths before and after relevant Tor/network restart/recreation. Tor loss
blocks public egress while established local grants remain usable. Exercise native
namespace-sharing recovery; document required application recreation rather than
adding a recovery engine.

**G3 — Network authority gate:** fresh independent review of startup/steady-state
grants, firewall order, namespace ownership, dependency failure/restart evidence
and unchanged ingress isolation.

### P4 — Qualify optional non-root Tailscale

If G1 establishes native support, start the wrapper/child tree as a fixed
unprivileged image user with all capabilities dropped. Change trusted storage
preparation only for the Tailscale leaf and existing contents actually requiring
ownership adjustment. Preserve enrollment bytes and retry behavior; diagnose
missing material instead of reenrolling or deleting state.

Consumers: `compose.funnel.yaml`, Tailscale image/wrapper, provisioning storage,
Funnel lifecycle fixtures and webapp/configuration guidance. Commit scope: the
coherent non-root lifecycle, state-preservation checks and docs, or an evidence-backed
deferral with a concrete next action if native support is unavailable.

Acceptance: disposable fixtures cover first-use state creation, existing state
permissions, repeated setup, restart/recreation and clean child termination.
Exact-name checks, empty forwarding on startup and reset on shutdown remain intact.
Demonstrate non-root operation with empty capability sets and unchanged proxy/network
grants. Controlled fixtures do not establish live enrollment/public HTTPS; record
unavailable native/live coverage explicitly.

**G4 — Optional ingress gate:** fresh independent review of native boot support,
identity/ownership preservation and shutdown/failure behavior. If this is the final
implementation phase, G4 and G5 may share one fresh review covering both scopes.

### P5 — Combined qualification and completion

Run `make check` and `make test` for the resulting implementation, plus focused
production-entrypoint, process-set and lifecycle checks above. Validate effective
base/Funnel Compose models for changed definitions. Every security phase needs
allowed/forbidden-path evidence and relevant failure/restart checks before its
gate, not just static inspection. Serialize fixtures sharing fixed networks; use
disposable volumes and no operator secrets/state or paid calls. Do not run resource
exhaustion workloads. Reuse still-valid evidence; repeat checks only for changed
inputs, failures or unresolved concerns.

**G5 — Final combined gate:** a fresh independent reviewer assesses the complete
result, relevant unchanged security contracts, corrections, maintained guides and
limitations. Supply the exact SHA/snapshot (including new files), baseline,
evidence and earlier findings. Require tracing consumers/failure paths and
challenging unnecessary machinery. Resolve material findings before completion;
unavailable review/checks remain pending rather than passed.

All independent reviews use newly spawned read-only subagents with fresh
conversations (`fork_turns="none"`); reviewers author no changes. One review may
cover a phase and gate when explicitly briefed for both. Record concise results,
reviewed revisions, finding dispositions and missing coverage here while active.
After final acceptance, preserve lasting contracts/evidence/limits in maintained
guides, resolve inbound links and remove the completed plan in the completion or
focused cleanup commit. Do not archive it or remove it while gates remain pending.

## Related plans, acceptance and rollback

[Read-only configuration](readonly-configuration.md) stays separate: preserve
administrative writers/profile operations without adding configuration integrity
work here. [Configurable MCP listeners](changing-mcp-listeners.md) shares readiness
and maintenance consumers: qualify the implemented inventory and reconcile that
plan if either implementation changes shared interfaces. [Browser content work](webapp-interactive-content.md)
retains ingress and authenticated-operator authority; preserve its fixtures without
implementing deferred browser features. These proposals are not implemented
contracts or authority to expand this work.

Accept a reduction only when intended privilege is absent, supported operations
pass and relevant restart/shutdown logs show no permission failures. Document
justified retained root/grants and explicit deferrals; a deferred item needs a
concrete next action and must not be described as implemented. Runtime inventory
and G1–G5 are pending; source inspection alone does not meet acceptance.
The three-candidate comparison and preferred implementation proposal are also
pending. This scope expansion supplies no new runtime qualification or G1 acceptance.

The plan-only scope expansion at baseline `e2fc800` received a fresh independent
read-only review with no material findings. Local-link inspection and
`git diff --check` passed. This review covers the expanded investigation and gate
requirements; the future comparative assessment and G1 design remain pending.

Rollback restores prior image/Compose startup behavior and recreates affected
services while preserving volumes, keys and configuration. For Tailscale ownership
changes, document the exact prior leaf/content ownership and a trusted offline
reverse operation before rollout; preserve enrollment bytes. Do not delete state,
regenerate identities, disable `no-new-privileges` or broaden network access to
work around a failed reduction.
