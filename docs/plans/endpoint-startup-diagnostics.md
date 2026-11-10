# Endpoint startup diagnostics without failure deadlines

Status: proposed; design review pending.
Baseline: branch `webapp-private-content`, commit `c8cb1e2aa6a94a3f5558d2f4272a8c9b8837f1e6`.

## Intent and current behavior

Add the agreed generalized enforcement rules and supporting clarifications. Keep
all twelve authenticated research endpoints required before Hermes registration.
The current activation loop silently retries transient MCP probes, prints waiting
only once, and notices service exit/restart but not native endpoint failures that
leave other endpoints/processes alive. The user wants native endpoint errors and
regular progress messages, without a whole-startup deadline or attempt cutoff.

Pinned native source/image: `424f36a814711d542fbff27f139842c9d08d5b76`.
Its deployment listener task emits a specific terminal endpoint diagnostic and
closes that listener, while deliberately retaining the process and other listeners.
There is no external typed endpoint-readiness API in this revision. Generic ERROR
logs (for example retrying SOCKS reachability) do not imply terminal endpoint failure.

## Smallest approach and preserved boundaries

- Add short AGENTS rules for checking component-owned enforcement first, separating
  authoritative state from derived/advisory information, and distinct timer purposes.
  Explain native accepted-work ownership/no-replay in the treasury guide; document
  plain-language, scoped diagnostics and severity in the development guide. Do not
  import the reference project's review bureaucracy, financial engine or journaling.
- Follow current-serving-lifetime Docker logs during activation, display native
  diagnostics, and recognize only the pinned revision's two explicit terminal
  endpoint diagnostic messages. Treat them as failure even if the container stays
  running. Do not infer failure from elapsed time, silence, arbitrary log severity,
  funding readiness announcements, missing optional evidence or retry counts.
- Keep authenticated initialize/list probes as readiness evidence. Poll a running
  probe subprocess so native errors, process replacement/restart and Ctrl-C remain
  observable even while a protocol request is waiting. End only the local probe/log
  helpers on activation failure/cancellation; do not stop or replay treasury work.
- Emit an initial waiting message and repeat it every 30 seconds while pending.
  That is a reporting cadence, not a readiness or financial-authority deadline.
  Preserve existing protocol transport timeouts; add no overall startup timer.
- Scope log replay to the current container StartedAt so a corrected restart does
  not inherit old terminal errors. Loss of the log observer fails activation visibly
  rather than silently dropping the native-error channel. No new service, persistent
  marker, health retry policy, upstream patch or configuration option is needed.
- Exact diagnostic recognition is deliberately tied to the pinned source; verify
  the contract with a real native terminal-failure fixture and review it on upgrades.
  Replace recognition if a future native typed readiness signal supplies equivalent
  semantics; do not add a compatibility parser or broad log-based policy engine.

Keep wallet preparation history, native financial journals and all existing network,
credential, process and mount boundaries. No financial actions or live Funnel
publication are authorized. Docker health remains deferred: repeated unsuccessful
probes alone cannot distinguish slow native startup from terminal failure, and its
retry-count transition would add a separate failure policy without solving that.

## Phase P1: implementation, documentation and qualification

Independent design review precedes implementation. Update controller consumers and
focused tests: delayed success, terminal endpoint error with live peers, retryable
native ERROR, service exit/restart/replacement, observer failure, cancellation,
reporting without a deadline, and no MCP registration on failure. Use deterministic
synchronization/fake clocks rather than sleeping through progress intervals.

Use disposable networkless real-image fixtures with ephemeral unfunded static keys
and local catalogs for actual authenticated probes, native terminal endpoint errors
while peers remain live, and corrected restart without stale-error poisoning. No
wallet bootstrap, funding, paid calls or operator state. Reuse existing focused
checks and run only affected integration checks. Update maintained guides, reconcile
prior plans by linking any superseded diagnostic claims, record evidence here, and
commit coherent completed work. Independent final combined/P1 review is required.
