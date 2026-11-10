# Maintenance and initialization rule conformance

Status: proposed; independent design review pending.
Baseline: branch `webapp-private-content`, commit `48a0f9b3584ff2368de4f5af60832b957eb7e3e5`.

## Intent and current defects

Address the independent audit's three confirmed findings and lower-priority duplicate
completion enforcement: invalid inference publication blocks shutdown; inspection and
repair run unrelated configuration/path checks; default-file creation can strand
partial final files; native successful bootstrap/warming is checked again through
report presentation fields. The user requests final review to treat other discovered
rule violations as valid findings, not dismiss them because outside the narrow diff.

Preserve native state/credentials, all network/isolation and authentication boundaries,
initial explicit financial preparation and twelve-endpoint activation. No live funding,
paid calls, private-state modification, Funnel enrollment or publishing is authorized.
The treasury source remains `424f36a814711d542fbff27f139842c9d08d5b76`.

## Simplest approach

- Centralize process-local inert interpolation values for maintenance only, including
  Teep publication/command fields. Shutdown uses both Compose files without Settings
  validation so it can stop existing Funnel resources. Inspection/control of existing
  containers and explicit offline maintenance jobs bypass unrelated Settings checks;
  normal launch/build/config validation retains actual operator settings. Keep command
  dispatch small and explicit; do not build a generic CLI parser/adapter registry.
- Plugins/update checks operate on the existing Hermes container without validating
  unrelated ingress settings. Credential creation/rotation needs no deployment settings;
  remove Make prerequisites that run full init before deliberate credential repair.
- Separate saved-wallet inspection from policy-aware admin mounts using a networkless
  `x402_treazury-inspect` Compose maintenance job with the same image/UID/wallet volume,
  but no serving-config bind. Compose cannot omit an unused required bind per action;
  a small explicit job avoids conditional mount overrides and temporary fake config.
  Status and repeated init do not seed configuration, prepare other storage or invoke
  trusted setup. New-wallet creation alone prepares Tor/network host inputs and the
  research policy, then runs the existing Tor-routed native creation job. Native Docker
  volumes retain image ownership; native wallet code owns its storage requirements.
- Give native Hermes configuration repair a minimal networkless `hermes-config` job
  (same Hermes image, unprivileged UID, profile volume only). Replace `setup config`
  and its consumers directly. This prevents unrelated data/auth/wallet mounts from
  blocking repair without adding privilege or a separate image. Trusted setup still
  owns normal provisioning and filesystem qualification, not ordinary read-only access.
- Scope wallet host initialization to actual new-wallet Tor/network inputs. Keep the
  shared deployment operation lock at a fixed ignored project-root path rather than
  underneath a component configuration directory that shutdown does not require.
- Publish missing defaults with one small helper: read source before creating a final
  name, write/fsync/chmod (and chown where required) a same-directory temporary file,
  then hard-link without replacement and remove the temporary name. Existing operator
  files and modes remain untouched, including a concurrent winner. No journal or state
  machine; retries simply see a complete file or no file. Apply to .env, allowlist and
  initial Hermes defaults; retain the existing atomic update path for established config.
- Trust native command success for bootstrap/catalog completion. Keep JSON parsing for
  requested structured diagnostics, but remove schema/completion/source-set presentation
  gates already owned by the pinned native command. Preserve actual deployment-policy
  validation, errors, saved treasury identity and only record completed successful phases.

## Phase P1: implementation and acceptance

Independent design review before implementation. Update direct consumers, operating
and development guides, affected prior plan claims and focused tests together. Validate
shutdown/maintenance with bad unrelated settings, saved-wallet status with bad network,
executor/Tailscale and research-config paths, repeated init preserving identity, normal
launch refusing unsafe settings, and repair jobs' actual effective mounts/permissions.
Inject source-read/write/publication failures and concurrent destination creation to
prove absent-or-complete defaults, preserved modes/owners and safe retries. Show native
successful report presentation changes do not revoke completion; native failure still
stops subsequent phases. Use existing disposable networkless wallet/research fixtures
and storage qualification for actual images, repaired profile defaults and native CLI.
No funded bootstrap/warming is run; their native completion contracts are inspected at
the exact pin and wrapper behavior tested with controlled results. Reuse prior endpoint,
browser and network evidence for unchanged paths rather than repeat broad matrices.

Commit coherent passing work, obtain fresh read-only final combined/P1 review, resolve
material findings and record validation/limitations here. The final review brief must
explicitly invite other rule violations noticed across affected/unchanged consumers.
No blanket new quotas, timeouts, fallback policy, extra persistent records or recovery
frameworks. New Compose jobs are explicit invocations, not long-running services.
