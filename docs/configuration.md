# Configuration ownership and backups

## Repository files and local files

`components/` contains tracked implementation files and defaults, grouped by
component. Dockerfiles retain their base image and source-revision pins. The
Hermes image digest is defined once under `x-hermes-image` in `compose.yaml`.
Changing an image version is a reviewed repository change rather than a local
`.env` override.

The root `.env` is the unified operator configuration input to Compose. Start
with `make init`, edit the desired settings, then build/start the stack. The
initializer creates a missing `.env` from `.env.example` with mode 0600. It
leaves existing contents and permissions unchanged; add new settings explicitly
using the example as a reference. Existing exported
shell variables retain Compose's normal precedence over `.env` values.

Compose explicitly selects each service's environment variables:

| Settings | Recipient |
| --- | --- |
| Inference provider API keys | teep |
| `BASE_RPC_URL` | x402_treazury serving/administration containers |
| `TS_AUTHKEY` | Optional Tailscale container |
| Funnel enablement, local webapp port and hostname | Deployment workflow and selected ingress components |

Generated webapp credentials are kept separately under `config/webapp/`; see
[webapp setup](webapp.md). The existing networkless bootstrap copies native auth settings into
Hermes state during bootstrap without exposing them to the executor.
`make init` creates missing webapp credentials and renders proxy configuration;
repeating it preserves the credentials.

No service loads the entire root `.env`. Hermes and the SSH executor receive
none of the provider, funding, or Tailscale credentials. Keep provider and funding credentials out of the
Hermes workspace, skills, and profile. Add future deployment settings to the
example and explicit Compose mappings together.

`config/` contains operator-owned editable files mounted into services. The
initial file is `config/network/mcp-allowlist.json`; its tracked default is
`components/network/mcp-allowlist.json`. `make init` creates the local copy only
if missing. Existing local policy is preserved. The service mounts it read-only,
and Compose refuses to create a directory if the source file is missing. Run
`make init` before starting a fresh checkout. Use `make up` and the
`scripts/stack.py compose` wrapper so enabled ingress layers are selected.

Other component files, such as Tor/SSH settings, resolver settings, and the
initial Hermes configuration template, remain implementation-owned defaults.
They live beside their owning components. Their existing delivery through image
COPY instructions or read-only bind mounts is preserved. Moving these files
does not implement the separate read-only Hermes configuration plan.

## Persistent data layout

Hermes profile/database state and x402_treazury wallet/database state use native
Docker named volumes (`hermes-data` and `x402_treazury-data`). Other persistent
files use the bind directories below. This keeps lock-sensitive state off the
host-backed filesystem that failed qualification on this Docker Desktop host.
`storage-init` checks locking on the native volumes before applications start.
No existing volume contents are copied or deleted by this change.

PrivateOnyxApp's PostgreSQL/OpenSearch initialization was checked as a possible
workaround. Its Podman path initializes a temporary native volume and copies the
stopped database into the host bind; its macOS PostgreSQL preparation removes
only `user.containers.override_stat`. That attribute was absent on our test paths,
and Docker's `com.docker.grpcfuse.ownership` attribute must remain intact.

Our disposable mount reports filesystem type `fakeowner`. A competing process
incorrectly acquired an exclusive lock on a freshly created file, but correctly
failed after the file was closed and reopened. This matches the creation-path
behavior described in [Docker issue #7004](https://github.com/docker/for-mac/issues/7004).
Initializing a SQLite database in native container storage, closing it, copying it
to the bind, and then opening it in WAL mode still allowed two writers to acquire
the writer lock. Consequently, staging initialization or changing ownership is
not a sufficient workaround for this host. Qualification must include fresh-file
locking and SQLite writer exclusion, rather than just successful startup or
database reads/writes. These observations describe the tested host, not all
Docker Desktop or Linux bind mounts.

Track that upstream issue when evaluating Docker Desktop updates. Before moving
live state to host binds, rerun the fresh-file `flock` and competing SQLite WAL
writer probes on the proposed bind filesystem; existing-file locking alone is
not sufficient. `components/provisioning/storage.py:verify_filesystem` contains
both probes. Do not remove the checks or assume that closing the upstream issue
qualifies a particular host. `make storage-test` checks the current native-volume
layout and verifies files and SQLite data survive ordinary Compose `down` and
container recreation, using only a disposable test project and no network access.

After rebuilding the provisioning image following an engine update, test the
host-backed `data/` filesystem directly with:

```sh
docker compose run --rm --no-deps --entrypoint python3 storage-init /opt/storage.py --check-filesystem /persistent-data
```

This creates and removes temporary probe files without changing application data
or permissions. A nonzero exit means the filesystem is still unsuitable. Passing
these probes is necessary before considering a storage-layout change; it does
not by itself change the deployment or replace full application qualification.

| Storage | Contents |
| --- | --- |
| `hermes-data` named volume | Hermes profile, configuration, credentials, conversations, memory, skills and uploads |
| `data/executor/workspace/` | Durable agent-created work, repositories, documents and scripts |
| `data/executor/home/` | Executor home, shell/tool configuration and caches |
| `data/ssh/agent/` | Agent SSH client identity and pinned host trust |
| `data/ssh/executor/` | Executor host identity and authorized client key |
| `x402_treazury-data` named volume | Entire treasury home: wallet state/key, financial journals, catalog cache and onboarding record |
| `data/x402_treazury-auth/` | Persistent MCP bearer token, separately mounted from the wallet |
| `data/tor/` | Tor guard-selection and persistent Tor state |
| `data/tailscale/` | Optional Funnel node enrollment and identity |

`make init` creates missing directories without replacing data. A trusted,
networkless `storage-init` process checks native-volume filesystem locking and sets the declared
leaf-directory UIDs, GIDs and modes before applications start. It does not
recursively chown/chmod existing files. Restore backups with their ownership and
permissions intact rather than relying on initialization to repair file metadata.

The host-owned `data/` parent is mode 0700. Application identities remain unchanged;
wallet and SSH private-file permissions remain restrictive. On Linux, service-owned
private directories may require privileged access or a container backup helper
for backup. Do not loosen wallet permissions to make them readable to host tools.

Only the trusted metadata initializer mounts the whole `data/` parent. Hermes,
the executor, financial services, Tor and Tailscale each receive their own leaf
mounts. The executor never receives Hermes state, wallet files, or the MCP token.
The shared Tor Unix-socket directory remains a Docker volume: it is runtime IPC,
not backup data. `/tmp` remains disposable; `/workspace` is durable work, not an
automatically cleared scratch directory.

`.env`, `config/`, and `data/` are Git-ignored and excluded from Docker build
contexts. Builds receive only `components/`.

## Applying configuration changes

Edit the root `.env` and local MCP policy as needed. Recreate the deployment
with `make down` followed by `make up` when changing namespace configuration;
retain persistent data. Rebuild images with `make build` after implementation
changes. Wallet initialization and funding remain explicit operator actions.

## Backup scope

Back up the root `.env` and `config/` as private operator configuration. Protect
these backups as secrets; `.env` may contain paid API keys or authenticated RPC
URLs. Record the repository commit so the corresponding implementation and
image/source pins can be recovered.

The backup scope is `.env`, `config/`, `data/`, and both application named volumes,
together with the repository revision needed to reproduce images and configuration.
Protect all of these as
secrets. x402_treazury keeps its encryption key alongside encrypted wallet state;
its native wallet backup also contains that key.

Use the native wallet backup command or gracefully stop writers with `make down`
before making a complete filesystem copy. Copying live SQLite databases and their
sidecars independently is not a consistent backup. Preserve file modes, ownership
and the full application directories. Tor sockets and other runtime IPC do not
need backup. `make down` and ordinary `docker compose down` retain named volumes
and host bind directories. Starting again with the same Compose project name
reattaches the existing volumes. The default project name is `private-hermes`;
changing it selects a different set of volumes. `docker compose down -v` explicitly
deletes the application volumes, including wallets and conversations, as well as
the runtime socket volume. Do not use it on a deployment whose state you need.
Deleting bind-mounted host data requires a separate filesystem operation.
Backing up `data/` alone does not include the application volumes.

Hermes's generated profile `.env` in `hermes-data` is distinct from the root
deployment `.env`: it contains the MCP token and Hermes-owned credentials.
`x402_treazury-data` contains preparation records and catalog cache as well as
the wallet. Those records are historical preparation evidence, not current
spendability or perpetual cache freshness. Host operation locks remain under
`config/x402_treazury/`. See [staged onboarding](x402_treazury.md).
