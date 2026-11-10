# Development and qualification

For operator setup, see [the README](../README.md). For network design and
execution boundaries, see [architecture and isolation](architecture.md).
Read [AGENTS.md](../AGENTS.md) before changing the stack and follow the
[planning workflow](planning-workflow.md) for substantial staged work.

## Repository layout and local configuration

- `components/`: tracked Dockerfiles, container scripts, and component defaults.
- `.env`: private operator settings, selected explicitly for each service.
- `config/`: private editable bind-mount configuration; initialized from defaults.
- `data/`: persistent bind directories for identities and executor work.
- `scripts/`: host-side initialization and checks.
- `tests/fixtures/`: disposable test servers and configuration.

`make init` creates missing local configuration files and leaves existing files
unchanged. The research TOML is seeded separately from the built treasury image
after `make build` or before managed startup/treasury commands; see
[research configuration](x402_treazury.md#edit-the-research-configuration). Add new settings explicitly using `.env.example` as a reference.
`make build` and `make up` run it automatically. Saved-wallet commands do not run
full initialization; new-wallet creation prepares only its Tor/network host inputs. Image pins and source revisions live
in Compose and component Dockerfiles, not `.env`. Hermes and wallet state use native named volumes; other persistent files live
in `data/`. Runtime Tor socket IPC also uses a named volume. See
[configuration and backups](configuration.md) before starting.

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
Tests use separate project volumes and private temporary bind directories, never
the operator's volumes or `data/` tree. Only disposable test resources are deleted.

References: [Hermes backends](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/#terminal-backend-configuration),
[Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security/),
[Dockurr Tor](https://github.com/dockur/tor),
[Docker isolated networks](https://docs.docker.com/engine/network/port-publishing/#gateway-modes),
[teep](https://github.com/13rac1/teep).

Component-specific checks and limits are documented in the
[webapp](webapp.md#verification-and-current-limits),
[x402_treazury](x402_treazury.md#stop-and-test), and
[updates and plugins](updates-and-plugins.md) guides.

## Diagnostic messages

Explain the affected operation or capability, its impact, the known cause or
uncertainty, and a useful next action when established. Messages must make sense
without decoding implementation stage names or error categories; structured
fields supplement that explanation. Include safe causes and status information,
never credentials, raw protocol responses or credential-bearing upstream prose.

Choose severity at the owner that knows the outcome after applicable recovery:
ERROR for unavailable required service/endpoint functionality, WARN for a terminal
requested-operation failure or unexpected loss of functionality, INFO for useful
lifecycle/progress/recovery messages, and DEBUG/TRACE for routine attempts and
diagnostic detail. An intermediate failure with retry remaining is not a terminal
operation failure. Elapsed time or repetition alone does not promote severity.
Scope errors to the affected capability rather than announcing whole-stack failure.
When outcome is uncertain, say so; do not imply that a payment is safe to repeat.

Endpoint activation follows Docker logs from the serving container's `StartedAt`.
The pinned x402_treazury revision has no public typed endpoint-readiness signal;
the wrapper recognizes its two exact terminal endpoint diagnostic messages from
`deployment.rs` and `deployment/deferred.rs`. This is not a general log-severity
failure policy: recoverable native ERROR events do not fail activation. Recheck
those native messages and their semantics when changing the treasury pin, using
`tests/endpoint_readiness_smoke.py`. Replace this recognition when a native typed
signal provides equivalent behavior; do not add historical-message compatibility
parsers. The observer and read-only authenticated probes add no treasury state.
Closing the controller's input pipe cancels the remote probe, including when the
controller exits unexpectedly. Protocol waits remain cancellable without an
additional startup deadline. Reporting cadence is independent of failure policy.
