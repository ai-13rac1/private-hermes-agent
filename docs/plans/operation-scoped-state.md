# Operation-scoped validation and persistent state

Status: proposed; implementation pending design review.
Baseline: branch `webapp-private-content`, commit `5b29ec666804235d912fd1cc6e09746b6b5540da`.

## Intent and boundaries

Correct the five audited defects: implementation fingerprints invalidate treasury
preparation; webapp/Funnel validation blocks offline wallet commands; serving
policy validation blocks saved-wallet inspection; interrupted credential writes
can strand the saved password; missing SSH public sidecars block initialization.
The user explicitly requests generalized AGENTS.md rules and simple recovery,
without journals, recovery frameworks, additional services or persistent records.

Keep initial explicit financial preparation, treasury identity binding, native
wallet validation, exclusive ownership for writers, Tor/SSH/Teep/MCP boundaries,
authentication and browser policy enforcement. No private-state modification,
payments, public ingress enrollment or publishing is authorized by this work.
The pinned treasury remains `424f36a814711d542fbff27f139842c9d08d5b76`.

## Approach

- Remove source/build fingerprint eligibility and its stored fields. Retain the
  current preparation record schema, treasury identity and successful phase list.
  Native serving reconciles policy and cache changes. Build/patch verification is
  unchanged. No compatibility reader or replacement version gate.
- Separate reading wallet/preparation state from runtime deployment validation.
  Offline status uses the fixed wallet paths and native explicit state/key CLI
  arguments without loading unrelated serving configuration. Inspection reports
  wallet validity separately from readiness to serve. Networked initialization,
  preparation and serving still validate the actual deployment before operating.
- Give init/status a minimal host initialization path that neither validates nor
  rewrites webapp credentials/proxy settings. Use base Compose without Funnel and
  process-local neutral values for unrelated ingress interpolation (Compose
  parses the full model even for offline commands). Never start ingress with
  those values. Permit storage-only setup without a required auth-file mount by
  mounting its existing private auth directory into trusted setup instead.
- Atomically publish credential files, with saved password published before its
  hash. Reuse that password after interrupted initial creation. If an existing
  hash disagrees with the saved password, reconcile the hash with that password
  while preserving the session secret. A missing password beside existing auth
  is unrecoverable from a hash: explain explicit rotation; never silently rotate.
  No journal or additional persistent state. Explicit rotation still rotates.
- Derive a missing `.pub` from the existing private SSH key; preserve the private
  identity and existing complete pairs. Invalid private material fails visibly.
- Add generalized rules requiring concrete, operation-scoped preconditions,
  persistence across unrelated updates, separation of readiness/history/access,
  and simple retry-safe publication/derived-data repair.

## Phase P1: implement, qualify and document

Update all direct consumers, tests, operating guides and affected historical plan
claims (editable research configuration). Focused unit tests cover build/code
changes retaining completion; missing/wrong/corrupt records refusing serving;
invalid runtime settings allowing offline inspection but refusing networked
operations; credential interruption/retry and preserved secrets; actual SSH key
sidecar repair and private-key preservation.

Use disposable real-image fixtures for native explicit-path inspection with
missing/malformed/unsafe runtime config, unchanged wallet identity, completed
record retention through wrapper changes/restarts, and forbidden serving paths.
Run storage qualification for real setup key repair, credential installation and
persistence, plus effective Compose models and focused checks. No live funding,
bootstrap, warming or funded service starts. Document remaining live limits.

Independent read-only design review precedes implementation; independent final
review covers P1 and the combined change. Commit coherent completed work, record
results here, and retain this plan. Existing browser and readonly-configuration
plans retain their scope; no new configuration-integrity enforcement is added.
