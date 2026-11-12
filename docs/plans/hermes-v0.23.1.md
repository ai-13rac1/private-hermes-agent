# Hermes v0.23.1 integration qualification

Baseline: `3161614ad6936e994b8e0ddd278ba1ad953a3c50`, branch
`hermes_v0.23.1`. Upstream review range:
`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19..3b421578588243f920886e6fe79a6faa87ea026e`.

## Intent and approach

Update the official Hermes image and its source/build checks to v0.23.1.
Review the actual upstream range and packaged inputs before rebasing the seven
explicit patches. Preserve Tor-only public egress, exact internal grants, SSH
executor placement, early deployment-owned WEBAPP_EXTERNAL_CONTENT and
COMPUTER_USE_ENABLED policies, authenticated browser containment, native
configuration application and persistent operator state. No new service,
configuration framework, compatibility reader or trust boundary is proposed.

The reference checkout is read-only. Resolve the official image digest and
verify its clean source stamp, renderer receipt and browser dependency closure;
these are not established merely by the checked-out tag. Review newly added
network/browser/configuration routes as well as changed patch targets.

## Phases and acceptance

- U1: Independent read-only design/upstream hazard review before substantive
  implementation. Identify concrete major integration risks and map them to
  focused existing checks or necessary additions. Inspect relevant maintained
  guides and deferred plans for conflicting shared interfaces.
- U2: Update pins, source/hash checks, explicit patches and affected consumers.
  Build the actual derived Hermes and executor images. Qualify native dispatch,
  configuration/setup preservation, policy capture and registration, patched
  renderer, authenticated content, SSH execution/browser/desktop placement and
  allowed/forbidden network paths including outage/recovery. Serialize fixed
  subnet fixtures. Reuse existing focused suites; upstream feature completeness
  is outside scope. Document precise checks and unavailable coverage.
- U-FINAL: Fresh independent read-only review of the resulting combined commit,
  relevant unchanged contracts and qualification evidence. Resolve material
  findings, update maintained guides and affected plans, then remove this plan
  after acceptance. Local commits only; no publishing or private-state changes.

## Evidence and unresolved items

U1 accepted by fresh read-only reviewer at baseline plus plan commit `bce23dc`.
Review identified native saved-gateway relay routes, new browser_vault inline
dispatch, threaded native availability checks and schema 52->53 migration.
The existing global response policy and registry/inline exclusions cover the
new routes structurally; focused actual relay coverage and populated-schema
migration coverage have been added to existing fixtures.

The official multiarch index is
`sha256:276d44685c65c0cb2a25f190b63c65c8906f9dc76486fb1c05ae71b5826bda08`.
Downloaded ARM64 source stamp is clean at the intended commit; native receipt
and calculated renderer source hash both equal
`d962149f7c279801f68eb629e8939592105e0d49ddb97d01a549b85748335717`.
Browser lock closure and screenshot helper are unchanged. All seven patches
apply after refreshing one import context. Upstream switched frontend builds
to pnpm and excludes it from runtime images; the derived frontend stage now
uses the identical upstream PM hash-verified pnpm installation recipe.

`make check` passed 92 unit tests, effective base/Funnel models and compilation.
Native dispatch/mode capture, 12 packaged tool-policy combinations, URL-context
checks, full renderer TypeScript and 70 focused UI tests passed. Storage/setup
qualification passed, including populated schema-52 migration, CLI repair,
identity preservation and native volume locking. Desktop/network qualification
is running. Image fixture startup collided with the active network fixture;
no image assertions ran, and that fixture will be rerun serially.
Remaining runtime qualification and final review are pending. Target is Docker Desktop
ARM64, Engine 29.9.3. Fixtures use disposable projects, dummy credentials and no
paid inference, funded wallet operations or live Funnel enrollment. Existing
AMD64, rootless Podman and full visual noVNC limitations remain.

Desktop actions, sandbox/user-namespace restrictions, native idle/display repair,
on/off/on state preservation and missing desktop/SSH refusal/recovery passed.
The subsequent UID-101 public Tor probe hit its three-second connection timeout;
that successful-path probe now reuses the existing `eventually` helper, like
other allowed Tor probes. The network/outage portion is rerunning without
repeating the already-passed desktop actions/switching checks. Forbidden and
Tor-stopped assertions retain their original failure behavior.

The focused network rerun passed UID-101 Tor routing, allowed/forbidden paths,
Tor outage and restart, and browser-harness outage/recovery. Serial image
retrieval qualification passed. Browser lifecycle qualification passed actual
missing-harness refusal/recovery in addition to placement, native cache sync,
concurrency, cancellation, daemon crash and owner death. The final static check
again passed 92 tests, Compose models and compilation after test changes.
Plugin and webapp matrices are pending; final review must consider that evidence
before accepting U2/U-FINAL.
