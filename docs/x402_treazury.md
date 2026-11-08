# x402_treazury MCP integration

The main `compose.yaml` runs one x402_treazury process in
its own container, sharing `agent-net`'s network namespace with Hermes. Its twelve
HTTP MCP listeners stay on `127.0.0.1:3010–3021`; no ports are published and no
forwarding service or firewall grants are needed. Upstream's loopback restriction
is preserved without a source patch.

| Hermes MCP name | Local port |
| --- | --- |
| x402_treazury_web | 3010 |
| x402_treazury_science | 3011 |
| x402_treazury_health | 3012 |
| x402_treazury_social | 3013 |
| x402_treazury_business | 3014 |
| x402_treazury_finance | 3015 |
| x402_treazury_property | 3016 |
| x402_treazury_security | 3017 |
| x402_treazury_world | 3018 |
| x402_treazury_travel | 3019 |
| x402_treazury_toolbox | 3020 |
| x402_treazury_shopping | 3021 |

## Build and prepare

Complete the README's unified `.env` setup first. Stop an existing
deployment with `make down` before recreating namespace owners; retain its
volumes. Build and provision without starting a treasury:

```sh
make init
make build
make x402_treazury-setup
```

Set `BASE_RPC_URL` in the root `.env` for the upstream funding configuration.
Compose supplies that variable only to x402_treazury; it does not pass the entire
`.env` file to any container. Do not put wallet or funding
credentials in Hermes's environment, configuration, workspace, or skills.

The image builds unmodified upstream commit
`e1420b6364726e0c1a9d69dda72a15d8253a2b8b` using its Rust 1.99.1 toolchain and
locked dependencies. The image includes the pinned providers and their specs.
The renderer changes only the SOCKS endpoint, persistent state path, and HTTP
Host allowlists in the upstream `examples/deployments/research_desk.toml`.
Wallet groups, rotation, funding, payment caps, source selection and tool
selection retain upstream's authored policy. Review that policy before funding.

`x402_treazury-setup` is a networkless one-shot container. It generates a bearer token
once in `x402_treazury-auth`, copies that token into Hermes's private `.env`, and
adds twelve `mcp_servers.x402_treazury_*` entries to Hermes's persisted config. Repeated
setup preserves the token and compatible custom endpoint settings, including
tool filters. Conflicting URLs/authentication stop setup for operator review.
It never mounts, initializes, funds, or modifies the wallet volume.

Inspect the resolved production config offline:

```sh
docker run --rm --network none private-hermes-x402_treazury:local config show
```

`config check` can fetch remote catalogs; use `config show` for offline inspection.

## Initialize and run

Treasury initialization/restoration and funding are explicit operator actions. Use
the image's native wallet CLI so it uses the same configuration, state volume,
and Tor socket as serving:

```sh
python3 scripts/stack.py compose run --rm x402_treazury wallet --help
# For a NEW treasury, after reviewing the configuration:
python3 scripts/stack.py compose run --rm x402_treazury wallet init
```

These commands start required Tor/network dependencies. Initialization can query
chain state through Tor; it does not start the MCP server. Follow upstream's
wallet and funding instructions. For an existing treasury, restore its protected
state and key, or review `wallet init --help` for mnemonic-file restoration with
an explicit birthday. Do not create a replacement treasury unintentionally.
No funded production wallet was used to qualify this stack.

After initialization and funding:

```sh
make up
make chat
```

For a configured messaging gateway, use `make gateway`. Restart existing Hermes processes after provisioning so they
reload the token and MCP settings. The production server starts its authored
funding and catalog behavior; startup and tool use can spend money according
to that policy. There is no extra readiness probe making paid calls.

## Secrets and execution boundary

- x402_treazury runs as UID 10003 with a separate PID namespace and mount
  namespace, no capabilities, a read-only root, and a private `x402_treazury-state`
  volume. Hermes has neither that volume nor the server's private token mount.
- Tor exposes a group-restricted Unix SOCKS socket only in the x402_treazury
  container. Its control socket/cookie remains private to Tor. x402_treazury's
  native Tor policy and SOCKS authentication remain enabled. Its shared agent
  namespace also has the existing transparent Tor route and host/VM blocks.
- The SSH executor remains in its separate namespace. It cannot connect to the
  localhost MCP listeners, mount the wallet or agent config, or obtain the MCP
  bearer token from its environment. SSH TCP forwarding and tunnels are disabled.
- All twelve endpoints use one bearer token. Hermes holds authority to call
  all twelve; client tool filters do not create independent server credentials.
  Native Hermes subagents share the agent's authority. The current pinned
  Hermes `execute_code` tool RPC allowlist excludes dynamic MCP tools; changing
  that allowlist or copying secrets into the executor changes this boundary.
- Sharing a network namespace allows Hermes and x402_treazury to reach each other's
  local listeners and share permitted local network paths. It does not isolate
  their network activity from each other. Container filesystem/PID isolation
  protects wallet files from ordinary agent code; Docker/kernel compromise and
  application vulnerabilities in the authorized MCP API remain outside that
  protection.

## Stop and test

Use `make down` to stop the deployment while retaining state.
Do not use `down -v`: `x402_treazury-state` contains wallet data and `x402_treazury-auth`
contains the persistent MCP token. Back up wallet/recovery material using the
upstream wallet guidance and protect backups as secrets.
The default `wallet.key` is stored alongside encrypted wallet state; obtaining
that directory gives access to both state and its decryption key. The native
`wallet backup` command includes the encryption key.

With all normal deployments stopped, run:

```sh
make check
make x402_treazury-test
make test
```

The x402_treazury test uses a disposable project and the real Rust server, twelve
local MCP listeners, an ephemeral unfunded static key, local catalog fixtures,
and a free Tor-check API. It checks bearer enforcement, actual authenticated
MCP initialization/listing, a Rust HTTPS call through the Unix SOCKS socket,
executor secret/network isolation, code RPC denial, disabled SSH forwarding,
and Tor failure without direct fallback. It does not initialize a treasury or
make paid research calls. The main test uses the same unfunded x402_treazury fixture
and checks host/VM isolation and normal SSH, inference, and transparent Tor
behavior separately.

Upstream: [x402_treazury](https://github.com/mikeperry-tor/x402_treazury).
