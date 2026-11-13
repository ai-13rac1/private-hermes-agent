# Private Hermes

Private Hermes is a Docker Compose stack for running [Hermes Agent](https://github.com/NousResearch/hermes-agent)
with private research tools, code execution in a separate container, and an
authenticated web interface. It brings together Tor-routed Internet access,
confidential-computing inference through Teep, and paid research APIs through
x402_treazury.

The goal is to let an agent research and write code while keeping your network
address, inference requests, and agent payment history private, and
[sandboxing the agent](#service-hardening) from accessing your local machine.
You can use Hermes through your browser or terminal, and optionally enable public
HTTPS access through Tailscale Funnel.

By default, the webapp also prevents [displayed content](#web-page-previews) from
bypassing Tor through your own browser: supported external images load through
the stack's Tor gateway, and active external content is blocked. You can use
a normal browser with these protections; deliberate external link clicks
still use your browser's connection.

## Components and the problems they solve

- **Hermes Agent v0.23.1** provides chat, tool use, skills, and subagent orchestration.
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
amount among Near Intents Base USDC swaps. Closely spaced funding swaps are
easier to correlate. x402_treazury makes effort to schedule swaps early and
decouple their execution from prior transactions, but this unlinkability
ultimately depends upon the incoming volume of Base USDC swaps coming from Near
Intents over the course of your usage. After an initial single bootstrap wallet
phase, the provided configuration uses four distinct sets of rotating USDC
wallets, with usage assigned by x402 API endpoint topic. These wallets rotate
independently. See the [x402_treazury guide](docs/x402_treazury.md) for funding,
wallet groups, and operation.

## Get started

You need a container engine, Compose 2.36+, `make`, and Python 3. Use either:

- **Docker Engine 28+** with Linux containers, or
- **rootless Podman 5.4+** on Linux, with the user API socket enabled:
  `systemctl --user enable --now podman.socket`. Set `CONTAINER_ENGINE=podman`
  in `.env`. Rootless Podman runs no root daemon, and container root maps to
  your unprivileged user. No `docker` command is needed.

`CONTAINER_ENGINE` in `.env` selects the engine (`docker` when absent); an
exported value overrides it. The stack adds the Podman overlay files itself. It requires isolated
bridge networking and Linux GRE support; startup checks reject unsupported
setups. Its fixed `10.203.80.0/24` through `10.203.84.0/24` networks, local
ingress `10.203.85.0/24`, and optional Funnel `10.203.87.0/24` must not overlap
your existing networks.

On rootless Podman, Compose 2.36+ must be the provider of `podman compose`;
Debian 13's `docker-compose` package is older. Install the Compose release binary
for your user and set `PODMAN_COMPOSE_PROVIDER` to its path, or name it in
`compose_providers` in `~/.config/containers/containers.conf`. Containers stop
when you log out unless lingering is enabled for your user (`loginctl
enable-linger`, which may need an administrator). After a reboot, run `make up`
to start the stack again. Keep the default `WEBAPP_PORT=9120` or another port
of 1024 or above: a rootless user can publish a lower port only if the host
allows it. See [engine differences](docs/architecture.md#rootless-podman).

Initialize your local settings:

```sh
make init
```

Set `NEARAI_API_KEY` in the generated root `.env` for the default NearAI
`neardirect` inference route through Teep. The default model is
`neardirect:z-ai/glm-5.3-flash-long`. Set `HERMES_DEFAULT_MODEL` in `.env` and
run `make up` to choose another default. See [inference configuration](docs/configuration.md#host-inference-access)
for model selection and the local OpenAI-compatible endpoint.

To build and start the stack:

```sh
make up
```

Builds need Internet access, and use your host's default networking for this purpose, not Tor.

Once the stack is up, open **http://127.0.0.1:9120** and log in as `admin` with
the password saved in the file `config/webapp/password`.

If you prefer terminal use, you can use the terminal client with:

```sh
make chat
```

## Paid Research APIs and Cryptocurreny Wallet

The stack includes [x402_treazury](https://github.com/mikeperry-tor/x402_treazury/),
which gives Hermes Agent a full set of x402 APIs to conduct web searches, web page access,
and access a large collection of data services using privacy-enhanced [x402 micropayments](https://x402.org/).

to create a
treasury and back it up before depositing ZEC:

```sh
make x402_treazury-init
```

The provided `config/x402_treazury/research_desk.toml` (created after `make
x402_treazury_init`) has 12 MCP endpoints organized by topic, automatically
connected to your Hermes Agent. Funding this wallet with $5 worth of ZEC will
enable all endpoints sharing a pair of ~$2.50 USDC wallets.

This will get you started, but the privacy properties of x402_treazury increase
if you add $20 worth of ZEC. The 12 MCP endpoints will then be separated across
four independent wallet groups after your agent uses an API from a group for the
first time. This avoids linking research across broad high-level areas.

You can still start with $5 worth of ZEC to try it out, and then add more ZEC to
the agent's shielded wallet at any time; the four isolated wallet groups will
then be created as you use those topics.

The actual USDC wallet addresses also rotate to reduce long-term linkability of
your research over time. See the
[x402_treazury README](https://github.com/mikeperry-tor/x402_treazury/#how-it-works) for
details on this process and the privacy properties it provides.

After funding the displayed shielded receive address with sufficient ZEC, ensure
the stack is up (`make up`), then run:

```sh
make x402_treazury-prepare
```

Preparation funds a single initial shared bootstrap wallet, warms provider
catalogs, and connects research tools without restarting Hermes. The 12 MCP
endpoints will be added to Hermes Agent automatically, but the agent will be
unable to use any x402_treazury APIs until funding and catalog warming complete.

Use `make x402_treazury-status` to inspect current wallet funding status and shielded ZEC fudning address (this also works while the stack is down).

See the [x402_treazury README](https://github.com/mikeperry-tor/x402_treazury/blob/main/README.md),
[README_ADVANCED.md](https://github.com/mikeperry-tor/x402_treazury/blob/main/README_ADVANCED.md),
and this repository's [x402_treazury onboarding guide](docs/x402_treazury.md)
for more information.

For config changes after the stack is running, stop with `make down`, edit, then
restart with `make up`; there is no hot reload.

## Living Dangerously: Full wallet access

You can also give the agent a general-purpose cryptocurrency wallet by uncommenting
the `[servers.toolbox.swap_control]` stanza at the bottom of `config/x402_treazury/research_desk.toml`.

This gives your agent **full control over their ZEC wallet**: they can send and
receive shielded ZEC using single-use shielded addresses, create
exact-input-amount cryptocurrency addresses on Near Intents for any supported
cryptocurrency, and execute Near Intents swaps of any amount to any
cryptocurrency destination address supported by Near Intents.

**This allows your Hermes agent to conduct arbitrary cryptocurrency activity**.
The default outgoing limit is 0.5 ZEC, but if you leave that commented, there is
no outgoing limit other than whatever ZEC you send to your agent's wallet. Send
and receive swap tools can be enabled independently.

These tools are available on the `x402_treazury_toolbox` MCP endpoint, which
also contains tools to perform arbitrary x402 raw calls by default, even without
this swap option enabled. You can give this toolbox endpoint to select agent
profiles in the Hermes agent profile configuration tools panel.

As with everything else in this stack, all swaps are conducted over Tor. Swaps use independently isolated Tor circuits.

> *NOTE*: There currently is no way to transfer ZEC out of x402_treazury
> other than by enabling this feature and politely asking your agent to please
> send you its remaining ZEC. **Be kind to your agents!**

## Web Page Previews

The default stack protects you from IP address leaks through your own web browser,
regardless of browser version, through a Browser Content Security Policy and internal
Tor proxy that loads basic images and videos through Tor, and blocks all other content.
This policy only covers content within the Hermes Agent Web UI. Any links you
click on will load through your browser's default network.

To allow Hermes Agent to show you previews of web pages inside the agent Web UI,
set `WEBAPP_EXTERNAL_CONTENT=browser_native`
in `.env`, run `make up`, reload the webapp and start a new conversation.

If IP address privacy is impotant to you, use this mode only with Tor Browser or
Brave Browser's Private Window with Tor and Tailscale (`TAILSCALE_FUNNEL_ENABLED`); the stack does not detect or verify browser Tor routing in `browser_native` content access mode.

See the [webapp content policy](docs/webapp.md#external-content-policy) for modes and
limits.

## Browser and Computer Use

To give Hermes Agent a full Linux graphical desktop environment inside an isolated docker service, set `COMPUTER_USE_ENABLED=true` in `.env`, then run `make down` and
`make up`.

This selects a substantially larger image and enables computer-use
and browser automation tools for the agent to use.

For remote browser access, follow the [optional Funnel setup](docs/webapp.md#optional-public-funnel).
Funnel is disabled by default and requires explicit enrollment and activation.

## Updates and Backups

The stack will automatically update componet images with the following sequence:

```bash
make down
git pull
make up
```

If the upstream x402_treazury research_desk.toml config changes during update,
or you make local changes to `config/x402_treazury/research_desk.toml`, then
`make up` and `make x402_treazury-prepare` display differences from the packaged
defaults. You can restore this file to the defaults by removing it: `make
x402_treazury-config` will create this file if missing (but preserves an
existing file).

Use `make check-updates` to check stack versions and `make plugins` to manage
persistent Hermes plugins. See [updates, plugins, and privacy
defaults](docs/updates-and-plugins.md) for applying plugin updates and
understanding plugin authority.

Backups must include the named volumes as well as local `config` and `data`
directories; see [backup scope](docs/configuration.md#backup-scope).

## Service hardening

Private Hermes adds substantially stronger containment than the
[stock Hermes v0.23.1 Compose setup](https://github.com/NousResearch/hermes-agent/blob/v0.23.1/docker-compose.yml),
which uses host networking.

The additional controls limit what malicious tool output, prompt-injected
commands, or a compromised service can reach:

- **Network containment:** Hermes and its executor have isolated networks and
  default-deny firewalls. These block access to host/VM services, private networks,
  and cloud metadata addresses, and prevent direct Internet fallback if Tor fails.
  Only explicitly required internal connections are allowed. Tor egress does not
  cover Teep's direct provider connection or your browser's connection to the webapp.
- **Code and secret separation:** Agent code and desktop usage runs as an
  unprivileged user in the SSH executor, without mounts for agent config, provider
  keys or wallets. This limits theft or modification of those files by generated code.
  Different agent profiles share the same code and desktop environment.
- **Reduced service privileges:** services drop default container capabilities
  and receive only those needed for their work, with privilege escalation through
  setuid executables and file capabilities blocked. The executor and most
  supporting services have read-only root filesystems, limiting system-file
  modification while keeping designated state and work directories writable.
- **Protected browser rendering:** the default webapp content policy prevents
  automatic external content from exposing the viewing browser's network address,
  including when you use a normal browser.

These controls reduce exposure and the damage a compromise can cause; they do
not guarantee protection against kernel/container-engine exploits or a compromised
host.

For exact grants and trust boundaries, see
[architecture and isolation](docs/architecture.md). For build procedures and
test coverage, see [development and qualification](docs/development.md).