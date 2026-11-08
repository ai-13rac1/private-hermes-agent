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
| `BASE_RPC_URL` | x402_treazury |
| `TS_AUTHKEY` | Optional Tailscale container |
| Webapp/Funnel enablement, local port and hostname | Deployment workflow and selected ingress components |

Generated webapp credentials are kept separately under `config/webapp/`; see
[webapp setup](webapp.md). The networkless setup copies native auth settings into
Hermes state without exposing them to the executor.

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

`data/` is reserved for a future migration to application-state bind mounts.
It has no active service mounts. `.env`, `config/`, and `data/` are Git-ignored
and excluded from Docker build contexts. Builds receive only `components/`.

## Applying configuration changes

Edit the root `.env` and local MCP policy as needed. Recreate the deployment
with `make down` followed by `make up` when changing namespace configuration;
retain named volumes. Rebuild images with `make build` after implementation
changes. Wallet initialization and funding remain explicit operator actions.

## Backup scope

Back up the root `.env` and `config/` as private operator configuration. Protect
these backups as secrets; `.env` may contain paid API keys or authenticated RPC
URLs. Record the repository commit so the corresponding implementation and
image/source pins can be recovered.

Application state remains in named Docker volumes. A configuration-directory
backup alone does not capture wallets, agent sessions/memories, SSH identities,
workspaces, the generated MCP token, or Tor state. Include those volumes in the
backup procedure, using application-consistent backups where required. The
x402_treazury guide describes the wallet backup CLI; its backups include the
wallet encryption key.

Hermes's generated profile `.env` inside its data volume is distinct from the
root deployment `.env`: the profile contains its MCP token and any Hermes-owned
credentials. Neither that token nor wallet/SSH keys are moved into the root
`.env` by this reorganization. `data/` does not contain these volumes yet.
