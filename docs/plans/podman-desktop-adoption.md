# Adopt the native Podman policy for the desktop executor

Baseline: `rootless-podman-support` at `c7eabe9` (2026-11-13).
Status: proposed; implementation and normal-path qualification pending.

The operator explicitly accepts the native Podman seccomp policy for desktop
use and requests removing the desktop refusal and qualifying normal deployment.
The previous experiment passed actual desktop/browser, sandbox, isolation,
ingress and recovery checks on Debian 13 ARM64 rootless Podman 5.4.2 with stock
Compose 5.1.4. It also fixed persistent Chromium coordination after recreation.
Production still selects Docker's pinned Moby-derived profile and refuses Podman.

Use the same native engine policy for both lean and desktop Podman executors.
This preserves the existing lean Podman policy; it is not policy equivalence
with Docker. Docker keeps its current custom desktop profile. Preserve active
seccomp, Chromium's own sandbox, NNP, the existing SSH capability bounding set,
zero-capability runner children, separate namespaces/mounts, Tor and exact peer
grants, readonly root and persistent identities/cookies. No unconfined mode,
sandbox bypass, extra capabilities, API translator, patched provider or new
operator setting is needed or authorized.

## A1 — Promote the qualified configuration

Put the native-policy `security_opt: !override [no-new-privileges:true]` and
empty `/tmp` and `/run` mounts (`notmpcopyup`) in `compose.podman.yaml` for the
executor. The latter avoids copying upstream's UID-1000 runtime directory into
the UID-10000 desktop; retain the existing mount modes/destinations. Applying
the empty-mount contract to lean Podman also matches the Docker behavior.

Normal desktop startup must pass preflight on Podman. Retain the small generic
diagnostic for genuinely unsupported custom profiles supplied to Podman's
Compose API, but remove its obsolete desktop-needs-Docker advice. This does not
claim inline custom-profile delivery was fixed. Keep Docker's policy unchanged.

Remove the experimental overlay/driver and replace their model test with checks
of normal Docker/Podman models, desktop off/on, base/Funnel, and preflight
acceptance. Test unchanged capability/mount/network invariants and active NNP.
Use existing standard computer/browser/webapp fixtures. Ensure Make's desktop
preflight renders desktop enabled, matching its builds and runtime tests.

Update README operator guidance, configuration, architecture, development checks
and the affected capability-reduction plan. Preserve prior qualification history
as history; remove commands/claims for deleted experimental entry points and
state the accepted engine-specific policy choices without implying equivalence.

## A2 — Qualify normal engine paths and review

Obtain fresh independent read-only design review before implementation. Run
unit/model/compile checks with each actual provider. On the VM use normal
Compose and image tags, without the deleted test security overlay: exercise
desktop-enabled preflight, the standard computer-use/core suite (real actions,
SSH/Python placement, capabilities/private state, Tor/forbidden paths,
on/off/on actual identity/cookies, dependency refusal and Tor outage/recovery),
browser harness/sandbox/cancellation/recreation, and local/simulated HTTPS
desktop/browser results. Run the networkless startup preservation/error checks.
On Docker repeat the standard affected desktop/browser paths and effective
models, preserving its custom profile. Run lean core on Podman because its
tmpfs behavior is now explicitly empty; reuse unchanged prior broad evidence.

Serialize fixed-subnet fixtures on each host. Never enroll Funnel, run provider
inference/payments, change operator configuration or delete private state.
Restore ordinary lean image tags after tests; remove current disposable resources
and preserve unrelated resources and the older Docker fixture volumes.

Obtain a fresh independent final combined source/evidence review; resolve material
findings and rerun affected checks. Commit coherent validated implementation and
record accepted scope, evidence and limits in maintained guides. Remove this plan
after acceptance, resolving links under the planning workflow. Other platforms,
live public ingress, provider attestation and funded settlement remain outside
the qualification claim.
