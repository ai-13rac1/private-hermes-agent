# Rootless Podman support

Status: proposed; independent design review and implementation are pending.
Planning baseline: branch `main`, commit `4a08841`.
Plan path: `docs/plans/rootless-podman.md`.
Follow the [planning workflow](../planning-workflow.md) before implementation.

## Intent and scope

Support rootless Podman as an engine next to Docker, from the first release. A
rootless engine runs no root daemon, and container root maps to an unprivileged
host user, so a compromised container or engine has less authority on the host.

In scope:

- Start, operate, back up and stop the current topology on rootless Podman with
  the same trust boundaries as on Docker.
- Keep every Docker file and command unchanged. Docker Desktop, the qualified
  Docker platform, stays the Docker regression target.
- One Podman overlay that removes or replaces only the Docker-only settings.

Out of scope:

- Topology changes. GRE stays on both engines. The
  [capability reduction plan](capability-reduction.md) owns the choice between
  GRE, a shared Hermes/Tor namespace and veth pairs.
- Rootful Podman and Podman Desktop. They are not tested.
- Paid treasury operations. The checks below use no funds.

## Current behavior

The stack supports Docker only:

- `scripts/preflight.py` requires Docker Engine 28+ and Compose 2.36+.
- `compose.yaml` and `compose.funnel.yaml` use Docker bridge options: isolated
  gateway mode on internal networks (`compose.funnel.yaml:3-5` for
  `funnel-link`), `enable_ip_masquerade: false` on `webapp-publish`, and
  `gw_priority` (`compose.yaml` teep, `compose.funnel.yaml:39`). Health checks use
  `start_interval`.
- `scripts/deployment.py` (`settings()`, `compose()`, `maintenance_compose()`)
  builds the Compose commands. `scripts/stack.py:53`, the Makefile and the smoke
  tests also call `docker compose` with explicit files.
- `tests/smoke.py` checks forbidden destinations at Docker addresses
  (`172.17.0.1`, the Docker Desktop VM `192.168.65.x`, embedded DNS `127.0.0.11`).

## Observed facts

Environment: Debian 13, kernel 6.12, Podman 5.4.2 rootless with netavark 1.14.0
and pasta, Compose 2.26.1 from Debian (`docker-compose`), `podman-docker` for the
`docker` command, and the user `podman.socket` for the Compose API. Commit
`a0650f5` on branch `podman-trial` of `ai-13rac1/private-hermes-agent` holds the
trial changes. It is evidence, not a change for merging, and its base is `main`
commit `0f19d8e`; the changes since then (x402_treazury pin and documents) do not
touch the network code. With the trial changes the full stack started: `tor`,
`agent-net`, `executor-net`, `executor` and `teep` became healthy, Hermes and
HAProxy started, and the webapp answered with a redirect to login. The trial ran
without Funnel and without an initialized treasury.

Some facts below were observed in commands run during the trial, not in saved
logs: F1's message, F6, F7's restart count, the executor Tor result and module
loading. Saved logs show F2, F4 and the started services.

| # | Docker behavior the stack depends on | Rootless Podman behavior | Trial change |
| --- | --- | --- | --- |
| F1 | `ip tunnel add` creates GRE links | Fails with `add tunnel "gre0" failed: No such device` when `ip_gre` is not loaded; `ip link add type gre` loads it | Netlink; in pull request 1, engine-neutral |
| F2 | tmpfs `uid=`/`gid=` options | `unknown mount option "uid=101"` | Router sets the owner of `/run/tor-control`; in pull request 1 |
| F3 | Isolated gateway mode, masquerade option | Netavark rejects the gateway option: `unsupported bridge network option com.docker.network.bridge.gateway_mode_ipv4` | Removed; `no_default_route: "true"` on `webapp-publish` |
| F4 | `healthcheck.start_interval` | Compose refuses it: `can't set healthcheck.start_interval as feature require Docker Engine v25 or later` | Removed |
| F5 | Preflight version floors | Podman reports its own version (5.4.2) | Floors skipped for Podman |
| F6 | Published port enters on the publication interface | `rootlessport-child` runs inside the HAProxy namespace and connects over loopback to the container's first network address, `10.203.85.3:9120`; the proxy firewall dropped it in OUTPUT | Loopback-only accept rule and a second HAProxy listen address |
| F7 | Restart backoff | A container that exits at once restarts about every 0.3 s: teep without a provider key restarted 13,597 times in an hour while `make up --wait` waited | None |
| F8 | Compose 2.36 | Compose 2.26.1 drops `gw_priority` and renders `create_host_path: false` as `bind: {}`, which fails `test_storage`. It keeps `stop_grace_period: -1s` in `config` output; whether it applies it is not known | None |

Network evidence from disposable experiments. These used networks with
`-o isolate=strict` and `--disable-dns`, which the trial Compose and the proposal
do not set (D5).

- The executor's public TCP left through Tor over the GRE link in the trial
  stack: `{"IsTor":true}`.
- On a Podman internal network, plain routing to a peer container works for
  public destinations, without GRE. From reading Moby `master` (not a test of
  the pinned Engine): the iptables IPv4 rule for internal networks drops this
  traffic (`-i <bridge> ! -d <subnet> -j DROP`); the IPv6 rule and the nftables
  backend check interfaces and do not. This is evidence for the GRE comparison
  in the capability reduction plan; this plan keeps GRE.
- Rootless bridges live in the user's network namespace. The bridge gateway is
  not a host address. A host service bound to `0.0.0.0` was not reachable at the
  host IP or the gateway from a container on an ordinary network.
- From the same container, that host service was reachable through pasta at
  `169.254.1.2` (`host.containers.internal`). The test did not check services
  bound only to `127.0.0.1`. An internal client routed through Tor could not
  reach it: Tor rejected the private address. The router's `169.254.0.0/16` deny
  covers Tor's own outbound traffic.
- A rootless container loaded `nf_nat`, `xt_REDIRECT` and `ip_gre` on demand. No
  host root step was necessary on this kernel.

## Preserved boundaries

All boundaries in [AGENTS.md](../../AGENTS.md) and
[architecture](../architecture.md) apply on both engines without change:
separate Hermes and executor namespaces, Tor-only public TCP and DNS, denial of
host, VM and private destinations, exact internal grants, ingress separate from
egress, Teep's verification behavior and its accepted direct uplink, and wallet
isolation. A Podman difference must not weaken a boundary on either engine.

## Proposed approach

1. Engine-neutral changes go into the base files. F1 and F2 are in pull
   request 1.
2. `compose.yaml`, `compose.funnel.yaml` and all Docker consumers stay as they
   are.
3. One file, `compose.podman.yaml`, removes or replaces the Docker-only keys with
   Compose's `!reset` and `!override` tags: `driver_opts: !reset {}` on the
   internal networks and `funnel-link`, `driver_opts: !override
   {no_default_route: "true"}` on `webapp-publish`, `start_interval: !reset null`,
   `gw_priority: !reset null`, and an environment value for HAProxy's startup
   (F6). A review check with Compose 2.26.1 confirmed `!reset` and `!override`
   give the intended model.
4. `scripts/deployment.py` adds the overlay to the commands it builds when the
   engine is Podman, and preflight checks the floors of that engine. Other
   callers that name files (`stack.py:53`, the Makefile, the smoke tests) get the
   same file list from `deployment.py` or a shared helper.
5. Docker gets no new file. If Podman detection fails, the Docker options stay in
   the model, netavark rejects them and startup stops with a visible error.
6. The `docker` and `docker compose` commands stay. On Podman, `podman-docker` or
   a `docker` shim and the user `podman.socket` provide them.

Support for both engines is a stated requirement, so this engine selection is
not a speculative option.

## Decisions

- **D1, engine identification.** The engine that matters is the one behind the
  socket Compose uses. With `podman-docker`, `docker` runs `podman` directly and
  `docker version --format json` has no server component list, so a check of the
  component name `Podman Engine` does not work in that form. Recommendation:
  query the API of the socket Compose uses (`DOCKER_HOST`, or Podman's default
  socket that `podman compose` sets) and select the overlay from its answer. To
  verify on Docker, Docker Desktop and Podman.
- **D2, Compose floor on Podman.** `make down` and the treasury controller pass
  `--timeout -1` (`stack.py:48`, `x402_treazury.py:186,206,242,278`), so
  `stop_grace_period` does not govern them. `gw_priority` leaves the Podman model
  in either case. Open questions: what Podman does with a stop timeout of `-1`
  through the API, and the treasury recreate path (`x402_treazury.py:256`).
  Recommendation: decide the floor after those checks; Compose 2.26.1 is enough
  if they pass, apart from the `test_storage` rendering difference (F8), which
  the test must then accept.
- **D3, `start_interval` on Podman.** Compose refuses it because of the Podman
  API version, not the Compose version. The overlay resets it.
- **D4, host loopback through pasta (Podman only).** On Docker, teep already
  reaches host services on non-loopback addresses through its gateway; its
  direct uplink is an accepted boundary. The possible new exposure on Podman is
  services bound only to host loopback, which is not tested. Options: accept it
  with a documented reason; set pasta options in the user's `containers.conf`
  (user-wide, outside the repository); or add a deny in teep's namespace, which
  needs a namespace owner or `NET_ADMIN` and conflicts with the least-machinery
  rules. Recommendation: test loopback-only reachability first, then decide. P3 checks follow the decision.
- **D5, network settings and aardvark-dns.** The endpoint firewalls deny
  `10.0.0.0/8` and connected networks (`network.py:17,105,146`), which covers
  aardvark at each gateway. Decide whether the overlay also sets `isolate: strict`
  to match the experiments, and whether DNS off can be set through Compose at
  all. Keep a P3 runtime check of aardvark on port 53.
- **D6, restart loops (F7).** Any fail-closed exit restarts about every 0.3 s
  on Podman, and `up --wait` then waits without end. Recommendation: preflight
  checks that teep has at least one provider key, a real startup requirement.
  For other exits, the guide states how an operator sees the loop
  (`podman ps`, restart count). A general backoff stays deferred.
- **D7, Funnel on Podman.** The port forwarder connects to the first network
  address. With Funnel, `funnel-link` (`10.203.87.3`) may sort before
  `webapp-backend`, and F6's rule and listen address would then miss.
  Recommendation: derive the address in HAProxy's startup from the forwarder's
  actual connection target, or fix the network order; check local access with
  Funnel on, without live enrollment.

## Phases

### P1 — Engine-neutral changes (pull request 1)

GRE through netlink and the Tor control directory owner (F1, F2). Status: draft
pull request 1, Docker check in progress.

### P2 — Podman overlay, engine selection and ingress

Implement the approach and D1–D7. Consumers: `compose.podman.yaml`,
`scripts/deployment.py`, `scripts/stack.py`, `scripts/preflight.py`, the
Makefile, `tests/compose.yaml`, `tests/test_configuration.py`,
`tests/test_storage.py`, the smoke tests that build Compose commands
(`smoke.py`, `storage_smoke.py`, `plugins_smoke.py`, `webapp_smoke.py`,
`x402_treazury_smoke.py`, `research_config_smoke.py`,
`endpoint_readiness_smoke.py`), `components/webapp/settings.py`,
`components/webapp/proxy-start.py`. Acceptance: the effective models for Docker
and Podman, each with and without Funnel, differ only in the intended keys;
unit tests pass on both engines.

### P3 — Qualification on both engines

On rootless Podman, and on Docker Desktop and Linux Docker for regression, with
disposable state and no funds. Podman targets go into the existing smoke tests,
next to the Docker addresses:

- Allowed paths: executor and Hermes public TCP and DNS through Tor; SSH, Teep
  and MCP grants; webapp through HAProxy with the right `Host`, with and without
  Funnel.
- Forbidden paths: direct egress; host services at the host IP and each gateway;
  `169.254.1.2` from Hermes and the executor, and from teep as D4 decides;
  Docker or Podman DNS; UDP other than DNS; non-loopback IPv6; Hermes to
  HAProxy's listen addresses; wrong `Host` (421).
- `make storage-test` and the locking checks on rootless volumes.
- x402_treazury without funds: `group_add: 102` access to the Tor SOCKS socket
  under user-namespace mapping, `make x402_treazury-init` and the preparation
  path up to funding.
- Restart and recreation of `tor` and the network owners; stop with
  `--timeout -1` (D2); repeated `make init` and `make up`.

### P4 — Guides

- README requirements for both engines: `podman-docker` or a shim, the user
  `podman.socket`, the Compose version from D2.
- Rootless operation: containers do not restart after a reboot without the user
  `podman-restart.service`, and they stop at logout without linger, which may
  need root to enable.
- Backups: bind data under `data/` is owned by subordinate UIDs, so host-side
  backups need `podman unshare` (`docs/configuration.md` backup scope).
- Engine differences in `docs/architecture.md`, including F6 and the
  `X-Forwarded-For` value, which is `10.203.85.3` for every client on Podman.
- Checks in `docs/development.md`.

### Gates

- **G1, design gate before P2:** a fresh independent reviewer checks this plan,
  D1–D7 and the evidence.
- **G2, final gate after P4:** a fresh independent reviewer checks the combined
  change, the P3 evidence on both engines and the guides.

## Relation to other plans

- [Computer use](computer-use-support.md): the optional desktop uses the same
  executor service, UID, mounts, namespace and existing SSH capability grants.
  Qualify both lean and desktop variants on rootless Podman, including the
  desktop-only seccomp profile and Chromium's nested user-namespace sandbox.
  Docker Desktop ARM64 desktop evidence is not Podman evidence; no sudo or
  additional capabilities are authorized as a compatibility workaround.
- [Capability reduction](capability-reduction.md): this plan keeps GRE and adds
  no capability. Its network evidence answers parts of that plan's P1. If that
  plan changes the topology, the Podman overlay and P3 checks must be redone for
  the new design. A rootless engine also removes the root daemon itself, which
  is relevant to that plan's goal.
- [Configurable MCP listeners](changing-mcp-listeners.md): MCP grants stay
  addresses in `10.203.84.0/24` on both engines.

## Rollback

Remove `compose.podman.yaml` and the engine selection in `deployment.py` and
preflight. Docker is not affected. Volumes, keys and configuration stay; no
state format changes.

## Missing evidence

- Docker runs of P1, on Docker Desktop and Linux Docker.
- D1 detection, D2 stop-timeout behavior, D4 loopback-only reachability, D5
  settings through Compose, D7 network order with Funnel.
- x402_treazury and Funnel on Podman.
- Other kernels and distributions, for example hosts with `br_netfilter` loaded
  or with restricted unprivileged user namespaces.
