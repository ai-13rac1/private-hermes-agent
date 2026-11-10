# Capability reduction

The maintained [maintenance job contracts](../configuration.md) and
[development workflow](../development.md) supersede earlier shared setup/
configuration-repair and wallet-inspection prerequisites; historical qualification
below describes its recorded revision.

Status: proposed for the main Hermes runtime. Consolidated offline setup already
uses an explicit capability set; its current baseline is recorded below.

## Objective

Reduce Linux capabilities granted to the deployment where evidence shows they
are unnecessary. Preserve normal startup, execution, maintenance, and shutdown.
Do not select a capability set merely because another deployment calls it
minimal.

Resource and storage limits are outside this plan. Do not add CPU, memory, PID,
disk, temporary-storage, or log-size limits as part of this work.

## Current baseline

The source of truth is `compose.yaml`, including its inherited service fields.

| Service | Current capability configuration | Role |
| --- | --- | --- |
| `hermes` | Docker defaults minus `NET_ADMIN` and `NET_RAW` | Official root initialization, then unprivileged agent services |
| `setup` | All dropped; `CHOWN`, `FOWNER`, `DAC_OVERRIDE`, `SETUID`, `SETGID` added | Networkless ownership, SSH/auth/MCP provisioning; native config command drops to UID/GID 10000 |
| `executor` | All dropped; `SETUID`, `SETGID`, `SYS_CHROOT` added | SSH daemon privilege separation; commands run as UID 10000 |
| `agent-net`, `executor-net` | All dropped; `NET_ADMIN` added | Firewall, GRE, and route setup; stable namespace ownership |
| `tor` | All dropped; `NET_ADMIN`, `SETUID`, `SETGID`, `CHOWN`, `FOWNER`, `DAC_OVERRIDE` added | Network and volume setup, followed by unprivileged Tor |
| `teep` | All dropped | Unprivileged inference proxy |

The agent retains the official `/init` entrypoint and s6 supervision. Its
default UID/GID is 10000. A previous networkless help-command check established
that the current configuration starts, but did not establish a reduced minimum
or exercise every long-running service and shutdown path.

## Invariants

- Keep the agent and executor in separate containers and network namespaces.
- Give neither application `NET_ADMIN`, `NET_RAW`, host networking, privileged
  mode, or Docker engine access.
- Preserve pinned SSH identity, key-only login, remote code execution, and the
  existing host/VM and MCP firewall boundaries.
- Keep the trusted network initialization services separate from applications.
- Retain the official Hermes initialization and privilege-dropping contract.
- Preserve data, key identities, Tor guard state, and existing volume ownership
  across restarts and upgrades.
- Distinguish capabilities granted to a container from the effective,
  permitted, inheritable, ambient, and bounding sets of its actual processes.
  Initialization capabilities do not disappear simply because boot finishes.

## Implementation sequence

1. Record the resolved Compose configuration, pinned image identities, and
   process capability sets in a disposable deployment. Inspect the scripts in
   the actual pinned Hermes image; the reference checkout may differ.
2. Audit s6 initialization, UID/GID changes, ownership and permission changes,
   profile reconciliation, child supervision, and termination. Establish which
   operations need capabilities and which already work through ownership.
3. Replace the main Hermes service's broad default set with `cap_drop: [ALL]`
   and an explicit, experimentally justified `cap_add` list. Treat `CHOWN`,
   `SETUID`, `SETGID`, and `DAC_OVERRIDE` as candidates, not an established
   answer. Investigate `FOWNER`, `KILL`, and other operations where required;
   add nothing without an identified use and a reproducing check.
4. Review the explicit `setup` set separately. Ownership/provisioning uses
   `CHOWN`, `FOWNER`, and `DAC_OVERRIDE`; the native configuration command uses
   `SETUID`/`SETGID` to execute as UID/GID 10000 with supplementary groups cleared.
   Preserve fresh and repeated setup, configuration repair, and MCP updates.
5. Review the already explicit executor, network, and Tor sets independently.
   Remove a capability only when the relevant lifecycle checks support doing
   so. Verify that executed code and Tor retain no effective capabilities.
6. Update Compose, owning documentation, and meaningful regression checks in
   focused changes. Record why each retained capability is needed and what
   would fail without it. Do not bundle an image upgrade or filesystem redesign.

## Qualification

Use disposable volumes and the pinned production entrypoint. The smoke-test
override starts Hermes directly as UID 10000, bypassing s6, so it cannot by
itself qualify changes to the main container's initialization capabilities.

Cover:

- Fresh provisioning and repeated bootstrap with existing keys and data.
- Initialization with representative existing ownership and permissions.
- CLI startup and the supported long-running gateway/profile lifecycle,
  including clean termination without permission errors or abandoned children.
- Container restart and recreation while retaining data and SSH identities.
- Actual Hermes terminal and Python execution over SSH, including the
  executor's unprivileged UID and capability sets.
- The existing Tor, host/VM, embedded-DNS, and selected MCP integration checks.
- Representative enabled features that use subprocesses or native tools.
  A help command succeeding is insufficient evidence of compatibility.

Run `make check` and `make test` for implementation changes, plus the focused
production-entrypoint and lifecycle checks above. Do not deliberately run a
fork bomb or resource-exhaustion workload to qualify capability reduction.

## Acceptance and rollback

Accept a reduction when the intended capabilities are absent, all supported
operations pass, and shutdown and restart logs contain no relevant permission
failures. If a capability is still needed, document the reason and retain it;
functionality preservation takes precedence over a smaller-looking list.

Rollback by restoring the previous capability configuration and recreating
affected services. Do not delete volumes, regenerate keys, disable
`no-new-privileges`, or broaden network access to work around a failed reduction.
