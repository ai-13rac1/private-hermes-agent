# Staged x402_treazury onboarding

Status: implemented and locally qualified. Live wallet creation and funded
preparation have not been performed.

## Objective

Let the operator start Hermes, log in to the local webapp, and configure inference
before creating or funding the research treasury. Keep x402_treazury a built-in
component of the main Compose deployment, with staged activation rather than a
separate optional overlay.

Use command completion and exit status to identify preparation milestones.
Do not infer progress or success by scraping `serve` logs. Preparation must work
while Hermes and the rest of the stack remain available.

The four upstream phases are:

1. Create the treasury wallet and obtain its shielded ZEC receive address.
2. The operator deposits ZEC, at a time of their choosing.
3. Observe receipt and fund the configured managed USDC wallet pools.
4. Fetch and cache the configured API catalogs before connecting Hermes.

Use the existing `wallet init`, `wallet status`, `wallet bootstrap`, and
`catalog warm` commands. No upstream extension is currently required. Qualify
their exact behavior against the pinned image during implementation.

## Operator workflow

| Command | Behavior |
| --- | --- |
| `make init` | Create missing local configuration and webapp credentials. No wallet creation, network startup, funding, or MCP connection. |
| `make build` | Build the stack images, including x402_treazury. No wallet or funding operations. |
| `make up` | Start the core stack and authenticated local webapp. Start and connect x402_treazury only when its preparation record is valid. |
| `make x402_treazury-init` | Create a new wallet only when demonstrably absent; otherwise display existing status and receive address. Exit after showing the address and backup guidance. |
| `make x402_treazury-status` | Display saved wallet status/address and the deployment's preparation phase, including any recorded failure. Do not sync, fund, or warm catalogs. |
| `make x402_treazury-prepare` | Run `wallet bootstrap`, then `catalog warm`, then start `serve` and connect Hermes after successful readiness checks. Stop at the first failed phase. |

The networkless `setup mcp` subcommand manages tokens and Hermes registrations.
`make x402_treazury-prepare` is also the retry command. A matching successful
preparation record retries activation without repeating bootstrap or catalog
warming. Incomplete or invalidated preparation resumes through the native
bootstrap and warming commands and their existing journals/cache policy.

Initial use:

```text
make init -> edit .env -> make build -> make up
                                           |
                              log in and explore Hermes
                                           |
                           make x402_treazury-init
                                           |
                       back up wallet; deposit ZEC when ready
                                           |
                         make x402_treazury-prepare
                                           |
                  wallet bootstrap -> catalog warm -> serve
                                           |
                        connect Hermes research MCP clients
```

Wallet initialization discovers a birthday over the configured Tor connection.
Reuse the running stack's Tor infrastructure for the one-shot command. If core
services are not running, start only the dependencies needed for wallet
administration, never the serving process or Hermes MCP connections implicitly.
Repeat initialization displays the existing address; it never replaces a wallet.

The deposit is an external action. Do not require it before Hermes can start,
and do not make `make init` wait for funds. Preparation can be started before
funds arrive; `wallet bootstrap` may wait while the operator continues using
Hermes in another terminal or browser tab.

## Preparation execution and recovery

Run each phase as a separate one-shot process using the production image,
deployment configuration, persistent state, Tor socket, UID, and network policy.

1. **Inspect the wallet.** Distinguish missing state from existing, unreadable,
   incomplete, or incompatible state. A failed status command is not evidence
   that initialization is safe. Require a valid existing treasury for preparation.
2. **Run `wallet bootstrap`.** Use its exit status and machine-readable result
   where supported. This step operates the configured funding policy and can
   spend deposited ZEC. It waits for the native captured funding claims to
   complete; preserve the distinction between completed work and current serving
   capacity. Do not invent extra funding targets or financial limits.
3. **Run `catalog warm`.** Select the configured deployment's sources and retain
   Tor policy. Never add `--direct` or a direct-network fallback. Warming may
   spend from managed wallets through the configured paid relay policy. Check
   the exit status and structured summary before advancing. Report cache entries
   needing revalidation or not stored; a successful warm is not a promise that
   all future help, dynamic discovery, or API requests are cached.
4. **Start `serve`.** Only after both commands succeed and release ownership.
   Validate authenticated MCP initialization/listing on every configured
   endpoint without making paid research calls. Use protocol checks, not a log
   message or an open TCP port, to establish connection readiness.
5. **Connect Hermes.** Install or enable only the managed x402_treazury entries
   and reload its MCP clients. Verify reload support in the pinned Hermes image;
   if necessary, restart only the Hermes process, preserving its sessions and
   the network namespace. Do not restart the stack or affect unrelated MCPs.

Stream phase output to the operator and retain a bounded recent-output tail for
failure diagnosis in private storage. Report the phase, native exit status,
useful structured result, and immediately preceding output without printing
keys, tokens, environment dumps, or seed material. Do not impose arbitrary phase
deadlines, retry budgets, storage quotas, or new transaction limits.

A failed phase stops the sequence and leaves Hermes usable. Retrying incomplete or invalidated preparation
reruns the native resumable commands against the same treasury; it does not
erase state, recreate keys, replay shell-level payments, or discard completed
cache entries. Native journals and cache policy determine what work remains.
Do not implement retries that treat incomplete financial work as absent.

Serialize wallet-owning operations per deployment. Do not run bootstrap, paid
warming, sync, or another serving process against a treasury already owned by
`serve`. An explicit preparation rerun must stop the serving process gracefully
before acquiring ownership and disconnect its managed MCP clients while it is
unavailable. Unrelated Hermes functions remain running. On interruption, use
the upstream graceful shutdown path and preserve journals; do not force-kill
wallet operations as a routine timeout mechanism.

`wallet status` and `wallet addresses` can inspect saved snapshots while serving.
Label their data as saved observations, not live proof of spendability. They
must not trigger preparation or repair state.

## Startup, registration, and completion records

- Keep service definitions in `compose.yaml`. Remove Hermes's mandatory startup
  dependency on an unprepared x402_treazury service and stop unconditional MCP
  registration in the current setup step.
- Have the deployment workflow explicitly select the services appropriate to
  the preparation state. Address bare Compose startup too: it must not bypass
  staged activation and launch unprepared serving/funding accidentally. A profile
  or entrypoint guard is an implementation choice, not a separate overlay or
  another operator opt-in setting.
- On a fresh stack, leave the managed MCP entries absent or disabled so Hermes
  does not attempt twelve failing connections. Preparing a wallet alone does not
  connect Hermes. Generate the serving token and register endpoints at the
  appropriate activation step without exposing financial secrets.
- Store an atomic, private preparation record with the x402_treazury state,
  accessible to trusted deployment tooling but not Hermes or the executor.
  Record completed phases, the treasury identity, relevant image/source identity,
  deployment fingerprint, and failure information. Do not record secret values
  or create a second ledger of financial authority.
- Bind completion to the effective deployment's wallet assignments, funding
  policy, source selections, and relevant image/configuration identity. A copied
  marker must not authorize another treasury. Define the fingerprint inputs and
  validate the treasury identity before reusing a record.
- Record preparation completion only after successful bootstrap and warming.
  Track serving/connection success separately, so a failed process launch or
  Hermes reload does not pretend that funding failed. A crash between phases
  must remain safely retryable.
- Subsequent `make up` may start a prepared service and reconnect its MCP clients.
  Missing or invalidated completion leaves Hermes available and directs the
  operator to explicit preparation; it must not silently start new preparation.
  Existing ambiguous or damaged state requires diagnosis, never automatic init.
- Completion is historical evidence, not perpetual readiness. Catalogs expire,
  balances change, and `serve` continues native synchronization, replacement
  funding, and discovery under its configured policy. Ordinary restarts can
  therefore perform that native work. Document this distinction rather than
  making startup run bootstrap or warming again automatically.
- A serving or MCP-connection failure must be visible without preventing local
  Hermes access. Keep failed research connections from becoming a gateway
  startup requirement.

## Boundaries and repository organization

Preserve the shared agent network namespace, loopback-only authenticated MCP
listeners, Tor Unix socket, wallet filesystem separation, and SSH executor
isolation. No host port publication, Docker socket in Hermes, or webapp-driven
container management is needed. Core bootstrap must remain networkless and must
not mount wallet state.

Continue using `.env` for operator settings, component Dockerfiles/Compose for
image pins, `components/x402_treazury/` for implementation, and the existing
private state volume for wallet data. Use the deployment-aware Compose wrapper
so optional Funnel configuration remains consistent. Preserve unrelated Hermes
configuration and MCP entries when connecting or disconnecting research tools.

No backward compatibility, migration code, wallet restoration automation, new
webapp onboarding UI, or arbitrary resource/storage limits are part of this work.
Update README, configuration, and x402_treazury operator guidance together; the
operator workflow allows ordinary `make up` before treasury initialization or funding.

## Implementation sequence and acceptance

1. Qualify native command exit statuses, JSON results, ownership behavior, cache
   location/persistence, and initialization state detection using the pinned image.
2. Implement initial core startup without treasury preparation or MCP connection.
3. Add wallet init/status commands and the resumable preparation coordinator,
   private records, serialization, and phase failure reporting.
4. Add conditional serving and Hermes MCP registration/reload after success;
   support subsequent startup and graceful preparation reruns.
5. Update operator documentation and run the existing checks and relevant
   integration suites. No live wallet creation or spending is needed to implement
   this plan; real funding qualification is a separately authorized operator step.

Acceptance checks must cover:

- Fresh and repeated `make init`; no wallet/network operations or lost credentials.
- Fresh `make up`; usable authenticated Hermes webapp without a treasury, deposit,
  or running x402_treazury process. Inference still requires
  its independently configured backend.
- New-wallet versus existing-wallet inspection; repeated init preserves identity;
  partial, corrupt, unreadable, or incompatible state never causes replacement.
- Phase ordering and early exit on failure; recent output and native exit status
  are available; no serving or MCP activation after failed bootstrap/warming.
- Cancellation, concurrency, retry after partial work, missing/invalidated records,
  configuration changes, and interruption before an atomic completion write.
- Successful preparation followed by serving and authenticated MCP connection;
  reconnect/reload failure remains distinguishable from preparation failure.
- Restart of a prepared stack; no explicit bootstrap/warm rerun; no whole-stack
  restart when activating research tools on an already-running stack.
- Persistent catalog reuse under native freshness/provenance rules, and Tor
  failure without direct fallback during initialization or preparation.
- Existing webapp, SSH, host/VM isolation, MCP authorization, and executor-secret
  regressions, including absence of wallet files and preparation records in
  Hermes/executor mounts.

Use controlled command substitutes to test orchestration failures and disposable,
unfunded fixtures for real CLI/MCP checks. Never make tests depend on a production
wallet, a ZEC deposit, paid catalogs, or live financial transactions. Report live
funding/catalog qualification separately from locally verified orchestration.

## Implementation notes and qualification

The main Compose file now defines the serving service, a non-restarting networked
job service, an offline administration service, and the networkless `setup`
service. Profiles select treasury lifecycle roles internally; no separate
onboarding overlay or operator enable flag was introduced. Core startup removes
managed research registrations before starting Hermes and conditionally activates
a matching prepared treasury afterward.

The coordinator validates native bootstrap summary schema 3, completed captured
work, and a complete non-direct catalog-warm summary. The record fingerprints
native config/build identity and coordinator contents. Base RPC endpoints use
the pinned native defaults through Tor, with no operator RPC preference.
Native cache files live
under the treasury's `http-cache/` directory. The serving entrypoint refuses
unprepared or mismatched state, including command-line configuration overrides.

One-shot jobs never inherit the serving service's automatic restart policy.
Detached jobs let the operator command capture the actual exit status while
streaming logs and retaining control of graceful shutdown. Serving and jobs use
an infinite Docker shutdown grace period; host cancellation forwards signals and
waits for native cleanup. A retained job is not overwritten automatically.

Local checks cover initialization and preparation failure/retry, lost/incomplete
state, competing owners, malformed/stale records, configuration and RPC changes,
atomic-record failure, direct-transport refusal, credential redaction, and signal
forwarding. Real unfunded Rust and pinned Hermes fixtures qualify authenticated
MCP activation and live reload/disconnection without a gateway restart. A free
public JSON OpenAPI fixture qualifies native warming over Tor, persistent cache
writes and reuse by another process with Tor stopped.

No real wallet was created, deposited into, or bootstrapped with funds. Native
financial success/failure branches are substituted for orchestration tests; live
birthday discovery, ZEC receipt and managed USDC funding remain operator
qualification steps. This distinction must remain explicit in implementation
reports and operator documentation.

Completed local checks: `make check` (36 unit checks, Compose validation and
Python compilation), `make test`, `make x402_treazury-test`, and
`make webapp-test`. Browser qualification also exercises a failed detached
production preparation job against an absent wallet, cleanup without restarting
Hermes, preservation of an unrelated MCP entry, and explicit attachment to the
existing gateway for reload. Docker's effective shutdown timeout was verified
as `-1` for the serving container. Disposable projects were removed after tests.
