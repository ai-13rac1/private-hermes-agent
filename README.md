# Private Hermes

Private Hermes is a Docker Compose stack for running [Hermes Agent](https://github.com/NousResearch/hermes-agent)
with private research tools, code execution in a separate container, and an
authenticated web interface. It brings together Tor-routed Internet access,
confidential-computing inference through Teep, and paid research APIs through
x402_treazury.

The goal is to let an agent research and write code while keeping your network
address, inference requests, and agent payment history private, and sandboxing
the agent from accessing your local machine. You can use Hermes through your
browser or terminal, and optionally enable public HTTPS access through Tailscale
Funnel.

## Components and the problems they solve

- **Hermes Agent** provides chat, tool use, skills, and subagent orchestration.
  Its webapp and terminal client let you work with the same persistent agent.
- **SSH code executor** runs model-issued shell commands and Python code in a
  separate container and workspace. It keeps that code away from the agent's
  stored state, inference provider keys, and research wallet files. Sessions and
  subagents share this executor; each task does not get a separate sandbox.
- **Tor gateway** routes public TCP traffic and DNS from Hermes and its executor
  through Tor, hiding their source network address from Internet destinations.
  Network rules block direct Internet fallback and access to host, VM, and
  private-network services except the stack's explicit internal connections.
- **[Teep](https://github.com/13rac1/teep)** connects Hermes to confidential-computing
  inference providers through an OpenAI-compatible API. It handles provider
  credentials and upstream attestation checks in a separate service with its own
  direct Internet connection. The stack preserves Teep's upstream verification
  policy, including its allowed failures; service health alone does not prove
  successful attestation.
- **[x402_treazury](https://github.com/mikeperry-tor/x402_treazury)** gives Hermes
  research tools backed by paid information APIs. These provide an alternative
  to directly browsing websites that subject Tor users to extra CAPTCHAs,
  rate limits, or bans. It pays for x402 APIs using **Zcash-funded rotating Base
  USDC wallets**, with **Tor circuit isolation tied to each payment identity**.
  Rotating wallets and changing the Tor isolation identity reduce the linkability
  of API usage across payments. Hermes receives authenticated tool access while
  wallet files and spending keys stay in a separate container.
- **HAProxy and optional Tailscale Funnel** provide access to the authenticated
  webapp. HAProxy supplies the local entry point; Funnel optionally makes it
  reachable over public HTTPS without requiring visitors to join a tailnet.
  Remote access remains separate from the agent's Tor egress.

x402_treazury exposes twelve research tool groups covering web, science,
shopping, world, social, property, travel, health, business, finance, security,
and general API discovery. You can start using Hermes before creating or
funding the research treasury.

To avoid blocking during catalog and metadata downloads, x402_treazury tries
three isolated Tor circuits, then falls back to up to two paid relay downloads.
This keeps research tools available without relying on direct website browsing.

Funding swaps use Zcash, unique shielded refund addresses, and isolated Tor
circuits. The main remaining funding linkability is correlation by timing and
amount among ZEC-to-Base USDC swaps. This is greatest during the consecutive
initial funding swaps at startup; subsequent swaps occur independently as
wallets rotate. See the [x402_treazury guide](docs/x402_treazury.md) for funding,
wallet groups, and operation.

## Get started

You need Docker Engine 28+ with Linux containers, Compose 2.36+, `make`, and
Python 3. The stack requires isolated bridge networking and Linux GRE support;
startup checks reject unsupported setups. Its fixed `10.203.80.0/24` through
`10.203.84.0/24` networks, local ingress `10.203.85.0/24`, and optional Funnel
`10.203.87.0/24` must not overlap your existing networks.

Initialize your local settings:

```sh
make init
```

Set `NEARAI_API_KEY` in the generated root `.env` for the default NearAI
`neardirect` inference route through Teep. The default model is
`neardirect:z-ai/glm-5.3-flash-long`. Set `HERMES_DEFAULT_MODEL` in `.env` and
run `make up` to choose another default. See [inference configuration](docs/configuration.md#host-inference-access)
for model selection and the local OpenAI-compatible endpoint.

Start the stack (including cached image builds):

```sh
make up
```

Open **http://127.0.0.1:9120** and log in as `admin` with the password saved in
`config/webapp/password`. Tor bootstrapping can take several minutes.
`make init` preserves existing configuration and credentials; add new settings
to an existing `.env` explicitly using [`.env.example`](.env.example).
Startup rebuilds changed image inputs and reuses Docker's cache for unchanged
layers. Builds may need Internet access. Use `make build` to build ahead of time.

Use the terminal client with:

```sh
make chat
```

For remote browser access, follow the [optional Funnel setup](docs/webapp.md#optional-public-funnel).
Funnel is disabled by default and requires explicit enrollment and activation.

## Enable paid research when ready

Edit `config/x402_treazury/research_desk.toml` to adjust wallet funding policy,
payment caps, source/tool selections, or instructions.

You can restore this file to the defaults by removing it: `make x402_treazury-config`
and `make x402_treazury-init` below will create this file if missing; both commands
preserves an existing file. You can also edit the `config/x402_treazury/research_desk.toml`
**before or after** `make x402_treazury-init`: initialization does not freeze the
policy or require it to be finalized.

For config changes after the stack is running, stop with `make down`, edit, then
restart with `make up`; there is no hot reload. Starting with a changed policy
can spend funds under its automatic funding settings. Keep the deployment's
network, state paths, and listener settings intact, and use the documented
procedure when renaming wallet groups to preserve their wallets. See
[configuration and wallet renaming](docs/x402_treazury.md#edit-the-research-configuration).

Follow the [x402_treazury onboarding guide](docs/x402_treazury.md) to create a
treasury and back it up before depositing ZEC:

```sh
make x402_treazury-init
```

The `config/x402_treazury/research_desk.toml` file specifies four wallets
initially funded with a randomized amount from $2-4. This means that you need to
deposit at least $16 in ZEC to ensure all four wallets are funded. You can
reduce this requirement by changing the config file to use fewer wallets. Removing the endpoints by themselves will not eliminate the wallet funding
requirement; instead you must remove wallet definitions and then either remove those endpoints or point them at different wallets.

For example, changing all endpoints to use the `general` wallet and removing `personal`, `health`, and `financial` wallets will reduce the ZEC needed to fund the research desk down to ~$5, at the cost of associating all of your usage together under a single rotating USDC wallet.

After adjusting your wallet selection and funding the displayed shielded receive
address with sufficient ZEC, ensure the stack is up (`make up`), then run:

```sh
make x402_treazury-prepare
```

Preparation funds the API wallets, warms provider catalogs, and connects research
tools without restarting Hermes. It can spend ZEC and USDC under the configured
policy and may wait for spendable funds while the webapp remains available.
It first runs a cached build of the treasury image; build failure leaves existing
research services and preparation history untouched.
Use `make x402_treazury-status` to inspect saved status.

Live ZEC receipt, managed USDC funding, and funded catalog preparation remain
unqualified in this deployment wrapper; local fixture tests do not establish
those financial outcomes. See [remaining live qualification](docs/x402_treazury.md#pending-live-qualification).

## Everyday operation

Use `make up` and `make down` to start and stop the deployment. Ordinary shutdown
preserves conversations, configuration, wallets, and executor work. **Do not use
`docker compose down -v` for routine shutdown:** it deletes application volumes,
including wallets and conversations. Backups must include the named volumes as
well as local configuration and data; see [backup scope](docs/configuration.md#backup-scope).

Use `make check-updates` to check stack versions and `make plugins` to manage
persistent Hermes plugins. See [updates, plugins, and privacy defaults](docs/updates-and-plugins.md)
for applying updates and understanding plugin authority.

For startup diagnostics:

```sh
python3 scripts/stack.py compose logs -f hermes tor executor
```

Use the deployment-aware `scripts/stack.py compose` wrapper for other Compose
operations so your enabled options are included.

## Privacy and access limits

An authenticated webapp user has administrative agent authority. The browser's
interactive terminal runs in the agent container and is separate from the
model's SSH code executor. Plugins also run with agent privileges. Only grant
access to people and plugins you trust.

By default, supported external raster images load through the authenticated
gateway over Tor. Active previews and external players have non-loading
fallbacks. Deliberate external link clicks use your browser's own connection;
browser requests do not inherit Docker's Tor route. See [webapp content policy](docs/webapp.md#external-content-policy)
for image consent, other policy modes, and current limits.

Tor egress does not cover Teep's direct provider connection or your browser's
connection to the webapp. The container boundaries do not protect against a
compromised host or Docker engine. For exact grants and trust boundaries, see
[architecture and isolation](docs/architecture.md). For build procedures and
test coverage, see [development and qualification](docs/development.md).
