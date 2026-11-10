# Maintenance and initialization rule conformance

Status: initial P1 fixes committed as `085230c` and qualified. Final combined
review found three further P2 operation-scoping defects; corrections below are
in progress. Initial independent design review of `fad9ab2` found no material findings.
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
- Treasury operations validate their actual mounted policy and existing Hermes
  availability, without full Make init or unrelated ingress validation.
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
- Trust native command success for bootstrap/catalog completion. Stream native output
  as diagnostics without parsing it to authorize completion; remove presentation gates
  already owned by the native command. JSON parsing remains only where an actual read
  interface needs its data. Preserve actual deployment-policy validation, errors, saved
  treasury identity and only record completed successful phases.

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

## P1 qualification

- `make check`: 86 unit tests, effective base/Funnel Compose validation and Python
  compilation passed. Synthetic bad ingress/Teep settings cannot block shutdown,
  logs, existing-container commands or documented offline repair/backup jobs; actual
  launch retains its policy gate, and raw model inspection retains actual settings.
- Host default publication tests inject source-read/fsync/link failures and a concurrent
  operator-file winner. No partial final file is left, retry publishes complete data,
  and existing content/modes remain intact. Credential repair needs no deployment settings.
- Treasury image rebuilt from the unchanged native pin. Packaged Hermes profile path
  ownership is UID/GID 10000, so the unprivileged job needs no root initialization shim.
- `tests/research_config_smoke.py`: passed with disposable unfunded state. Actual Make
  status/repeated init kept the same address/identity/history despite invalid ingress,
  credentials, network allowlist, executor/Tailscale paths, and wrong-type research
  configuration directory. No unrelated paths were initialized and no services started.
- `tests/storage_smoke.py`: passed. Real setup's injected initial default-publication
  failure left no final config, and retry succeeded. Native config repair and wallet
  inspection worked after failed setup. New jobs ran as their unprivileged UIDs with
  zero effective capabilities, only their required native volume, no unrelated private
  paths, and no internal Teep connection. SSH identity, native lock exclusion and
  persistence through ordinary Compose down/recreation remained qualified.
- Controlled native results prove successful presentation changes do not veto phase
  completion; native failure still stops later phases. Exact pinned bootstrap/warming
  Result propagation and native completeness guarantees were independently inspected
  during design review. No funded bootstrap/warming was executed.
- Prior endpoint/browser/network qualification is carried forward for unchanged paths;
  no broad test matrix or success cache was added. No new image/dependency/fork, journal,
  financial ledger, timeout or transport fallback was introduced. The two additional
  Compose jobs are explicit same-image maintenance invocations with distinct mounts.

All checks used public source and disposable projects, not operator wallet/profile
state. Local link and diff checks accompany the final evidence update. The final
review is explicitly asked to assess other rule violations it notices, not only
regressions in this diff; material findings must be resolved before completion.

## Final-review corrections

The fresh final reviewer was explicitly asked to report other rule violations and
found three valid P2 cases: `setup mcp` still requires webapp/wallet mounts;
documented full storage repair still validates unrelated settings; and image build
still runs initialization/check/settings gates. Final approval is pending correction.
The earlier proposal to retain build validation was wrong for an artifact-only build.

- Add a same-image trusted networkless `mcp-config` job for token/connect, with
  Hermes profile, bind-data parent for its auth directory, and required public code;
  no webapp credentials or wallet volume. Only the actual auth directory is prepared
  by registration code; unrelated bind-data leaves are neither validated nor used.
  Disconnect uses the existing unprivileged profile-only `hermes-config` job with
  its entrypoint set to Python and the required public component code mounted read-only.
  This avoids an unused auth mount blocking disconnect, an additional disconnect
  service, or conditional fake config/secret mounts. Preserve root helper authority
  for cross-UID token publication, and native UID 10000 for profile-only removal.
- Add a declarative `setup-storage` job using the existing trusted setup image/code
  and actual storage mounts, excluding webapp auth. Its purpose is explicit full
  storage qualification, so actual invalid storage paths still fail. Replace the
  documented repair command directly and include both new jobs in narrow maintenance
  dispatch. No legacy aliases or general command-routing framework.
- Make both Make/stack build artifact-only: no init, whole-deployment check, Settings
  validation or post-build policy publication. Use inert unused serving interpolation
  while retaining actual pinned build inputs. Launch continues to validate actual
  settings. Add explicit `make x402_treazury-config` policy seeding via the existing
  treasury helper/extractor; startup/new-wallet creation still seed if needed.
  Update every affected operating/build workflow rather than hide state writes in build.

Independently review the revised MCP mount/authority approach before implementation.
Qualify root token publication and unprivileged disconnect, including missing unrelated
webapp/auth paths, plus offline full storage repair and artifact dispatch under bad
settings. Reuse still-valid atomic/default and wallet fixture evidence; rerun affected
checks only. A fresh final reviewer will assess the corrected combined state and any
other rules it notices, as the user requested. No financial/live state is involved.
