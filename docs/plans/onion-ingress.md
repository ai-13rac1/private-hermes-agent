# Optional onion-service ingress

Status: planned; implementation has not started. This task creates the plan only.
Follow the [planning workflow](../planning-workflow.md) and
[repository instructions](../../AGENTS.md) before execution.

Planning baseline: branch `main`, `e4bfd20e2fc29526e162cc42ec2d1c097049ca06`.
At execution, record the actual implementation baseline and reconcile intervening
changes. Preserve unrelated untracked files; they are outside this plan.

## Objective and current behavior

Add optional Tor v3 onion ingress to the authenticated Hermes webapp. It must
work with or without Tailscale Funnel, while localhost access continues
independently. Onion ingress is disabled by default and explicitly selected by
`TOR_ONION_ENABLED=false|true` in root `.env`.

Provide `make onion-address` to create a persistent onion identity if absent and
display its HTTP URL, or display the existing address. Creating an identity must
not publish it, start the stack, enroll Tailscale, require inference credentials,
or initialize wallets. Document this command and both remote ingress workflows
in a user-facing Ingress section of [README.md](../../README.md).

Today, `components/webapp/settings.py` renders separate localhost HTTP and
optional Funnel HTTPS frontends in HAProxy. The proxy strips forwarded headers,
sets the trusted scheme, checks exact Host authorities, and has a fixed Hermes
backend. Hermes trusts only proxy address `10.203.85.3`, with no fixed public URL.
Native cookies follow the trusted request scheme: HTTPS uses Secure, host-only
`__Host-` cookies; HTTP uses ordinary host-only cookies. Both retain HttpOnly and
SameSite=Lax. Native origin checks and WebSocket authentication remain in place.

The existing Tor service owns transparent egress and persistent bind state at
`data/tor/`, mounted at `/var/lib/tor`. Its firewall denies private destinations;
onion forwarding therefore needs an explicit exception. Its startup also creates
the treasury-only SOCKS Unix socket. Preserve that behavior when rendering an
additional optional hidden-service configuration.

Relevant pins at this baseline:

- Tor `dockurr/tor:0.4.9.16`, digest
  `5b5c9e5036fff91bdf021ef225fdb0fc9ba4222425b9cbc1858a15681d220590`.
- Hermes official v0.23.1 source
  `3b421578588243f920886e6fe79a6faa87ea026e`, matching the local reference checkout
  and the packaged source recorded in `components/hermes/Dockerfile`.
- PrivateOnyxApp reference `f147f06e500ffcadfd4ce2d1205076313d125743` demonstrates
  native HiddenServiceDir/HiddenServicePort and an isolated ingress gateway.
  Use it as reference, not governing design: reuse Hermes's existing HAProxy
  rather than adding its extra gateway, and retain exact-host enforcement rather
  than accepting every syntactically valid onion hostname.

## Chosen topology and boundaries

Use existing Tor and HAProxy processes. Add one always-present internal network,
`onion-ingress`, provisionally `10.203.86.0/24`, with Tor at `10.203.86.2` and
HAProxy at `10.203.86.3`. This subnet is unused in the inspected baseline; include
it in preflight overlap checks and the documented address pools.

```text
localhost HTTP ----------------------+
Funnel HTTPS (independently optional) +--> HAProxy --> Hermes
onion HTTP --> existing Tor ----------+
```

The `.env` flag changes publication, listener and firewall behavior, not network
membership or Compose file selection. Add the network to base Compose and its
`isolate: strict` counterpart to the existing Podman overlay. Keep Funnel's
existing conditional overlays. There is no onion runtime overlay, additional
Tor daemon, proxy relay, public port publication, or ingress access for the
executor. A networkless maintenance invocation of the existing network image
may own offline identity creation/inspection; it is not a new running service.

When enabled, native Tor maps onion port 80 to `10.203.86.3:8080`. HAProxy listens
only on that address/port, accepts only Tor's exact source address, and allows
only the saved hostname and its explicit `:80` authority. Reserve the listener
port against local-publication conflicts when enabled, including Podman's
wildcard local frontend. Exclude the new interface from the proxy's discovery
of its single host-publication interface.

Tor receives one new outbound TCP exception to that exact proxy destination and
port, before private/connected-network denial. HAProxy receives the matching
inbound exception. Do not grant Tor general backend access or grant the proxy
new outbound initiation paths. Existing established-reply rules suffice for
responses. When disabled, omit HiddenService configuration, the HAProxy onion
frontend, and both new-connection grants; leave the network and keys intact.

Onion requests preserve their Host and report `X-Forwarded-Proto: http`, with
the same forwarded-header stripping, peer attribution and content-policy header
handling as other frontends. Localhost continues to report HTTP; Funnel continues
to report HTTPS and emit Secure cookies. Do not spoof HTTPS for onion requests
or add global cookie rewriting. Independent browser logins use the same native
credentials and signing key; no shared browser session or origin-wide logout
guarantee is required. This is not cryptographic audience separation of bearer
tokens; preserve native rotation semantics across all ingress paths.

Preserve agent/executor mounts and namespaces, default-deny Tor egress, Teep's
accepted direct uplink, treasury-only SOCKS access, and the proxy privilege drop.
Never mount Tor keys into Hermes, HAProxy, Tailscale, or the executor. The
authenticated browser operator still has administrative agent authority.
Deployment external-content policy and exact browser-origin consent remain in
force on the new origin. Onion ingress does not change content-fetching policy
or make browser-native content safe in an arbitrary non-Tor browser.

## Persistent identity and operator workflow

Use native Tor files in `data/tor/onion-service/`, including `hostname`,
`hs_ed25519_secret_key` and `hs_ed25519_public_key`. This is the only identity
store: no duplicate key, hostname `.env` input, completion marker, or lifecycle
journal. The secret identity is authoritative; `hostname` and public material
are derived. Keep Tor ownership UID 101/GID 102 and restrictive native modes;
do not loosen them for host-side display.

Proposed workflow, to be documented with the implementation:

1. Run `make init` and build the network image as needed. With an existing
   deployment, use `make down` before first identity creation or recovery.
2. Run `make onion-address`. It prints `http://<saved-address>.onion` and succeeds
   again without changing the identity. It works while onion ingress is disabled.
3. Set `TOR_ONION_ENABLED=true` in `.env`, then run `make up`. Read the address
   with the same target and log in through Tor Browser. Funnel may remain off
   or be independently enabled.
4. Set the option to false and apply the documented down/up workflow to withdraw
   publication. Localhost and independently enabled Funnel continue to work.
   Ordinary down, disable/re-enable and image rebuilds preserve the identity.

`make onion-address` must inspect an existing address without starting Tor,
building images or validating unrelated serving/provider/treasury settings.
Use the selected engine's existing maintenance path and a read-only Tor-state
mount for inspection when host permissions prevent direct access. Missing local
images/engine access get explicit errors; inspection does not pull implicitly.
Creation may build only the owning network image if needed, and prepare only
the required Tor bind path. Explain build network access separately from offline
key generation. Keep the entire root `.env` out of container environments.

For a missing identity, use native Tor with networking disabled in a
`network_mode: none`, no-dependencies maintenance job mounting only Tor state.
Prefer a small helper in the existing network component and host Make workflow.
Serialize mutation with the existing operator operation lock and refuse identity
creation/repair while the runtime Tor service is running; do not rely solely on
fresh bind-filesystem locks. Existing-address inspection remains available with
the runtime running. Never start a second writer to live Tor state.

Before implementation, confirm on the pinned Tor image that native offline
startup creates the hidden-service identity and can reconstruct missing derived
files from an intact secret key. Observe native completion/error and stop the
temporary process cleanly; do not wait for public bootstrap or invent an
operational failure deadline. If this contract fails, revise this narrow design
and independently review it before implementation; do not add a crypto library
or alternative daemon speculatively.

Interrupted creation must preserve any saved secret and let native Tor finish
derived files on retry. A lone hostname/public file without its secret cannot
authorize generation of a replacement identity: report the missing material
and backup recovery requirement. Corrupt/unrecoverable secret material fails
visibly without deletion or rotation. Do not introduce a rotation command in
this scope. Do not require a full set of derived files simply to inspect a
saved address; distinguish displaying saved information from readiness to serve.

An enabled managed startup requires the saved identity/address before proxy
rendering, with an actionable `make onion-address` error if missing. It must not
silently initialize or rotate keys as a rendering side effect. `make init` stays
networkless on the host; document the address prerequisite when enabling before
initialization. Read only the public hostname through a scoped maintenance
helper for rendering; the generated proxy configuration contains no Tor secrets.
Validate that saved value as one canonical v3 onion hostname before embedding it
in HAProxy configuration; reject extra lines, tokens or malformed authorities.
Before enabled runtime Tor starts, its owning component must reject orphan
hostname/public files without the secret rather than let native Tor replace the
identity. The scoped startup check reports readiness without exporting the key;
saved-address inspection remains permissive and does not claim readiness.
With onion disabled, missing onion files do not block ordinary startup. Saved
address inspection, credential repair, backup and shutdown stay available under
unrelated invalid settings. Maintenance normalization must explicitly disable
onion publication just as it disables Funnel.

Include all of `data/tor/` in backups and restore ownership/modes. The hostname
alone cannot recover an address; possession of the secret permits impersonation.
No private identity material belongs in Git, build contexts, command output or
qualification evidence.

## Implementation phases and review gates

### OI-DESIGN: validate the native contract and approve the design

- Recheck the baseline, owning Tor configuration/identity behavior, relevant
  engine guidance and consumers before implementation. Use only disposable
  networkless state for the focused native key-generation/recovery experiment.
- Finalize the helper invocation, address-reading path, port/subnet reservations
  and startup ordering. Keep native persistence and small explicit code; avoid
  new state machines, generic configuration layers or native-accounting checks.
- Obtain a fresh independent read-only design review of this plan and the
  exact baseline, including scoped maintenance, retry paths and both firewalls.
  The reviewer must not author changes or rerun supplied successful tests.
  Planning review alone does not prove the native contract or pass this gate.
- Commit the plan and any reviewed revisions before substantive implementation.

### OI-1: complete ingress, address workflow and permanent documentation

- Add the default-off option to `.env.example`, effective `x-deployment` settings
  and explicit Tor/proxy environment mappings. Reject malformed activation
  values for serving without blocking offline inspection and shutdown.
- Implement the identity Make target/helper, Tor rendering, fixed base network,
  Podman network declaration, scoped firewall rules and exact-host frontend.
  Trace `scripts/init-config.py`, `scripts/deployment.py`, `scripts/stack.py`,
  maintenance classification/bind checks, preflight and fixture consumers.
- Keep the existing treasury SOCKS configuration and ingress policy consistent
  through startup, disabling, restarts and configuration regeneration. Ensure
  changes take effect on Tor as well as the forcibly recreated web proxy.
- Extend focused qualification fixtures and checks described below. Update
  maintained documentation alongside the behavior, not after review.
- Commit coherent passing work; independently review the phase and combined
  change at OI-FINAL. Split further only if concrete work warrants another
  meaningful security boundary review, not an arbitrary number of gates.

README Ingress documentation must give usable localhost, Funnel and onion
instructions: enable flags, address creation/display, Tor Browser use, separate
logins, disable/re-enable and combinations. Include Funnel's missing first-use
setup: legitimate enrollment key, tailnet Funnel permission, exact assigned
`.ts.net` hostname, supported HTTPS ports, build/start and key removal after
enrollment. Explain that Funnel is public HTTPS, not tailnet authorization.
Link to [webapp operations](../webapp.md) for detail; keep maintainer machinery
and qualification out of README.

Update [webapp](../webapp.md) for origin/cookie behavior and diagnosis,
[configuration/backups](../configuration.md) for option ownership and identity
recovery, [architecture](../architecture.md) for the fixed network and exact
grants, and [development](../development.md) for checks and coverage limits.
Update the update guide only if component-build instructions change.

Reconcile [interactive-content part 2](webapp-interactive-content.md) to include
the independent onion browser origin when extending consent, frames and media.
It remains deferred and is not a prerequisite for this ingress. The
[read-only configuration plan](readonly-configuration.md) must retain the
trusted-proxy/native-auth settings and distinguish generated ingress configuration
from protected agent policy; this plan does not execute its proposed changes.

## Qualification and final acceptance

Use shared disposable fixtures with actual production entrypoints on Docker and
rootless Podman; serialize fixed networks. Never use operator Tor keys, wallets,
auth files, enrollment, or deployment state. Cover:

- Effective base/Funnel models on both engines for all four onion/Funnel flag
  combinations. Onion membership is fixed; runtime grants/listeners and native
  publication follow the flag. Include network overlap and listener-port conflicts.
- Fresh offline creation, repeated invocation, interruption after secret creation,
  missing derived files, unrecoverable keys, native modes, and identity retention
  through disable/re-enable, image/config changes, container recreation and
  disposable backup/restore. Prove no network/publication or unrelated setup
  during creation and no writes/builds during existing-address inspection.
- Malformed/unrelated settings, absent required files and active Tor writer
  cases: targeted useful errors, saved information remains readable, unrelated
  repair/shutdown works, no identity replacement or secret output.
- Native Hermes login, token refresh, logout, independent origins, and unchanged
  local/Funnel cookie attributes. Test the onion HTTP origin in actual Tor
  Browser before claiming browser compatibility; simulated HTTP or a Chromium
  hostname mapping alone does not prove that. Use ordinary onion cookies and
  confirm no shared login is required. Reuse unaffected browser-content evidence;
  add focused exact-origin consent separation and content-policy checks.
- On each engine, actual Tor-to-proxy success and denial of other sources,
  alternate ports/hosts and arbitrary onion authorities. Reject forged Origin,
  Host and forwarding headers; retain WebSockets, streaming and fixed backend.
  Confirm agent/executor cannot reach the new ingress or read its keys; the proxy
  cannot initiate to Tor, host/VM/private/Internet targets or other stack services.
  Tor's new exception must not allow agent/executor private egress through Tor.
- Dependency outage and recovery: Tor-only restart and proxy restart/recreation,
  withdrawal on disable, persisted identity, continued localhost/Funnel access
  during Tor outage where otherwise ready, and unchanged fail-closed agent
  egress. Do not independently recreate shared namespace owners to claim recovery.

Reuse `make check`, focused webapp/policy/engine and initialization checks,
`make webapp-test` and affected routing checks. Extend existing disposable fixture
mount overrides so new maintenance jobs cannot touch real `data/tor/`. Run only
affected broader suites; no payments, live provider inference or attestation
claim is needed.

A live end-to-end onion reachability check requires a disposable hidden service
and separate Tor client; static HiddenService config and direct frontend tests
do not prove descriptor publication or rendezvous. Creating the plan authorizes
no publication. Before such a future check, establish task authorization for
publishing the disposable authenticated service and accessing it over Tor. Keep
live Funnel enrollment separate and unnecessary for the simulated HTTPS checks.
Record actual Tor Browser/engine/platform versions and unavailable live coverage
as limitations, rather than silently substituting fixture results.

Gate OI-FINAL is a fresh independent read-only review of the accumulated change,
maintained docs, focused evidence and material finding dispositions. It can also
serve as the OI-1 phase review. Resolve material findings before acceptance;
do not rerun unchanged suites solely for review. Transfer lasting evidence and
limits to maintained guides, resolve inbound links and remove this plan only
after final acceptance under the planning workflow.

## Deferrals and evidence status

No shared sessions/SSO, distinct origin credentials, token audience redesign,
onion HTTPS certificates, onion client authorization, vanity keys, automatic
rotation, discovery UI, Onion-Location advertising, new egress mode or
browser-native interactive-content work. No implementation or public deployment
is authorized by this planning-only task.

- Planning source inspection: complete against the baseline above.
- Plan validation: local-link targets and staged `git diff --check` passed;
  no runtime checks are needed for this documentation-only task.
- Independent planning review: fresh read-only review accepted the approach
  against the planning baseline with no material findings. Incorporated its
  clarifications on pre-start orphan-key refusal and canonical hostname
  validation. No suites or native experiments were run by the reviewer.
- OI-DESIGN native experiment and design acceptance: pending.
- Implementation, both-engine runtime qualification and OI-FINAL: not started.
