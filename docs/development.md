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

`make init` creates missing local configuration and preserves existing files.
`make up` runs it automatically, then runs cached Compose builds for the selected
base/Funnel deployment and the treasury profile before offline setup or service
changes. Treasury is included even before preparation because its image supplies
the initial policy. `make x402_treazury-prepare` builds only the owning treasury
service before inspecting preparation history or disconnecting/stopping services.
The shared setup/admin image aliases need no separate build definitions.
Build failure aborts the requested operation before those runtime changes.
Docker owns build-input detection and caching; no freshness records are stored.
Inspection, backup and shutdown do not invoke builds. `make build` constructs images only: it does not
initialize operator state or validate deployment policy. Run `make check`
explicitly for source/configuration qualification.

Research policy is seeded from the built image by `make x402_treazury-config`,
managed startup or new-wallet creation; see
[research configuration](x402_treazury.md#edit-the-research-configuration).
Startup and explicit preparation compare saved policy with the rendered default
after building/seeding, before setup or activation. Comparison uses a networkless
image container without private mounts; failures are reported as advisory.
The standalone `make x402_treazury-config-diff` performs the same comparison
without builds or seeding, and reports inspection failures with a nonzero exit.
Saved-wallet commands do not initialize unrelated state. New-wallet creation
prepares only its Tor/network host inputs. Add new settings explicitly using
`.env.example`; image/source pins remain in Compose and Dockerfiles.

Hermes and wallet state use native named volumes; other persistent files live
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

`make check` validates the Docker and Podman Compose models with the selected
engine's Compose; `tests/test_engine.py` covers the `CONTAINER_ENGINE` selector,
the engine checks, the `stack.py compose` option parsing, Podman network creation,
the proxy firewall rules and the engine floors, without a running engine. The
live tests use the same Compose files and engine commands as the stack. Run
`python3 tests/launch_smoke.py` after building Hermes to check cold passthrough
runs, dependency/namespace-owner network creation, truly offline runs, rejected
maintenance overrides and disposable network cleanup. It uses no private mounts,
Tor or wallets; serialize it with the other fixed-subnet fixtures. The same check
uses native strict-network inspection when Podman is selected. It also checks
native dry-run placement and preserves an unused network during simulated down.
Run
`make test` on each engine (`CONTAINER_ENGINE=podman make test` selects Podman
without editing `.env`) before changing network, ingress or overlay code. On
Podman, `make podman-paths-test` checks the paths of a running stack, including a
client on a network without isolation, with positive controls for its DNS, TCP
and host-loopback probes; it refuses to run unless Podman is selected.

Before the current-main rebase, on 2026-11-13, Docker Desktop ARM64
(Engine 29.9.3, Compose 5.7.0) passed
139 unit tests, all four effective models, compilation, the cold-launch/dry-run
fixture, main SSH/MCP/Tor outage/recovery and storage suites, both standalone
policy scripts (including 12 tool-policy combinations), unfunded editable research
configuration and endpoint-readiness/cancellation checks. A fresh independent
combined review accepted `817fd3d` for the source/current Docker correction scope,
with no significant findings or compelling premerge simplifications. The model
tests exercise both engine paths through the selected provider; they do not prove
Podman runtime behavior. The subsequent native lifecycle, ingress and
corrected-launch qualification is recorded below.

The subsequent rebase onto `main` `b46e050` retained v0.23.1's pnpm layout,
relay guards and schema migration alongside native engine selection. Through
`454ce72`, the same Docker platform passed 143 unit tests, four effective models,
all image builds, native image and packaged policy checks, full TypeScript/70
renderer tests, main isolation/Tor/recovery, storage/migration, cold/dry-run,
unfunded research comparison and the full 24-case browser content/relay matrix
plus ingress failure/recovery and staged MCP activation. New comparison and
renderer-command tests cover both engine paths. The first webapp run hit a
transient post-restart Tor DNS failure; positive image checks now retry only that
exact failure, while Tor-stopped denial stays unchanged. The complete rerun passed.
Fresh independent reviews accepted combined source `e28fbde` and that focused
fixture correction with no material findings or compelling simplifications.
The native follow-up and final combined review acceptance are recorded below.

On 2026-11-13, unchanged source `a94ff16` was copied to Debian 13 ARM64
(kernel 6.12.116), rootless Podman 5.4.2 with netavark/overlay, and
the official Docker Compose 5.1.4 binary. The provider works without a PATH
change when `PODMAN_COMPOSE_PROVIDER=$HOME/.docker/cli-plugins/docker-compose`
and `CONTAINER_ENGINE=podman` are exported. No provider patch was used.
The 143 unit tests, four models, compilation, all selected lean/Funnel/treasury
image builds, full storage/migration/locking suite, packaged image/tool-policy
and URL-reference checks, full TypeScript/70 UI tests, endpoint cancellation,
readiness/errors/restart, and complete main SSH/MCP/Tor outage/recovery suite
passed. Managed `make up` and ordinary `make down` passed with dummy inference
credentials and no wallet initialization. The dedicated Podman path suite passed
38/38, including non-isolated-client denial, positive probe controls, strict
network inspection and HAProxy's absent default route. The deployment was left
stopped, its generated state preserved, and leftover disposable fixture volumes
removed explicitly by their exact project labels.
A networkless signal-handler probe completed 12-second cleanup both
with the configured unlimited timeout and explicit Compose `--timeout -1`.
Podman's native inspection stores the configured timeout as unsigned maximum.

That initial qualification exposed an API limitation. Compose preserves
`bind.create_host_path:
false` in its effective model, but the compatibility API starts a container and
creates the missing source anyway. Native `podman run --mount` refuses it.
The operation-scoped host preflight now rejects missing required sources for
managed creation, including offline jobs and supported passthrough launches; raw
Compose still bypasses it and concurrent host deletion remains an upstream gap.
The original reliability defect had no demonstrated credential or network
boundary bypass. A subsequent side-by-side comparison with the checksum-verified
official [Compose 5.7.1](https://github.com/docker/compose/releases/tag/v5.7.1)
binary reproduced both missing-bind creation and inline-seccomp filename failure
on Podman 5.4.2. The installed provider was not replaced; upgrading Compose alone
does not fix either observed issue.

The subsequent qualification corrections address the fixture failures:

- Cold-launch health checks use a simple executable HTTP probe, avoiding API
  splitting of a multiword Python argument.
- Research's missing-scratch negative control explicitly mounts read-only
  scratch on both engines; it no longer depends on Podman's automatic tmpfs.
- The disposable TLS fixture directory is traversable by container UID 10000.
- Both relay and local-file PNG fixtures have valid chunk checksums.
- The CONNECT observer uses unbuffered HTTP input before transferring socket
  ownership to its raw tunnel loop. A controlled coalesced-write probe reproduced
  lost early tunnel bytes with the old buffered parser. Real TCP tests cover
  preserved bytes and forbidden-target refusal without an upstream connection.
- The simulated TLS bridge closes both sockets and cancels residual copying
  when either peer closes. A real loopback probe reproduced the original
  orphaned bridge; two TCP tests verify full byte delivery, closure from either
  side and visible upstream-connection refusal. No active-stream deadline was
  added. A fresh independent review accepted this lifecycle correction.
- Ownership cleanup uses a networkless helper with only the disposable bind,
  preserving the nonce check and scoped capabilities. It no longer recreates
  named application volumes through `setup`; storage asserts their absence.
  Both engines also removed the helper's inherited anonymous volume with `--rm`.

Fresh independent review accepted the initial six-file fixture correction.
The expanded 147-test unit suite/model/compile checks and complete cold-launch/
dry-run, image-canary, research-policy and storage suites passed on both engines.
Subsequent browser testing exposed a product portability defect: Linux WebKit renders attachment
HTML inline despite its disposition. Standalone HTTP probes reproduced this
without containers; the sandbox blocked scripts, while binary MIME delivery
restored downloads. The existing untrusted HTML/XHTML/SVG branch now serves
binary attachments with unchanged bytes, nosniff and sandbox policy, preserving
trusted-document, raster and media behavior in every mode. Fresh independent
design review accepted this narrow fix. Browser tests retain actual click and
new-tab plugin download requirements and compare plugin/relay clicked-download
bytes with the authenticated response. Direct relay navigation still requires
403 under its native same-origin Fetch Metadata guard. Full rebuilt-image
Docker browser qualification passed before the focused-matrix refactor; native
Podman completed the controlled matrix but failed the separate live Tor control.
The corrected qualification and final controlled-browser/cleanup results are
recorded below.
Browser assertions wait for the exact consent-mutation response rather than
polling potentially stale state. Extra-tab exercises follow content/media checks;
chat streaming is qualified separately for each ingress.
Logout checks use a fresh page in the same cleared cookie context, avoiding a
race with the old SPA's own redirect while retaining unauthorized API assertions.

Earlier live checks also encountered a three-second Tor DNS timeout, an unfunded treasury
Tor-check TLS EOF, and a plugin environment GitHub-wheel download timeout; the
treasury and plugin suites did not pass. No weaker transport was selected.
The VM's checkout umask produced a group-writable public SSH configuration;
setting `components/hermes/ssh-client.conf` to `0644` was required by OpenSSH
before the successful core rerun. Source content was unchanged during that
initial qualification. Host browser
prerequisites were installed separately. Executor desktop/browser use remains
explicitly refused with Podman; no inference, funds or live Funnel was tested.

Component-specific checks and limits are documented in the
[webapp](webapp.md#verification-and-current-limits),
[x402_treazury](x402_treazury.md#stop-and-test), and
[updates and plugins](updates-and-plugins.md) guides.

## Executor desktop qualification

The [architecture guide](architecture.md#executor-capability-requirements) records
OpenSSH capability-removal experiments and their exact failure reasons. The
three existing listener grants are demonstrated requirements for that tested
configuration, not desktop grants. Repeat the affected evidence when replacing
OpenSSH, its account model or privilege-separation setup; do not repeat this
investigation merely because another GUI package is added.

The optional desktop build uses Debian rather than Alpine. Run the packaged
policy checks with `python3 tests/desktop_tools_smoke.py`. Run
`make computer-use-test` to build the selected images and test real desktop
actions over SSH together with the existing Tor/forbidden-path checks.
`python3 tests/computer_use_smoke.py --desktop-only` runs the GUI portion
while diagnosing an affected failure. These fixtures use disposable state,
ephemeral Teep host ports, dummy credentials and no inference or payments.
Serialize them with other fixed-subnet tests and keep the normal stack down.

The desktop executor uses a checked-in Moby seccomp baseline from commit
`7b5ccfab2d6b4e0aa64c6cce401a2705788eafeb`, with one added allow rule for
`clone`, `setns`, and `unshare`. Source:
[default.json](https://github.com/moby/profiles/blob/7b5ccfab2d6b4e0aa64c6cce401a2705788eafeb/seccomp/default.json);
license: `components/executor/seccomp-LICENSE`. The profile is selected only for
the desktop variant by native Compose inheritance in `compose.executor.yaml`.
It retains the baseline's `clone3` ENOSYS behavior and does not allow io_uring.
Playwright's older published full profile was rejected because it changed those
unrelated syscall contracts. Reconcile the baseline with engine updates. Remove
the custom profile when a selected native engine policy permits the qualified
Chromium sandbox without weakening unrelated syscall restrictions.

Enabling user namespaces exposes additional kernel paths to executor code; it
must not grant control of the parent network namespace or bypass Tor. Verify
those forbidden paths and the actual Chromium sandbox layers, alongside runner
capabilities, SSH failure/restart behavior and persistent state. Podman and other
CPU targets require their own evidence; source/manifest inspection is insufficient.
The optional desktop implementation is complete for the qualified scope below.
The stack has only been runtime-qualified on ARM64; AMD64 qualification is not a
completion prerequisite. The pinned desktop image includes Linux AMD64 and ARM64,
Compose imposes no ARM64 restriction, and Chromium discovery retains its AMD64
paths alongside the added ARM64 path. This preserves the ability to qualify AMD64
without claiming that it has passed. The [rootless engine differences](architecture.md#rootless-podman)
explain why executor desktop/browser tools remain Docker-only; native operator
webapp/browser qualification is recorded separately above and below.

The image choice avoids a substantial download and disk footprint when desktop
tools are unused. On 2026-11-11, the pinned desktop index reported compressed
downloads of 1,192,327,731 bytes (ARM64) and 1,203,999,297 bytes (AMD64).
Local ARM64 unpacked images measured 229,682,455 bytes for lean,
4,380,500,982 bytes for the desktop base and 4,429,795,686 bytes for the adapted
desktop executor. Download and unpacked sizes are different measurements; these
local build observations do not establish AMD64 disk or runtime requirements.
Adding the isolated browser harness brought the local ARM64 adapted executor to
4,508,949,695 unpacked bytes; the desktop base and lean target are unchanged.

On 2026-11-11, Docker Desktop ARM64 (Engine 29.9.3) passed 92 unit tests,
effective base/Funnel models, compilation, 12 packaged tool-policy combinations,
lean and desktop SSH/network checks, UID-101 Tor routing/outage/recovery and
desktop capture/click/type/key/scroll. Focused checks also passed native idle
eligibility/stop, human takeover preservation, display restart, lost derived
publication repair, enabled-gateway/lean-executor dependency refusal, SSH outage
and restart, actual root-write rejection on the system/identity mounts, and
on/off/on preservation of SSH identity, workspace, Chromium localStorage and an
HTTP-only fixture cookie. These use no real accounts or funds.

The combined webapp run passed the existing 24 content cases (Chromium, Firefox,
WebKit; four modes; local and simulated HTTPS), plus Chromium screen capture/RFB
pixels on both ingress fixtures in all four modes. Screen checks exercised
wrong-origin, one-use and expired tickets, watch/stale-viewer input denial,
positive takeover input, stop/restart, native cookie-logout lifetimes and no
external HTTP requests from viewing. The existing logout test now observes its
browser response without awaiting a fetch across SPA navigation. DNS/preconnect,
stale consent, Tor retrieval and credential/ingress failure checks also passed.
The GUI tests cover one active default-profile screen and programmatic native
display transport; full visual interaction with the native noVNC pane and other
profile arrangements are not independently qualified. AMD64 and rootless Podman
remain unqualified. Simulated HTTPS does not prove live Funnel ingress, and these
checks do not establish provider attestation or funded settlement.

A fresh independent read-only review accepted combined revision
`4f003190e91358d9908dda87390f8254dbce2ee0` for the implemented and qualified
Docker Desktop ARM64 scope with no material findings. The computer-use plan was
completed after the operator clarified that untested architectures do not block
completion. Full visual noVNC-pane interaction and additional profile arrangements
remain outside the qualified scope; concurrent profile screens remain unsupported.

### Browser harness and results

Browser automation reuses this desktop substrate and adds the pinned harness in
an isolated executor environment. Run `make browser-use-test` for its focused
disposable placement, sessions, cancellation and result checks. Runtime browser
qualification passed remote stdlib/child execution, DOM/navigation/type/download,
named/unnamed tabs, concurrent startup, screenshot staging/native vision, native
selected-cache round-trip with the browser profile excluded, takeover denial,
active/startup cancellation, timeout/retry, daemon crash, owner death and actual
missing-harness refusal/recovery. These fixtures execute the tool as Hermes UID
10000, matching the gateway: root `docker exec` can create native install locks
owned by the wrong account and invalidate restart tests. The complete desktop/
network run also passed image switching and harness Tor outage/recovery. The
actual automation-launched Chromium's `chrome://sandbox` page reported namespace,
PID/network-namespace and seccomp-BPF sandbox layers enabled.
The implementation adds no capability, syscall rule,
published port or internal network grant. The existing three OpenSSH grants and
desktop-only Chromium user-namespace profile remain the owning requirements.

On 2026-11-12, the combined Docker Desktop ARM64 webapp regression passed the
existing 24 content cases across Chromium, Firefox and WebKit, eight screen
mode/ingress cases, and eight browser screenshot/download mode/ingress cases
plus initial authenticated result checks. Actual generated screenshots rendered,
executor downloads transferred, logout denied subsequent file requests, and the
viewing browser made no external requests. Restart, credential rotation, stale
consent, DNS/preconnect, ingress mismatch and Tor failure/recovery checks passed.
The profile archive exclusion also passed actual selected-cache round-trip
without socket/symlink extraction failures. The qualification remains limited to
the single default-profile desktop and tested engine/architecture above; AMD64,
rootless Podman and full visual noVNC-pane interaction remain unqualified.
CDP/dialog/vault tools remain excluded; raw CDP through executor Python does not
qualify their separate native routes.

A fresh independent read-only combined review accepted BU-1 and BU-FINAL at
`db84bcfb8ea879a51db5ab59c0ac6b1a244874b3` for this documented scope, with no
material findings. Final patch-context whitespace cleanup was checked against
the exact packaged source: all seven patches apply and produce identical source
bytes. The completed browser-use plan has been removed; its history remains in Git.

## Hermes v0.23.1 integration qualification

The upgrade review covered upstream
`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19..3b421578588243f920886e6fe79a6faa87ea026e`.
The official multiarch base index is
`sha256:276d44685c65c0cb2a25f190b63c65c8906f9dc76486fb1c05ae71b5826bda08`.
The downloaded ARM64 image's clean install stamp matched the selected commit;
its native renderer receipt and calculated source hash both matched
`d962149f7c279801f68eb629e8939592105e0d49ddb97d01a549b85748335717`.
All seven deployment patches remain necessary. Only the disabled-tool patch's
import context needed refreshing. The browser harness dependency closure,
screenshot helper and copied upstream session fixture are unchanged.

The principal integration changes are the upstream switch to pnpm builds,
native saved-gateway HTTP/WebSocket relays and SSH connections, threaded tool
availability probes, a new browser-vault inline dispatcher, and schema 53.
The [derived build](updates-and-plugins.md#derived-hermes-build-and-patch-maintenance)
uses upstream's pinned pnpm in its disposable frontend stage. Existing registry
and inline exclusions also cover the new vault dispatcher. Native availability
budgets remain upstream-owned. Saved connections retain authenticated operator
authority and the namespace's existing network grants; no firewall exceptions
were added. The relay cannot pass a remote trusted-page marker through its
header allowlist, so the existing global response policy makes relayed HTML/SVG
inert attachments. The content matrix now exercises that actual route with
hostile documents, a valid raster, anonymous requests and credential/header
canaries. Configuration qualification includes a populated schema-52 migration
and preservation of operator settings and SSH identities.

On 2026-11-12, Docker Desktop ARM64 (Engine 29.9.3) passed 92 unit tests,
effective base/Funnel Compose models, compilation, native image dispatch and
policy capture, 12 packaged tool-policy combinations, URL-context refusal,
full renderer TypeScript and 70 focused renderer tests. Runtime checks passed
configuration migration/repair/retry and native-volume locking; actual SSH
terminal/code execution; allowed and forbidden network paths; Tor outage and
restart; desktop actions, sandbox layers and on/off/on state preservation;
browser placement, cancellation, daemon/owner death and missing-harness recovery;
image retrieval canaries; and dependency-bearing native plugin install/update
and recreation persistence. The successful UID-101 public Tor probe now uses
the same existing retry helper as other allowed Tor probes; forbidden-path and
Tor-stopped assertions retain their original failure behavior.

The webapp passed 24 content/relay cases across Chromium, Firefox and WebKit,
four content modes and local/simulated HTTPS ingress, plus eight screen and
eight browser screenshot/download mode/ingress cases. Native auth, credential
rotation, gateway restart, terminal/file placement and viewer-request checks
also passed. Initial transient Tor/DNS failures were retried without changing
transport. One Firefox popup observation timed out; a diagnostic repeat and the
complete matrix passed the same deliberate-link assertion with read-only click
diagnostics. Existing single-profile, platform and visual-surface limitations
above still apply. These checks use dummy credentials and establish neither live
Funnel ingress, provider attestation nor funded settlement.

The complete webapp run also passed stale-consent revocation across restart and
policy changes, direct DNS/TCP/preconnect observation, gateway/ingress mismatch
refusal and repair, real Tor raster retrieval and outage/recovery, and staged
activation/reload/disconnection of twelve unfunded fixture MCP endpoints.

A fresh independent read-only review accepted U2/U-FINAL at
`594bc0c92f87cbe3694f54afbb64e82b63275a4c` with no material findings for the
documented Docker Desktop ARM64 scope. The completed upgrade plan was removed
after acceptance; Git history retains its baseline and review evidence.

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

The focused qualification workflow runs `python3 tests/bind_mount_smoke.py` on
each engine before the core and browser suites. It uses only networkless,
disposable project containers and public fixtures, proving missing required
sources are refused without directory/container/network creation while existing,
overridden and unrelated offline jobs remain usable. Run `make webapp-test` and
`make webapp-live-test` serially: the former concentrates UI/ingress boundaries,
the latter retains public Tor image/outage/recovery evidence. See the
[webapp test matrix](webapp.md) for retained cross-browser coverage.

Native Podman controlled browser assertions passed after the matrix reduction.
Teardown exposed a stopped profiled treasury container omitted by default Compose
`down`; Podman then refused its namespace owner's removal. Managed/wrapper down
and disposable teardown now include all profiles. The fixture helper reports
cleanup errors and fails otherwise successful tests while preserving an original
exception. A real stopped-profile/shared-namespace regression case is included in
`tests/launch_smoke.py`. Operator shutdown preserves volumes unless requested.


On 2026-11-13, corrections through `897f91a` passed qualification on
Docker Desktop ARM64 (Engine 29.9.3, Compose 5.7.0) and Debian 13 ARM64 rootless
Podman 5.4.2 (netavark/overlay, official Compose 5.1.4). The installed VM provider
was retained. Results on both engines include:

- Effective models/compilation, packaged-image checks, full TypeScript and 70 UI
  tests, and artifact-only builds under invalid disposable deployment settings.
- Cold/dry-run and profiled namespace cleanup; real SSH/Python placement,
  forbidden paths, selected MCP grants and Tor outage/recovery.
- Named-volume storage, locks, migration and cleanup; authenticated image/socket
  policy; editable research policy; endpoint errors/readiness/cancellation;
  context-reference and twelve desktop/browser policy combinations.
- Separate live authenticated Tor raster retrieval, exit-control and redirect
  counter evidence, outage/recovery; unfunded twelve-listener treasury/free API
  checks and catalog warming; native plugin install/update/dependency persistence.

All 159 unit tests, four effective models and compilation passed on both engines.
Final controlled three-browser content/ingress suites and cleanup passed on both,
including stale consent, policy mismatch, credential/ingress failures and staged
MCP activation. The corrected profiled-namespace cleanup has an actual-engine
regression test on both engines.
No blanket browser retries, increased browser deadlines, direct transport or
weaker TLS verification were added.

On 2026-11-13, a fresh independent final combined review accepted `1d46ce9`
against `main` `b46e050`, including corrections through `897f91a`, with no material
security or reliability findings. The reviewer traced engine selection/endpoint
normalization, network preparation, dry-run operands, bind checks, maintenance
and treasury consumers, shutdown, browser containment and qualification fixtures.
It independently passed 54 focused tests (8 bind, 42 engine, 2 TLS bridge and
2 CONNECT), passed `git diff --check`, and inspected the successful Docker and
native Podman qualification logs and matching VM checkout. Full runtime suites
were not repeated for the unchanged reviewed snapshot. G2 is accepted for the
qualified lean deployments on Docker Desktop ARM64 and Debian 13 ARM64 rootless
Podman. The completed plan was removed under the planning workflow; Git history
retains its design and review evidence.

Podman executor computer/browser tools remain refused because of seccomp profile
delivery; operator webapp/browser qualification is a separate capability. Live
Funnel, provider attestation, funded settlement and other platforms remain
unqualified. Existing Docker optional-executor evidence remains historical and
was not rerun for this host-helper/fixture correction.

Final self-review also reproduced a native dry-run parsing ambiguity:
`up --no-attach --dry-run -d SERVICE` launches for real because the apparent flag
is an option value. The wrapper now consumes value options before interpreting
flags; dry-run still validates supported creation commands, and service names are
forwarded after `--`. Unit tests exercise both engines' preparation/refusal, and
actual-engine probes verify missing-bind refusal plus genuine global dry-run
preservation with flag-like operands. This correction was included in the final
independent combined review.

The final resource audit found no current-run qualification containers, networks
or volumes on either engine. Two older Docker webapp fixture volumes dated
2026-11-09 were preserved; they predate this run and are absent from the current
model. Normal deployment state and unrelated resources were preserved.

Qualification does not extend to Linux Docker, AMD64, other distributions/kernels,
Compose 2.36–2.39 or arbitrary provider/engine combinations. Additional targets
need native allowed/forbidden-path and lifecycle evidence. Podman executor desktop
support first needs a qualified seccomp delivery mechanism that preserves the
required profile; neither native bind enforcement nor seccomp delivery was fixed
by upgrading the stock Compose provider.
