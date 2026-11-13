# Capability reduction

Status: proposed; implementation, runtime qualification and independent design
acceptance are pending. This revision updates the plan only.
Planning baseline: branch `main`, commit
`0f19d8ee88a383f0e6de7eb72291761015136711`.
Scope expansion baseline: branch `main`, commit
`e2fc80057bc2aa8906a3a6623f640009d0e3a5a8`.
Topology-deferral baseline: branch `main`, commit
`9b536d0aefe53776f33eacb8366c8b639f1874ed`.
Hardening-scope amendment baseline: branch `main`, commit
`4041e1104dd12095e6cf215d32e3cdc4c65aaf77`.
Plan path: `docs/plans/capability-reduction.md`.
Follow the [planning workflow](../planning-workflow.md) before implementation.

## Intent and scope

Reduce unnecessary Linux capabilities and retained root authority while preserving
startup, execution, maintenance, ingress and shutdown. Address the concrete
exposure of long-lived processes retaining initialization authority after their
privileged work ends. Also investigate concrete privilege-escalation and escape
paths available to rogue, jailbroken or malfunctioning model code in the executor,
and to a compromised executor browser. Hermes hardening remains a priority in its
own administrative trust domain. Do not select grants merely because another deployment
calls them minimal, or claim that changing UID removes every capability.

Retain the existing GRE topology, separate Hermes/executor/Tor namespaces and
independent endpoint/router firewalls. The former topology comparison is deferred
in [alternate network topologies](deferred/alternate-network-topologies.md): GRE
works on both qualified engines, and we no longer expect compatibility or
significant security gains from replacing it. That investigation is not a
prerequisite or acceptance gate for this plan.

Prefer native privilege dropping and small explicit startup changes. Preserve Make
workflows; retain existing services and namespace ownership until G1 accepts a
specific design and its required changes. Add no runtime privilege broker,
state marker, recovery engine or generic privilege-management framework. Retain
justified root processes and grants where the owning component requires them;
this plan does not promise an entirely rootless stack.

Keep meaningful Hermes and executor hardening investigation in scope; existing
zero-capability runner children do not by themselves exhaust that work. Support
both lean and desktop executors on Docker and rootless Podman. Desktop must retain
full supported computer-use and browser-use, including Chromium's own sandbox.
Lean and desktop may have different justified hardening levels; do not broaden
lean privileges simply to match desktop or disable desktop features to obtain a
smaller grant list.

Prefer native facilities and changes to this wrapper's own code. A coherent,
revision-bound source adaptation comparable in scope to the existing
[SSH browser-use integration](../updates-and-plugins.md#derived-hermes-build-and-patch-maintenance)
is acceptable when it closes a concrete exposure and preserves supported workflows.
Assess total conceptual and lifecycle cost, not patch-file count. Defer reductions
that require deep Hermes/s6/OpenSSH rewrites, replacing supervision or SSH, or an
accumulating set of independent new patches and lifecycle mechanisms. P1 must
identify the proposed intervention, consumers, evidence and removal conditions;
this allowance does not select or authorize an uninvestigated runtime design.

Non-root Tailscale and further reduction of offline maintenance grants are deferred
below. Preserve their current behavior; neither investigation blocks this plan.
Resource/storage limits, a read-only Hermes root filesystem, image upgrades,
filesystem redesign, financial-policy changes and alternate network topologies
are outside scope. No CPU, memory, PID, disk, temporary-storage or log-size limits
are included. Live Funnel enrollment/publication, payments, funded wallet
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
| Optional `tailscale` | Yes | No drop configured. The Python wrapper starts upstream `containerboot` in userspace networking mode; non-root conversion is deferred. |
| `setup`, `setup-storage`, `mcp-config` | Yes | No drop. Short networkless jobs exit after ownership/provisioning work; they bypass native image bootstrap. |
| `teep` | No | Starts as UID/GID 10002. |
| `x402_treazury`, `x402_treazury-setup`, `x402_treazury-inspect`, `x402_treazury-admin` | No | Start as UID/GID 10003; serving and online setup also receive group 102 for the private Tor socket. |
| `hermes-config` | No | Starts the native configuration CLI directly as UID/GID 10000, independently of privileged setup. |

### Capability grants

| Service | Current container capability configuration |
| --- | --- |
| `hermes` | Selected engine defaults minus `NET_ADMIN` and `NET_RAW` |
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
  scratch paths and state access remain deferred investigation items.
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

Docker desktop's Chromium sandbox needs namespace syscalls denied by Docker's
default seccomp policy. Its desktop-only profile based on pinned modern Moby
policy adds `clone`, `setns`, `unshare`. Both lean and desktop Podman use their
native engine policy, as accepted for native desktop adoption. Neither selection
adds container capabilities; namespace support exposes user-namespace kernel paths. Child-namespace capabilities are not parent-network
namespace authority. Lean currently uses the engine default: Docker's desktop
syscall allowance does not justify broadening lean's policy. Any proposed tighter
policy needs a concrete exposure, supported delivery and native qualification. Podman already permits the required sandbox
with its native default; its policy is not identical to the Docker profile.
Browser/GUI/driver/model processes must have no effective/permitted capabilities
in the executor's original user namespace. ARM64 runtime checks found Xvnc,
xfwm4, xfdesktop, xfce4-panel and cua-driver at UID 10000 with empty effective,
permitted, inheritable and ambient sets and `NoNewPrivs=1`. Chromium reported
namespace and seccomp sandbox layers enabled. Nested user-namespace root could
neither join the parent-owned network namespace nor create raw sockets there;
UID 101 still used Tor and failed during its outage, then recovered through Tor.
The [development guide](../development.md#executor-desktop-qualification) records
platform and surface limits. Further process-tree/capability qualification belongs
to this plan; these focused SSH experiments do not satisfy the active design/final gates or authorize
topology changes.

Browser-use implementation reuses that executor and desktop profile. The Python
harness and its SSH-owned session launcher introduce no additional capabilities,
syscall allowances, published ports or peer grants. The separate browser Chromium
startup path also contained explicit sandbox-bypass arguments; those are removed
by the browser patch rather than expanding capabilities. Its runtime qualification
is recorded in [development](../development.md#browser-harness-and-results); the existing listener
omission evidence remains applicable and need not be repeated for Python packages.

## Engine parity and investigation strategy

Target an explicit startup capability list per service/executor variant and a
shared privilege-dropping implementation for Docker and rootless Podman. Variant
differences must follow real workload requirements and use existing Compose
selection, without a new policy framework. The
current Podman overlays do not override capability grants; Hermes's inherited
engine defaults are nevertheless not evidence of identical effective grants.
Replace defaults with measured explicit requirements rather than taking the
union of both engines' defaults. Exact reduced sets remain unqualified.

Investigate native lifecycle reductions with the existing GRE topology. Compare
starting directly as the service user where native startup supports it, dropping
identity and all capability sets after privileged initialization, and retaining a
justified root process with a reduced capability set where the native lifecycle
requires it. A UID change alone does not prove all capability sets are empty. Do not introduce
file capabilities, setuid helpers or a privilege broker merely to move authority
out of Compose. No topology change is required to accept useful reductions.

Keep engine-specific mount, ownership and networking behavior distinct from
capability requirements. Inventory actual UID/GID mappings, named-volume/bind and
tmpfs ownership, namespace ownership and port-binding requirements on each
qualified target. Rootless container capabilities do not confer authority in the
host's initial user namespace; keep that distinction explicit on rootless Podman
and inside Docker Desktop's Linux VM. Do not solve a mismatch with a rootful
engine, host networking, privileged containers,
engine-socket mounts or an additional host privilege helper.

The accepted seccomp baseline remains engine-specific, independently of the
shared capability target. This plan may investigate a focused tightening, but no
policy change is selected by this amendment. Engine-default filters can condition syscall permission
on the container's configured capabilities. Native Podman desktop experiments
found that omitting container `SYS_CHROOT` also blocked Chromium's child-namespace
chroot through the default filter, despite zero runner effective/permitted
capabilities. Capability reductions must therefore recheck the real Chromium
sandbox and browser workloads, not just SSH or a process capability snapshot.
Do not disable seccomp, weaken the browser sandbox or deliver a custom Podman
profile implicitly to force a common list.

If a concrete operation requires different grants, record the failing operation,
affected image/engine/kernel, capability and namespace involved, simplest shared
alternative and remaining security consequences before proposing an overlay
exception. Shared lists are a design target, not evidence of equivalent kernel
attack surface or a reason to retain unexplained grants. Prefer a small measured
exception or explicit deferral over a generic engine compatibility layer; any
policy or trust-boundary change still requires its own design acceptance.

## Preserved boundaries and intended behavior

- Keep Hermes/executor mounts, processes and network namespaces separate. Neither
  application receives `NET_ADMIN`, `NET_RAW`, host networking, privileged mode or
  Docker engine access. Preserve exact SSH, inference and selected MCP grants.
- Preserve executor denial of Hermes listeners, inference and MCP services,
  including access indirectly through existing services. Keep wallet mounts,
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

Exact existing network service grants and namespace boundaries remain unchanged. Any
proposal to change them belongs to separately scoped work and cannot be justified
as a prerequisite for privilege reduction.

## Phases, commits and gates

Commit this plan before implementation. Each phase includes affected consumers,
tests, maintained guides and concise evidence; commit coherent passing work at
phase boundaries. Commit scopes below describe outcomes, not mandatory extra
commits or permission to commit failing intermediate work.

### P1 — Establish lifecycle evidence and select privilege reductions

Capture effective base/Funnel Compose grants on both qualified engines without
retaining secrets, exact built images, packaged startup scripts and process
identity/capability snapshots in disposable resources. Trace bootstrap, steady state, subprocess creation,
profile operations, SSH authentication and shutdown. Check native guarantees
before adding wrapper enforcement. Resolve these decisions before affected edits:

- Which Hermes runtime/bootstrap operations need each capability? Hermes candidates
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
- What additional containment is practical for runner/model code and compromised
  browser processes in each executor variant? Trace the real SSH and browser
  entrypoints, reachable root listener/startup code, writable-home/workspace inputs,
  executable ownership and privileged helpers, inherited capability sets and
  namespace/syscall exposure. Check existing read-only mounts, no-new-privileges,
  native SSH privilege separation and Chromium sandbox guarantees first. Only
  pursue gaps with a concrete path or demonstrated unnecessary authority; do not
  turn this into a generic syscall allowlist or speculative hardening framework.
- Existing SSH omission experiments justify the current listener grants, not a
  conclusion that further executor hardening is impossible. Reuse those results;
  do not rerun omissions without a changed owning contract. Prefer closing exposed
  paths or tightening child authority over removing a demonstrated listener need.
  A changed SSH capability requirement needs its own native evidence.
- For each candidate, state the exposure, expected reduction, lean/desktop and
  engine impact, affected consumers and cumulative patch/lifecycle cost. Reject
  unsupported feature loss; defer candidates needing deep rewrites or independent
  new mechanisms beyond the coherent intervention budget. If no further safe
  executor reduction is found, record the specific paths investigated, blockers
  and residual authority rather than treating existing grants as a blanket waiver.

Use narrow disposable experiments only where a lifecycle uncertainty could change
the selected reduction. Name the question, affected component, supported target
and acceptance evidence before each experiment. Reuse existing evidence for
unchanged contracts; leave production state untouched. No topology prototypes or
comparison of proxy/veth alternatives are required.

P1 must recommend measured privilege reductions and justified retained grants
within the existing topology. Refine P2–P5 only where the lifecycle evidence
requires it, and reconcile shared consumers with the MCP listener and browser
plans. Missing decision-critical evidence keeps the affected reduction pending;
it does not require reopening network design.

Commit scope: focused qualification support and the evidence-backed privilege
proposal, without production privilege or topology changes. Update development
guidance for reusable checks; add no evidence subsystem.

**G1 — Independent design gate:** a fresh read-only reviewer inspects this plan,
the exact baseline/evidence snapshot and native contracts. Confirm that selected
reductions justify their complexity, authority is supported by lifecycle evidence
on both engines, engine exceptions are justified, and security claims have focused
evidence. Challenge duplicate enforcement and unnecessary startup machinery.
Review retained root justifications, state preservation and allowed/forbidden
checks. Resolve material findings before production edits; commit and re-review
material design changes that invalidate acceptance. No topology comparison or
alternate-topology acceptance is required.

### P2 — Harden Hermes and executor privilege boundaries

Replace Hermes's engine-default set with `cap_drop: [ALL]` and an experimentally
justified explicit list. Audit root s6 supervision, ownership/profile operations,
children and termination together. Implement the selected focused executor
hardening within the P1 complexity budget, preserving SSH and both variants' tool
contracts. Retain demonstrated SSH listener grants unless changed native evidence
supports a safe reduction; do not equate retaining them with excluding executor
hardening. If Hermes's explicit list or a further executor reduction cannot be
qualified within that budget, record an evidence-backed deferral and residual
exposure. Keep offline maintenance grants unchanged; verify affected consumers
without opening a separate minimization exercise.

Consumers: base/engine/executor Compose definitions, Hermes bootstrap/profile
services, executor images/startup/SSH and browser launchers, and affected
provisioning/maintenance callers. Commit scope: reductions, focused checks
and retained-grant rationale in `docs/architecture.md`, `docs/configuration.md`
and `docs/development.md` as applicable.

Acceptance: fresh/repeated setup, representative existing permissions, CLI and
gateway/profile lifecycle, SSH terminal/Python execution, repair/disconnect,
restart/recreation and clean shutdown pass. Qualify lean terminal/Python/file
operations and desktop computer-use/browser-use through production entrypoints on
both engines. For each selected hardening change show the formerly available
privilege/path is denied and intended workloads still succeed; a capability
snapshot alone is insufficient. Include Chromium namespace/seccomp diagnostics,
parent-network namespace/raw-socket denial, credential/state isolation and relevant
failure/restart behavior. Preserve native authorized tool RPC without widening
executor network grants. Record retained root processes/grants
and what fails without them. Executed code has empty effective, permitted,
inheritable and ambient sets; measure and justify any bounding-set inheritance
from native SSH rather than implying every set is cleared by the UID transition.

**G2 — Application security assessment:** include the resulting Hermes/executor
changes, supervision/SSH/browser failure paths, justified retained authority and
focused evidence in the consolidated review described under P5. An intermediate
fresh review is required before dependent work when this phase changes a security
boundary or mechanism on which that work relies; the phase label alone does not
require an additional review conversation.

### P3 — End network initialization authority before steady state

Keep the existing firewall, GRE links, routes and namespace ownership model;
change only the post-initialization privilege handoff and its required startup
grants.

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

**G3 — Network security assessment:** include startup/steady-state grants,
firewall order, namespace ownership, dependency failure/restart evidence and
unchanged ingress isolation in the consolidated review under P5. Apply the same
before-dependent-work rule as G2 when a material security change creates a dependency.

### P4 — Deferred work (not a completion gate)

Non-root Tailscale is deferred. Keep userspace networking, all capabilities
dropped, read-only root, no-new-privileges, exact-name verification, empty initial
forwarding and shutdown reset. The PrivateOnyxApp reference runs its Nginx frontend
gateway non-root but supplies no qualification of non-root `containerboot`; its
working userspace Funnel is not evidence for that reduction here. Revisit only
when this optional ingress component is separately prioritized. The first action
would be a bounded pinned-containerboot lifecycle probe covering scratch/socket
access, persistent state ownership, enrollment reuse and clean child termination.
Preserve enrollment bytes and avoid reenrollment or destructive ownership repair.
No such probe or ownership change is required for this plan.

Further offline maintenance grant reduction is deferred. Retain the existing
networkless jobs, explicit `CHOWN`, `FOWNER`, `DAC_OVERRIDE` grants, mount scopes and
separate unprivileged repair paths. Revisit if a concrete overgrant or privileged
input path is demonstrated; the next action is to reproduce that operation and
check native ownership requirements. Maintenance regression checks required by
Hermes/executor changes remain in scope. A demonstrated material defect in an
affected path must be resolved before dependent work, not hidden by this deferral.

P4 and the former G4 optional-ingress gate are inactive. Neither deferred item
requires implementation, runtime experiments or a separate review to complete
this plan.

### P5 — Combined qualification and completion

Use one shared qualification matrix for P2/P3 and the resulting combined change,
organized by engine, executor variant and affected contract. Run focused checks as
changes land, then `make check` and `make test` on both qualified engines for the
resulting implementation. Reuse those results at intermediate/final assessment
when their inputs remain unchanged; do not rerun full suites per phase or gate.
Run any remaining affected lean/desktop, computer-use/browser-use and lifecycle
checks once on the combined result, reusing still-valid phase evidence. Recheck
Chromium's real namespace/seccomp sandbox after changes to executor capabilities,
syscall policy, identity or launch behavior. Lean need not run desktop-only tests.
Validate effective base/Funnel/engine/executor models for changed definitions;
unchanged optional ingress needs no new enrollment or state-conversion exercise.

Use native production entrypoints and actual process capability sets; mock/model
parity alone does not qualify either engine. Each changed security contract needs
allowed/forbidden-path evidence and relevant failure/restart/state-preservation
checks on both engines. Missing target evidence stays pending. Record justified
variant differences and retained exposure without claiming equal hardening or
coverage of untested platforms. Serialize fixtures sharing fixed networks; use
disposable volumes and no operator secrets/state or paid calls. Do not run resource
exhaustion workloads. Repeat checks only for changed inputs, failures or unresolved
concerns.

Keep fresh independent G1 design and G5 final combined reviews. The final review
should cover G2 and G3 together with the complete evidence and maintained guides.
Use additional fresh intermediate review only for meaningful security/phase changes
requiring assessment before dependent work under the planning workflow. Commit
coherent passing work at phase boundaries; consolidation does not waive review of
material changes or allow unresolved findings to flow into dependent work.

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
and active G1/G2/G3/G5 assessments are pending; G4 is deferred. Source inspection
alone does not meet acceptance.
The privilege-reduction proposal remains pending. The former three-candidate
comparison is deferred and is no longer a requirement of G1 or completion.
This documentation-only scope reduction supplies no runtime qualification or G1
acceptance.

The plan-only scope expansion at baseline `e2fc800` received a fresh independent
read-only review with no material findings. Local-link inspection and
`git diff --check` passed. This review covers the expanded investigation and gate
requirements; that historical review does not satisfy G1, and the comparison is
now deferred.

The engine-parity amendment on `rootless-podman-support`, baseline `391151b`,
received a fresh independent read-only review with no material findings. Local
link targets and `git diff --check` passed. It adds shared-grant investigation,
capability-conditioned seccomp coverage and both-engine phase acceptance; no
runtime behavior changed or new runtime experiments were performed. This
plan-only review does not satisfy the future G1 design or implementation gates.

The topology-deferral amendment against baseline `9b536d0` received fresh
independent read-only review with no material findings. Both plan files passed
local file/heading link checks and `git diff --check`. This review accepts the
plan split only; runtime changes, new engine experiments and G1 acceptance remain
outside this amendment.

The hardening-scope amendment against baseline `4041e11` received fresh
independent read-only review with no material findings. All 15 local file/heading
links and `git diff --check` passed. This accepts the plan amendment only;
G1 design acceptance, selected reductions and both-engine runtime qualification
remain pending. No runtime changes or new engine experiments were performed.

Rollback restores prior image/Compose startup behavior and recreates affected
services while preserving volumes, keys and configuration. Preserve any executor
variant selection and restore prior source patches/security policy together with
the matching images; no Tailscale ownership change is included. Do not delete state,
regenerate identities, disable `no-new-privileges` or broaden network access to
work around a failed reduction.
