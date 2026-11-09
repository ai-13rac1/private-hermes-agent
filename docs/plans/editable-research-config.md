# Editable x402_treazury deployment configuration

Status: design review pending.
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
