# Read-only runtime configuration

Status: proposed; no runtime changes made.

## Objective

Prevent runtime agent processes from changing operator-owned deployment policy
while preserving an explicit, usable configuration and upgrade workflow. First
determine which settings can be protected without breaking Hermes's supported
configuration writes or migrations.

This is configuration integrity work, not a claim that all agent state becomes
immutable. Resource and storage limits, a read-only root filesystem, and changes
to the SSH execution boundary are outside scope.

## Current baseline

- `bootstrap` copies `components/hermes/config.example.yaml` into the `hermes-data` volume
  only when `/opt/data/config.yaml` is absent.
- For an existing config, bootstrap checks the SSH backend and custom teep
  endpoint before permitting agent startup.
- Hermes owns its writable state under `/opt/data`, including configuration,
  sessions, skills, and memories.
- The networkless `configure` service currently edits that same data volume
  as UID 10000. Setup and configuration commands can also write configuration.
- Hermes configuration code uses atomic replacement. A read-only file mount
  can prevent both intended writes and automatic migration; even a writable
  file mount may conflict with replacement of the mounted inode.
- Provider keys live in teep's environment, outside Hermes and the executor.
  Read-only configuration would not add confidentiality to those keys.

## Invariants

- Keep the SSH backend, teep endpoint, and selected MCP boundaries intact.
- Keep sessions, memories, and other required runtime state writable.
- Preserve existing configuration and user settings during migration.
- Give the runtime no writable mount or alternate write path to the protected
  authoritative configuration source.
- Keep administrative editing separate from runtime execution. Do not put a
  privileged configuration writer under the agent's tool authority.
- Make rejected runtime edits and migration requirements clear. Do not silently
  ignore a requested change, create a divergent writable config, or temporarily
  make protected policy writable at runtime.

## Design investigation

Inspect the exact pinned Hermes image before choosing a design:

1. Inventory configuration consumers and writers: initial setup, `config set`,
   model selection, MCP installation/authentication, profile management,
   gateway reload, and automatic schema or version migrations.
2. Identify which settings are operator policy and which are ordinary mutable
   preferences. Decide whether protection is required only for the default
   profile or also for every supported additional profile.
3. Evaluate Hermes's managed configuration/policy facilities, if supported by
   the pinned image. Verify which keys they enforce, precedence, failure
   behavior, and whether runtime-owned files can override them. Do not infer
   enforcement merely from a setting's name or documentation in a newer branch.
4. Compare that facility with a complete read-only configuration mount. The
   latter must account for every required write and migration path, not just
   normal chat startup.
5. Select and document one authoritative configuration model before changing
   the deployment. Prefer a mechanism that protects policy while retaining
   normal preference edits when it provides the required enforcement.

## Candidate mount-based workflow

If a complete read-only configuration file is the appropriate design:

1. Introduce a dedicated operator-owned configuration source, separate from
   writable agent state. Preserve the existing configuration through an
   explicit export/import step; do not replace it with the example template.
2. Mount the selected configuration read-only into the runtime. Avoid mounting
   its parent directory writable through the data volume or another alias.
3. Adapt bootstrap to validate the mounted configuration and its ownership
   contract without trying to copy, chown, chmod, or migrate that mount.
4. Adapt `configure` into a networkless maintenance workflow. It should edit a
   writable staging directory that supports atomic file replacement, validate
   the candidate, and publish it through an operator-controlled action.
5. Define the application step. Recreating runtime containers after publication
   is the conservative default: an existing file bind mount can retain the old
   inode after the operator atomically replaces its source file. Demonstrate
   any supported reload alternative rather than assuming it works.
6. Handle image upgrades and configuration migrations against a staging copy
   before the new runtime starts. Retain the previous image/configuration pair
   for rollback. Never solve a migration failure by making runtime policy
   writable or disabling the migration without understanding its requirements.

A managed-policy design needs an equivalent documented editing, validation,
application, migration, and rollback workflow, even if preference files remain
writable.

## Qualification

Use disposable data and the real production entrypoint. Check:

- Fresh provisioning and migration from a populated writable configuration,
  preserving unrelated settings and existing key identities.
- Startup, CLI and gateway operation, supported profiles, and restart behavior.
- An attempted runtime write or atomic replacement of protected configuration
  fails, including attempts through any alternate mounted path.
- Operator edits succeed through the maintenance path, are validated before
  publication, and become the effective configuration after the documented
  application step. Confirm the loaded values, not just the source file.
- Runtime setup, model selection, MCP changes, and other affected writers
  either remain supported or give an actionable maintenance instruction.
- Required sessions, memories, and other mutable state still work.
- Malformed configuration, unsupported policy keys, and incompatible image
  upgrades fail visibly without a writable-policy fallback.
- The existing SSH execution, Tor routing, host/VM isolation, and selected MCP
  integration checks still pass.
- A representative upgrade/migration and rollback preserve configuration and
  data. Do not claim general upgrade compatibility from one startup test.

Run `make check` and `make test` for implementation changes, together with
focused initialization, administrative editing, and migration checks.

## Acceptance and rollout

Implement only after the authoritative configuration mechanism and all affected
user workflows are understood. Document which policy is protected, what remains
mutable, and how to make a legitimate change. If protection requires changing a
supported workflow, provide its concrete replacement as part of the same change.

Rollback must restore the previous image, configuration source, and mount
arrangement while preserving state volumes. Runtime configuration protection
does not replace tool permissions, MCP authorization, credential separation,
or review of writable plugins and skills.
