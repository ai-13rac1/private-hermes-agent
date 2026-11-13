# Podman desktop with the native default seccomp profile

Baseline: `rootless-podman-support` at `15d7d8a` (2026-11-13).
Status: proposed qualification experiment; production support remains guarded.

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
Use a test-only overlay that replaces only executor security options with
no-new-privileges and selects a separate trial image tag. Native Podman supplies
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
container as UID 10000, cap-drop ALL and no-new-privileges, using temporary
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
