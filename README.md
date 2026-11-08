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

## Setup

Requires Docker Engine 28+ with Linux containers and Compose 2.36+. The isolated
bridge gateway mode is required, not an optional optimization. The fixed
`10.203.80.0/24` through `10.203.84.0/24` address plan must not overlap existing
networks. `scripts/preflight.py` checks engine features and pool conflicts.

```sh
cp -n .env.example .env
cp -n teep.env.example teep.env
chmod 600 .env teep.env
```

Add at least one provider key to `teep.env`. These keys are supplied only to
teep. The old `TORPROXY_API_TOKEN` setting is no longer needed: Tor control is a
private cookie-authenticated Unix socket in the Tor container.

```sh
make build
make up
```

`make up` starts the routing, inference, and executor services. Hermes runs
interactively with the command below, or as a gateway after messaging setup.

`bootstrap` runs without networking. It generates separate SSH client and host
keys in separate named volumes, pins the executor host key, initializes the
executor's workspace/home, and copies `config/hermes.example.yaml` only if the
Hermes configuration does not already exist. Existing compatible configuration and keys
are preserved. Incompatible existing configuration blocks agent startup. Tor bootstrapping can take several minutes.

Before inference, edit the model to an ID returned by teep:

```sh
docker compose exec teep curl -fsS http://127.0.0.1:8337/v1/models
docker compose run --rm hermes config set model.default 'provider:model'
docker compose run --rm hermes chat
```

The default `hermes` service command runs a messaging gateway. Configure its
platform/allowlist credentials using `docker compose run --rm hermes setup`
if desired, then start it with `docker compose up -d hermes`. Keep the custom
inference endpoint and SSH backend. No dashboard,
API, SSH, Tor, or inference ports are published to the host.

### Migrating the earlier prototype

Stop the old deployment first with `docker compose down`, without `-v`, using
its original Compose file if containers have already been started. The obsolete
socat containers can be removed with `docker compose down --remove-orphans`.
The `hermes-data` and `tor-state` volumes are retained by this deployment.
Before starting the agent, update any existing config to use:

```yaml
model:
  provider: custom
  base_url: http://10.203.83.3:8337/v1
  api_key: unused
terminal:
  backend: ssh
  cwd: /workspace
  env_passthrough: []
```

Use the networkless operator helper to edit an existing volume without starting
an agent or requiring successful bootstrap:

```sh
docker compose run --rm configure set terminal.backend ssh
docker compose run --rm configure set terminal.cwd /workspace
docker compose run --rm configure set model.provider custom
docker compose run --rm configure set model.base_url http://10.203.83.3:8337/v1
```

`make up` validates an existing config rather than silently converting it. If
you change network-namespace owners or the address plan, use `make down` then
`make up` to recreate their consumers together. Restarting or replacing Tor
alone does not replace either application's network namespace.

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

## Adding selected HTTP MCP servers later

The base allowlist is deliberately empty. A server should join only the
`mcp-access` internal network and receive a fixed unused address such as
`10.203.84.10`. Grant exactly its streaming HTTP port in
`config/mcp-allowlist.json`, for example:

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
No actual MCP server is configured until you select one.

## Images and other Hermes isolation choices

- Tor: `dockurr/tor:0.4.9.16`, pinned by digest in
  `docker/network.Dockerfile`. The derived image adds our firewall/route setup
  and local authenticated bootstrap health check. Tor runs as UID 101 after
  initialization; there is no TCP control API, SOCKS service, or HTTP proxy.
- Hermes: inspected official v0.23.0 image, pinned by digest. Override
  `HERMES_IMAGE` in `.env` when reviewing an upgrade.
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
Hermes image, the real SSH executor, real Tor, and teep with a dummy provider
key. It performs no inference. Stop a normal deployment before running it:
projects use the same fixed subnets, and preflight refuses overlaps.

Tests cover actual Hermes terminal and Python execution over SSH, absence of
agent keys/environment in the executor, Tor versus direct inference egress,
forbidden host/VM/RPC/private destinations, actual Streamable HTTP MCP
initialize/list/call with SSE responses, unselected ports, and Tor failure.
Only the test project's containers, networks, and volumes are deleted.

Use `docker compose logs -f tor executor` for startup diagnostics. `make down`
retains state. `docker compose down -v` permanently deletes the deployment's
keys, workspaces, memories, and Tor guard state.

References: [Hermes backends](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/#terminal-backend-configuration),
[Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security/),
[Dockurr Tor](https://github.com/dockur/tor),
[Docker isolated networks](https://docs.docker.com/engine/network/port-publishing/#gateway-modes),
[teep](https://github.com/13rac1/teep).
