# x402_treazury MCP integration

The main `compose.yaml` includes one x402_treazury serving process in
its own container, sharing `agent-net`'s network namespace with Hermes. Its twelve
HTTP MCP listeners stay on `127.0.0.1:3010–3021`; no ports are published and no
forwarding service or firewall grants are needed. Listeners are configured for
loopback access without a source patch. Serving and Hermes MCP registration
begin after staged preparation; the local Hermes webapp works before a wallet
is created or funded.

| Hermes MCP name | Local port | Wallet |
| --- | --- | --- |
| x402_treazury_toolbox | 3010 | general |
| x402_treazury_web | 3011 | general |
| x402_treazury_science | 3012 | general |
| x402_treazury_shopping | 3013 | general |
| x402_treazury_world | 3014 | general |
| x402_treazury_social | 3015 | personal |
| x402_treazury_property | 3016 | personal |
| x402_treazury_travel | 3017 | personal |
| x402_treazury_health | 3018 | health |
| x402_treazury_business | 3019 | financial |
| x402_treazury_finance | 3020 | financial |
| x402_treazury_security | 3021 | financial |

Wallet pools group requests by potential payer linkability: general research,
personal context, health context, and financial interests. They are upstream
payment policies, not separate MCP access-control identities.

## Start Hermes first

```sh
make init
# Edit .env to configure an inference provider.
make build
make up
```

Log in at `http://127.0.0.1:9120` with the credentials described in
[webapp setup](webapp.md). No research treasury or MCP token is
needed for this first startup. x402_treazury remains built into the main Compose
file; the deployment workflow activates its profile after preparation. There is
no additional overlay or enablement variable.

The image builds unmodified upstream commit
`6f3e1e6fd6738c5fece86dc796c5ef0686653552` using its Rust 1.99.1 toolchain and
locked dependencies. The renderer changes only the Tor SOCKS endpoint, persistent
state path, and HTTP Host allowlists. Wallet groups, rotation, funding, payment
caps, source selection, and tool selection retain upstream policy.

Inspect that policy offline before funding:

```sh
docker run --rm --network none private-hermes-x402_treazury:local config show
```

## Create the wallet and deposit when ready

```sh
make x402_treazury-init
```

This uses Tor for new-wallet birthday discovery, prints the shielded ZEC receive
address, and exits. If the wallet already exists, it displays its saved status
and address instead. Unreadable, incomplete, or incompatible state is an error;
it is never treated as permission to create a replacement wallet. It does not
start funding, serving, or Hermes MCP connections. If needed, the command starts
only Tor and the agent network namespace for the one-shot administration process.

Back up the wallet before depositing ZEC. Native wallet commands use the same
configured treasury, `x402_treazury-data` named volume, and UID as serving:

```sh
python3 scripts/stack.py compose run --rm --no-deps x402_treazury wallet backup --help
```

Choose a backup destination with an appropriate private mount; the container's
root filesystem is read-only. Never save recovery material in the Hermes or
executor workspace. No wallet creation or funding is part of `make init`.

Retrieve the address, saved balances, and preparation/activation state at any time:

```sh
make x402_treazury-status
```

Status runs without networking or exclusive wallet ownership. It reads saved
observations, not live proof of spendability, and can run while serving or
preparing. Deposit ZEC at a time of your choosing; Hermes remains usable.

## Prepare and connect research tools

Run while Hermes is up. x402_treazury uses its built-in Base RPC endpoints
through Tor; there is no operator RPC endpoint setting:

```sh
make x402_treazury-prepare
```

If matching preparation already completed, this command retries serving and
Hermes activation directly. Otherwise it runs, in order:

1. Disconnect the managed Hermes research MCP clients and gracefully stop an
   existing serving owner, if any.
2. Run `wallet bootstrap --json`, waiting for ZEC receipt/spendability and the
   native managed funding claims. This can spend ZEC under the configured policy.
3. Run `catalog warm` over Tor. Configured paid relay fallback can spend USDC.
   An exit status and structured result identify completion of each phase.
4. Start `serve`, then initialize and list tools on all twelve authenticated MCP
   endpoints without making research calls.
5. Register the managed MCP entries and call Hermes's native `reload.mcp` RPC.
   No gateway or network-namespace restart is needed. Unrelated MCP entries and
   sessions are preserved; active sessions follow Hermes's native reload policy.

Each phase streams native output. A failure stops the sequence, reports the
native exit status and recent redacted output, and leaves Hermes available.
The private preparation record retains the failed phase and recent output.
Retry the same command to resume through native wallet journals and cache policy;
never delete the state directory to retry. Bootstrap and paid warming require
exclusive ownership and must not run beside `serve` or another wallet operation.

Ctrl-C requests graceful termination and waits for native cleanup. These commands
and serving shutdown do not introduce a force-kill timeout. If a host/controller
crash leaves a one-shot container running, its name ends in `-x402-onboarding`.
Inspect it and stop it with `docker stop --timeout -1 CONTAINER` before retrying;
the workflow refuses to overwrite a retained container or competing owner.
Do not use an auto-restarting serving container for one-shot financial commands.

Completion is recorded atomically under `/var/lib/x402/onboarding/` in the
`x402_treazury-data` named volume, bound to the treasury identity, source/build identity,
coordinator code and effective configuration. The record contains no full
deployment configuration.
Only successful bootstrap and complete Tor catalog warming authorize serving.
The entrypoint checks this even when the serving profile is started manually.

Serving and MCP activation are tracked separately. If preparation succeeds but
activation fails, diagnose the serving logs and rerun preparation. A matching
successful preparation record retries only serving and Hermes activation:

```sh
python3 scripts/stack.py compose logs -f x402_treazury
make x402_treazury-prepare
```

Subsequent `make up` automatically starts and connects a prepared deployment.
Changed or missing preparation leaves research disconnected and prints the next
step. A completion record is historical evidence: balances can change, catalogs
expire, and serving continues native synchronization, replacement funding, and
discovery under its policy. Startup does not rerun explicit bootstrap/warming.

`catalog warm` stores cache data under the configured treasury's `http-cache/`
directory in the same persistent directory. It never uses `--direct`. Cached entries
remain subject to native freshness, provenance, and revalidation rules; warming
is not a promise that future help, dynamic discovery or API calls are offline.

`setup mcp` provides networkless token/registration operations in the stock
Hermes setup service. The setup service also prepares storage and has wallet-volume
access for ownership/lock checks, but does not run native wallet commands. Only activation
copies the serving token into Hermes and installs its twelve MCP entries.
Disconnecting removes only managed entries and that token from the profile, preserving unrelated
configuration. `x402_treazury-admin` runs offline inspection and record updates;
networked init/preparation uses `x402_treazury-setup` one-shot containers in the
agent namespace. Jobs have no automatic restart policy, so a failed financial
command cannot be repeated by Docker; retries are explicit operator actions.

## Secrets and execution boundary

- x402_treazury runs as UID 10003 with a separate PID namespace and mount
  namespace, no capabilities, a read-only root, and a private `x402_treazury-data`
  named volume. Hermes has neither that directory nor the server's private token mount.
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
Use the deployment workflow for graceful financial shutdown; `make down` waits
for native cleanup. `x402_treazury-data` contains wallet data and `data/x402_treazury-auth/`
contains the persistent MCP token. Ordinary `docker compose down` preserves this volume and token directory.
`docker compose down -v` deletes the wallet volume; do not use it for routine shutdown. Back up wallet/recovery material using the
upstream wallet guidance and protect backups as secrets.
The default `wallet.key` is stored alongside encrypted wallet state; obtaining
that directory gives access to both state and its decryption key. The native
`wallet backup` command includes the encryption key. A full private-directory backup
also preserves the deployment preparation record and catalog cache. A missing
preparation record requires explicit preparation again; it never authorizes
creation of a replacement wallet.

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
