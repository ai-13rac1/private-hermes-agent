# Podman desktop with the native default seccomp profile

Baseline: `rootless-podman-support` at `15d7d8a` (2026-11-13).
Status: Q1, core and ingress passed; confirmed recreation defect; Q3 proposed.

The operator requests trying Chromium/computer-use with Podman's native default
seccomp policy before adding a policy-delivery translator. Existing probes on
Debian 13 ARM64 Podman 5.4.2 show active seccomp, permitted user namespaces and
setns kernel validation, but extra allowed `keyctl`/`clone3` interfaces compared
with the pinned desktop profile. Those probes do not qualify Chromium or accept
identical security. No automatic production policy change is authorized by a
successful isolated probe; report the concrete qualification and security delta
before proposing adoption.

## Preserved boundaries and scope

Keep the existing production guard and Docker desktop profile. Use the installed
stock Compose 5.1.4 provider and the pinned desktop source in
`components/executor/Dockerfile` (Hermes sandbox index
`c7d8607d076f26a64e0bd6828f74e1764af43fe3281368188459bb693bfa7567`).
Use a test-only overlay that replaces executor security options with
no-new-privileges and selects a separate trial image tag. Disable tmpfs copy-up
for executor /tmp and /run to match the empty mounts required by startup; preserve
all capabilities, mount destinations/modes and network settings. Native Podman supplies
its default seccomp filter; never use unconfined, privileged, host networking,
extra capabilities or Chromium sandbox-disabling flags. Preserve SSH-separated
processes/mounts, Tor routing, namespace ownership and private endpoint denial.
All runtime state belongs to existing disposable test projects. Normal state,
provider configuration and the ordinary lean image tag are preserved. No live
Funnel, provider inference, payments or funded wallet operations are in scope.

This is a qualification experiment, not an API proxy, provider migration or new
runtime orchestration design. Reuse existing lifecycle/browser fixtures. A small
Podman-only host test entry point may select the experimental overlay and run
focused phases; do not add a production preference or adapter framework.

## Q1 — Standalone Chromium sandbox

Add `tests/podman-desktop-compose.yaml` and a focused test entry point under
`tests/`. Refuse non-Podman execution before mutation. Build the existing desktop
target under a trial tag without changing operator configuration or replacing
the lean image. Run headless Chromium in a networkless read-only disposable
container with the existing executor bounding set (cap-drop ALL then SETUID,
SETGID and SYS_CHROOT) and no-new-privileges. Drop to UID 10000 with zero
effective/permitted/inheritable/ambient capabilities before Chromium, using temporary
writable runtime/profile directories. Require seccomp mode 2 and actual
`chrome://sandbox` namespace, PID/network namespace and seccomp-BPF diagnostics.
Also check nested user-namespace root cannot rejoin or create raw sockets in its
parent network namespace. Stop and diagnose a real failure; no sandbox fallback.

## Q2 — Real SSH desktop/browser and ingress qualification

After Q1 succeeds, reuse core SSH/Tor/MCP allowed/forbidden-path checks with the
experimental executor, including the existing computer-use actions, child
capability checks, idle/reconnect behavior, on/off/on identity/cookie persistence,
and Tor outage/recovery. Reuse browser-use checks for native harness execution,
screenshots/downloads, concurrent sessions, cancellation, missing harness and
sandbox diagnostics. Exercise authenticated computer/browser results through local
and simulated HTTPS ingress using the existing disposable webapp fixture; make
only focused fixture corrections needed to reach those assertions.

Serialize fixed-network fixtures. Inspect effective models before runtime,
including unchanged capability/mount/network settings and the retained Docker
profile. Keep the default-policy syscall differences explicit. Update maintained
qualification guidance with actual results and unavailable evidence. If trials
fail, record the exact remaining barrier rather than adding transport/policy
fallbacks. Independent final read-only review must assess the combined experimental
change and evidence. Qualification success alone does not enable production
Podman desktop support; adoption needs a separate explicit policy decision.

## Review and completion

Obtain fresh independent read-only design review before implementation. After
focused checks and the experiment, obtain fresh combined source/evidence review;
resolve material findings and rerun affected checks. Commit coherent tested work,
then retain this plan while required qualification/review is outstanding. Once
this experiment is accepted, preserve outcomes and deferrals in maintained guides
and remove this plan under `docs/planning-workflow.md`.

## Evidence so far

Fresh independent design review accepted plan commit `a4d89a0`. The model check
passes and compares every executor setting and all other services/networks/volumes;
only the trial image, security options and tmpfs copy-up behavior differ. Local `make check` passed 160
unit tests, all four effective models and compilation.

Q1 passed on Debian 13 ARM64 Podman 5.4.2 with Chromium 156.0.8078.4, native
`/usr/share/containers/seccomp.json`, UID 10000, zero child capabilities, NNP 1
and seccomp 2. Actual Chromium reports namespace/PID/network/seccomp-BPF layers;
nested user-namespace root cannot join or open raw sockets in the parent network.
An initial probe incorrectly dropped the executor's existing bounding set and
failed Chromium chroot: Podman conditionally allows chroot based on SYS_CHROOT
at container creation. Correcting the fixture to match the real executor, then
dropping process identity/capabilities, resolves it without adding privileges.
No production setting changed at this stage. Q1 log on VM:
`/tmp/private-hermes-podman-default-desktop-sandbox.log`.

The first real Q2 launch exposed Podman tmpfs copy-up of image-seeded
`/tmp/hermes-runtime`, owned by upstream UID 1000. Runner UID 10000 cannot chmod
it, so SSH never starts. Q2 now uses native `notmpcopyup` for the executor's /tmp
and /run, matching Docker's empty tmpfs behavior without added capabilities,
image mutation or private-state changes. This is an experimentally required third
overlay difference; production files remain unchanged. Requalify Q1 and Q2 with
that correction and review the combined change.

Corrected core qualification passed end-to-end, including actual SSH desktop,
all private/peer/Tor/MCP controls, capability and nested-namespace denials,
on/off/on identity/workspace/browser-cookie persistence, missing dependency/SSH
refusal and recovery, plus Tor outage and harness recovery. The public-key
snapshot fixture now hashes only the public host key as authorized test root;
runner-owned marker snapshots remain runner, preserving native root-only auth
bind permissions. Docker desktop-only and local/HTTPS webapp/browser-result
qualification passed with the shared fixture corrections. Local and VM final
`make check` each passed 160 units, effective models and compilation. Browser
harness and webapp phases on Podman remain in progress before final acceptance.

The Podman webapp phase passed both local and simulated HTTPS desktop transport,
takeover/ticket controls, browser screenshots/downloads and authentication refusal.
Main browser-harness and actual sandbox diagnostics also passed. The separate
missing-harness check refused execution correctly while hidden, but restoring
and recreating the executor returned a Chromium DevTools-startup timeout. This
is an unresolved qualification failure, not a pass or proof of a seccomp cause.
Networkless force-killed headless and headed Chromium recreation controls passed
with both native default and exact custom profiles, so a stale-hostname profile
lock hypothesis is unconfirmed. Reproduce with disposable failed-state retention
and inspect actual launch stderr, publication/Xauthority and singleton metadata
before proposing a correction; do not add retries, delete profiles or bypass
sandboxing to hide the failure.

## Q3 — Clear coordination files at the owning container boundary

Amendment after exact failed-state diagnosis: normal Chromium stderr confirms
its profile is locked by an old executor hostname/PID. The initial isolated
controls reused Chromium PID 1 and did not reproduce the real PID/hostname
transition; their passes do not clear the defect. Q2 remains incomplete. The
first combined read-only review found this material defect and accepted the
remaining trial/fixture source and completed evidence, without final acceptance.

Fix the existing desktop startup script, before sshd accepts sessions and before
any user browser can run. Extend its existing UID-10000 setpriv preparation to
unlink exactly `SingletonLock`, `SingletonSocket`, `SingletonCookie` and
`DevToolsActivePort` inside the fixed executor browser profile. These are
per-process/container coordination, not browser cookies or credentials. Never
follow their symlink targets or recursively delete state. Unexpected errors must
fail visibly. Preserve the profile, cookies/localStorage, runner work, SSH keys,
root-only auth directory, read-only root, caps/NNP, Docker custom policy and
production Podman feature guard. Do not delete locks during ordinary browser
launch or add a recovery framework/retries. This is a shared desktop reliability
fix, not production adoption of a different seccomp policy.

Obtain fresh independent design review of this amendment before code changes.
Build both desktop images and rerun actual missing-harness refusal/recreation/
recovery on Docker and Podman, with existing main harness and sandbox checks.
Add a focused networkless runtime check with a seeded profile: exact stale
coordination files disappear at startup while cookie-like data and unrelated
files/keys remain byte-identical, UID 10000 retains zero process caps, and root
cannot rewrite protected mounts. Repeat actual on/off/on browser cookie/identity
persistence because startup changed. Reuse still-valid network/ingress evidence
unless a correction affects those contracts. Finally obtain a new independent
combined review of the resulting source and actual both-engine evidence; resolve
material findings before claiming Q2/Q3 acceptance or removing this plan.
