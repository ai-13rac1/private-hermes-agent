# Private Hermes: SSH execution, transparent Tor, and teep

Hermes's agent and its code executor run in separate containers, filesystems,
process namespaces, and network namespaces. Both have only isolated internal
Docker networks. Their public TCP traffic is transparently redirected through
an independently running Tor gateway; their DNS goes to Tor. Teep alone has a
separate direct uplink for confidential-computing inference providers.

```text
Hermes agent ── private SSH ── executor (/workspace, no agent volume or keys)
      │                           │
      ├── internal inference      └── executor route ─┐
      │      └── teep ── direct internet              │
      ├── selected MCP IP:port grants                ▼
      └── agent route ──────────────────────── transparent Tor ── internet
```

No application receives a Docker socket, host networking, privileged mode,
`NET_ADMIN`, or `NET_RAW`. The trusted `agent-net` and `executor-net` services
configure routes and firewall rules before applications start, then remain as
stable namespace owners. Tor is in a third namespace; impersonating Tor's UID
inside an application cannot grant a direct uplink.

## Repository layout and local configuration

- `components/`: tracked Dockerfiles, container scripts, and component defaults.
- `.env`: private operator settings, selected explicitly for each service.
- `config/`: private editable bind-mount configuration; initialized from defaults.
- `data/`: reserved for future application-state bind mounts; currently unused.
- `scripts/`: host-side initialization and checks.
- `tests/fixtures/`: disposable test servers and configuration.

`make init` creates missing local configuration files and leaves existing files
unchanged. Add new settings explicitly using `.env.example` as a reference.
`make build`, `make up`, and
`make x402_treazury-setup` run it automatically. Image pins and source revisions live
in Compose and component Dockerfiles, not `.env`. Existing named volumes remain
the authoritative application state.

See [configuration and backups](docs/configuration.md) for ownership and backup requirements.

## Setup

Requires Docker Engine 28+ with Linux containers and Compose 2.36+. The isolated
bridge gateway mode is required, not an optional optimization. The fixed
`10.203.80.0/24` through `10.203.84.0/24` base address plan must not overlap existing
networks. Optional ingress uses `10.203.85.0/24` through `10.203.87.0/24`.
`scripts/preflight.py` checks engine features and selected pool conflicts.

```sh
make init
```

Edit `.env` to add at least one inference provider key and the x402_treazury
`BASE_RPC_URL`. Compose supplies provider keys only to teep and the RPC URL
only to x402_treazury. Tor control uses a private
cookie-authenticated Unix socket in the Tor container.

```sh
make build
make x402_treazury-setup
```

Before the first `make up`, follow the [x402_treazury setup guide](docs/x402_treazury.md)
to configure `BASE_RPC_URL` and explicitly initialize or restore the treasury.
Then `make up` starts routing, inference, executor, and x402_treazury MCP services. Hermes runs
interactively with the command below, or as a gateway after messaging setup.

`bootstrap` runs without networking. It generates separate SSH client and host
keys in separate named volumes, pins the executor host key, initializes the
executor's workspace/home, and copies `components/hermes/config.example.yaml` only if the
Hermes configuration does not already exist. Existing compatible configuration and keys
are preserved. Incompatible existing configuration blocks agent startup. Tor bootstrapping can take several minutes.

Before inference, edit the model to an ID returned by teep:

```sh
python3 scripts/stack.py compose exec teep curl -fsS http://127.0.0.1:8337/v1/models
python3 scripts/stack.py compose run --rm hermes config set model.default 'provider:model'
make chat
```

The default `hermes` service command runs a messaging gateway. Configure its
platform/allowlist credentials using `python3 scripts/stack.py compose run --rm hermes setup`
if desired, then start it with `make gateway`. Keep the custom
inference endpoint and SSH backend. No dashboard,
API, SSH, Tor, or inference ports are published by the base stack.
The optional authenticated webapp publishes only its selected loopback endpoint.

## Authenticated webapp and optional Funnel

See [webapp setup](docs/webapp.md) for native password authentication on host
loopback and optional public HTTPS through Tailscale Funnel. Both features are
explicitly enabled in the unified `.env`. Image builds and tests never enroll
a Tailscale node. An authenticated browser user has administrative access to
the agent container; its browser terminal is separate from the SSH code executor.

## Network and execution boundaries

- Internal networks use `gateway_mode: isolated` for IPv4 and IPv6, so their
  bridges have no host-side address. Neither application has an uplink.
- Each namespace also has a default-deny firewall. Agent grants are limited to
  executor SSH at `10.203.82.3:2222`, teep at `10.203.83.3:8337`, configured MCP
  IP/port pairs, and DNS at its Tor router. The executor gets only Tor DNS,
  public TCP through Tor, and replies to agent-initiated SSH connections.
- Other private, shared-address, loopback (outside its own local process
  namespace), link-local, multicast, reserved, and connected-network targets
  are denied. This covers ordinary Docker VM/host gateways, RPC port 111,
  metadata addresses, and DNS answers that point into prohibited space.
  Docker embedded DNS at `127.0.0.11` is blocked before DNAT.
- Private GRE links carry original-destination packets across Docker's internal
  bridges; plain next-hop routing is blocked by Docker's internal bridge rules.
  The links are internal to the Docker VM, not Internet tunnels or encryption.
  Only the trusted namespace services create them. Linux GRE support is required;
  setup fails closed if it is unavailable.
- The router independently blocks prohibited destinations before NAT and
  blocks all IP forwarding. It terminates permitted traffic at Tor's TransPort
  and DNSPort. Tor's own outbound connections cannot reach private destinations.
- This deployment intentionally blocks non-loopback IPv6 and unsupported UDP,
  including QUIC. Tor DNS supports A, AAAA, and PTR over UDP; it is not a general
  DNS server. Public TCP is routed through Tor, not destination-allowlisted.
- These controls cover the host/VM's private and connected address space. A
  service exposed on an unrelated public Internet IP is still a public target;
  add an explicit deny rule if such an address must be excluded too. A host
  administrator or compromised Docker engine remains outside this boundary.
- Hermes terminal commands, remote Python `execute_code`, and backend-aware
  file tools use SSH. Native subagents remain orchestrator instances; their
  code calls use this executor. Sessions/subagents share one executor user and
  workspace: this is agent/executor separation, not tenant or per-task isolation.
- Provider credentials and the agent data volume are not mounted into the
  executor. Hermes can intentionally synchronize skills, selected caches, and
  skill/operator-declared credential files to remote backends. Keep
  `terminal.credential_files` and skill passthrough declarations under review.
  Code's authorized Hermes tool RPC remains a capability, not a network bypass.
- SSH is key-only, with pinned host identity. Password login, TCP/agent
  forwarding, tunnels, and root login are disabled. The SSH daemon has only
  the capabilities needed for privilege separation; executed code runs as
  unprivileged UID 10000 with no capabilities.
- Tor failure blocks public egress; established application namespaces keep
  their firewall rules and have no direct fallback. Existing local teep/MCP/SSH
  paths remain usable. Initial startup waits for Tor readiness.

## x402_treazury MCP servers

The default [x402_treazury integration](docs/x402_treazury.md) builds
x402_treazury and connects its twelve authenticated MCP endpoints over shared
localhost. It keeps wallet state in a separate container volume and uses a
private Tor SOCKS Unix socket. The SSH executor has no access to these endpoints
or their bearer token. See that guide for build, wallet initialization, startup,
and verification instructions.

## Adding other selected HTTP MCP servers

The base allowlist is deliberately empty. A server should join only the
`mcp-access` internal network and receive a fixed unused address such as
`10.203.84.10`. Grant exactly its streaming HTTP port in
`config/network/mcp-allowlist.json`, for example:

```json
[{"ip": "10.203.84.10", "port": 8000}]
```

Then add its URL under Hermes's persisted `mcp_servers`:

```yaml
mcp_servers:
  selected_tools:
    url: http://10.203.84.10:8000/mcp
```

Recreate the agent namespace and Hermes together after firewall edits
(`make down`, then `make up`). Other ports on that MCP container remain blocked;
executor access is not granted. HTTP streaming and SSE require no forwarding
service or HTTP buffering proxy. The integration fixture demonstrates both.

Do not give an MCP server an uplink, host mounts, or engine access unless its
role requires that authority. Servers needing public access can be given a
separately reviewed Tor route; they do not inherit the agent's egress. Powerful
MCP tools remain explicitly granted capabilities available through Hermes.
The twelve x402_treazury MCP servers run by default; this allowlist is for additional servers.

## Images and other Hermes isolation choices

- Tor: `dockurr/tor:0.4.9.16`, pinned by digest in
  `components/network/Dockerfile`. The derived image adds our firewall/route setup
  and local authenticated bootstrap health check. Tor runs as UID 101 after
  initialization; there is no TCP control API, TCP SOCKS service, or HTTP proxy.
  A private SOCKS Unix socket is mounted only into the x402_treazury container.
- Hermes: inspected official v0.23.0 image, pinned once by digest in
  `compose.yaml` under `x-hermes-image`, reused by runtime and maintenance.
- teep: built from commit `789918ea606826650447a7f1930b917521d3d135`
  with Go 1.26. It runs as UID 10002, read-only except temporary files, without
  `--offline`, `--force`, or debug tags. Upstream's default attestation policy
  (including allowed failures) is preserved. Health is not proof of attestation.
- Executor: Alpine with Python, Node, Git, SSH, and curl; read-only root with
  separate writable home/workspace. Base tags and OS packages can change on
  rebuild; review/pin further when qualifying upgrades.

Additional Hermes controls were reviewed: `HERMES_WRITE_SAFE_ROOT` guards
selected file tools but not arbitrary shell code; Python `code_execution.mode:
strict` changes staging/interpreter selection, not OS containment. Iron-proxy
can broker additional SDK credentials and enforce HTTP destination policies;
its default host-proxy wiring is not enabled here. Cloud microVM backends and
an external VM executor offer stronger kernel separation, but introduce a
separate runtime/provider. No newly identified mode replaces this SSH design.

## Qualification and maintenance

```sh
make check
make test
```

The live test uses a separate disposable Compose project with the actual pinned
Hermes image, the real SSH executor, real Tor, teep with a dummy provider
key, and the x402_treazury server with an unfunded fixture wallet. It performs no
inference or paid research calls. Stop a normal deployment before running it:
projects use the same fixed subnets, and preflight refuses overlaps.

Tests cover actual Hermes terminal and Python execution over SSH, absence of
agent keys/environment in the executor, Tor versus direct inference egress,
forbidden host/VM/RPC/private destinations, actual Streamable HTTP MCP
initialize/list/call with SSE responses, unselected ports, and Tor failure.
Only the test project's containers, networks, and volumes are deleted.

Use `python3 scripts/stack.py compose logs -f tor executor` for startup diagnostics. `make down`
retains state. `python3 scripts/stack.py compose down -v` permanently deletes the deployment's
keys, workspaces, memories, and Tor guard state.

References: [Hermes backends](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/#terminal-backend-configuration),
[Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security/),
[Dockurr Tor](https://github.com/dockur/tor),
[Docker isolated networks](https://docs.docker.com/engine/network/port-publishing/#gateway-modes),
[teep](https://github.com/13rac1/teep).
