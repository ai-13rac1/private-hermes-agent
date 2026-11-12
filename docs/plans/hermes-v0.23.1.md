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

Implementation has not started. Docker access needs sandbox escalation; target
architecture, image metadata, patch applicability and new routes remain to be
checked. Qualification uses disposable projects, dummy credentials and no paid
inference, funded wallet operations or live Funnel enrollment. Existing AMD64,
rootless Podman and full visual noVNC limitations remain unless independently
qualified here.
