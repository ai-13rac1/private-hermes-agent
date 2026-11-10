# Editable x402_treazury deployment configuration

Status: complete. P1 implemented, validated and independently reviewed.
The later [operation-scoped state corrections](operation-scoped-state.md) supersede
this plan's build/coordinator eligibility binding and inspection-time serving
policy checks; preparation history now survives unrelated updates, and offline
inspection is separate from runtime policy validation.
[Maintenance rule conformance](maintenance-rule-conformance.md) further separates
artifact building from explicit policy seeding; historical build-time seeding
evidence below describes its recorded revision.
Independent read-only design review of `66c641b` found no material blockers;
its recommendations on validation, safe seeding and rename ordering are adopted.
Baseline: branch `webapp-private-content`, commit `80d267f6e177d18f39dd59ee56cb33d9f9d14e54`.

## Intent and approach

Expose the packaged research policy as `config/x402_treazury/research_desk.toml`
for operator edits before treasury initialization and after deployment. Currently
it lives only in the image and all configuration changes invalidate the wrapper's
preparation gate. The pinned upstream `424f36a814711d542fbff27f139842c9d08d5b76`
already handles new wallet funding and catalog discovery during serving, and its
offline `wallet rename OLD NEW` preserves saved group identity.

Seed a missing file from the built image using a small offline extraction helper,
after `make build` and before managed startup/treasury commands. Preserve existing
files and modes on retries. Mount the directory read-only at the image's existing
deployment directory in serving, setup and admin containers, preserving relative
provider paths and host atomic edits. No new service, setting or state record.
`make init` alone cannot extract a default before the image exists.

Stop binding preparation eligibility to the entire effective configuration.
Retain the initial explicit preparation requirement, treasury identity and build/
coordinator binding. Validate the fixed Tor socket, treasury/key paths and twelve
loopback authenticated listeners on managed inspection/preparation/serving; policy,
wallet names, source/tool selections and payment settings remain operator-editable.
Do not widen executor access or expose wallet/config mounts to Hermes. No hot reload:
stop serving gracefully, edit/rename, then use `make up`. Initial preparation and
operator edits retain native financial authority; no funded operation is part of
implementation/qualification.

## Phase P1: implement, document and qualify

- Update the extraction, Compose consumers and configuration-independent gate.
- Document initialization timing, edit/restart steps, native offline rename and
  preview commands, preserved deployment fields and backup coverage.
- Extend focused tests for missing/existing config, policy edits, malformed or
  forbidden settings, unchanged identity/completion requirements and mount scope.
- Validate effective Compose models and use disposable real-image containers for
  read-only mounting, atomic edit visibility, config loading, forbidden policy
  rejection, wallet rename and restart behavior, with no payments or live ingress.
- Update this plan with checks and limitations; commit coherent completed work.

Independent design review precedes implementation. A fresh independent final review
covers P1 and the combined change, including host/controller and failure paths.
Runtime checks require Docker access; disclose unavailable evidence. Existing
read-only Hermes configuration work remains deferred in `readonly-configuration.md`;
this change concerns treasury policy only. Browser-content plans are unaffected.

## Qualification evidence

P1 implementation includes atomic missing-file extraction from the built image,
three read-only directory mounts, policy-independent initial completion and
explicit fixed deployment checks. Operating guides cover startup timing,
stop/edit/start, rename-before-new-name-startup, preview and backup scope.

- `make check`: 55 unit tests, base/Funnel effective Compose models and Python
  compilation passed.
- `docker compose --profile x402_treazury build x402_treazury`: passed, pinned
  upstream binary/build layers reused and new wrapper packaged.
- `python3 tests/research_config_smoke.py`: passed with actual image, networkless
  containers and a disposable unfunded wallet. Host atomic replacement/restart,
  relative providers, read-only writes, malformed/missing/forbidden settings,
  changed wallet policy and existing-file preservation were exercised.
- `python3 scripts/preflight.py private-hermes-x402-treazury-test` followed by
  `python3 -u tests/x402_treazury_smoke.py`: passed all twelve authenticated MCP
  listeners, free real API through Tor, executor wallet/secrets/network/RPC denial,
  persisted catalog/cache, and stopped-Tor denial with local inference retained.
- Changed-guide local file links and `git diff --check`: passed.

The offline policy test uses a controlled historical completion marker; it does
not establish successful financial bootstrap or catalog readiness for new policy.
Native rename is exercised through its missing-source error path; positive rename
semantics were inspected in the exact pinned source and guide, not qualified on a
funded group. No payments, funded operations, live ingress or provider attestation
were performed. A fresh independent read-only final review covered the combined
P1 snapshot, including the extraction pull policy, native rename contract and all
consumers; it found no material issues. The host operator TOML was initialized
from the rebuilt image without starting services or mounting private wallet state.
The implementation is complete; live financial qualification remains outside scope.
