# Private webapp content: safe defaults and passive media

Status: planned. Part 1 of the browser privacy work. Part 2 is
[interactive content and media](webapp-interactive-content.md).
Execution follows the [planning workflow](../planning-workflow.md) and
[repository instructions](../../AGENTS.md).

Planning baseline: branch `main`, commit `2d0ec55`. This revision expands the
plans only; it does not implement or qualify browser privacy. Record the actual
implementation baseline when execution starts, without rewriting this history.

## Scope and maintained documentation

The policy covers browser-rendered resources and the webapp content proxy. It
does not gate ordinary model inference, agent tool calls, deliberate downloads,
or user-requested external navigation. Downloading a document does not make it
safe to open outside the webapp; state that explicitly in fallback UI/docs.
Do not promise protection against trusted administrator actions, arbitrary
installed backend plugins, a compromised host, or browser extensions.

Update [webapp operations](../webapp.md) with modes, consent, fallbacks and
supported browsers; [configuration](../configuration.md) with `.env` ownership
and any consent persistence; and [updates/plugins](../updates-and-plugins.md)
with the derived-image build/patch/update procedure. Update the README and
AGENTS.md where their current-image or privacy descriptions change. Reuse these
guides rather than creating an extra documentation hierarchy.

## Objective and completion boundary

Prevent unapproved automatic connections from the user's browser while preserving
local content and privately loading supported external images and icons. This
plan must be independently safe and useful: part 2 restores functionality, rather
than completing a security boundary left unfinished here.

Deliberate clicks on ordinary external links remain allowed. Docker's transparent
Tor routing covers gateway requests, not requests originating in the browser.
Authentication and Funnel do not change that distinction. Fetching a unique URL
through Tor can still reveal that someone viewed it; it protects the browser's
address, not the fact of retrieval. The `ask` mode addresses that additional concern.

## Current implementation and findings

- We use the pinned official Hermes image without application source patches.
  HAProxy adds restrictions for fonts and styles alongside Hermes's own CSP.
- Markdown/generated images try remote browser loading before the gateway proxy.
  The existing image proxy accepts only selected image CDN hosts. It is not an
  arbitrary-image proxy and cannot provide private general Markdown rendering as-is.
- Connector-supplied icon URLs can cause browser image loads. Browser-hosted link
  title fetching is disabled and the favicon resolver appears desktop-only;
  verify both against the exact pinned image during implementation.
- Social embeds already have an ask/always/off consent mechanism. Preview and
  plugin HTML responses have separate, permissive network policies despite their
  opaque-origin sandboxes. Credential isolation does not prevent browser egress.
- A controlled Chromium test with the current policies permitted remote main-page
  images, fetches and frames, and preview images and scripts. Fake external
  destinations were intercepted before external network access.

Audit the exact pinned image, including compiled assets, before patching. The
reference checkout can differ from the packaged runtime.

### Revision and integration contracts to verify

At this planning baseline, `compose.yaml` selects official Hermes v0.23.0:
`nousresearch/hermes-agent@sha256:adb7890916de63245523492be8f68f9d2095fecbec4e2a6dab7960381f0fc002`.
Its source comment names upstream `2bd378ed`; the inspected reference checkout
is `36e095f59f1a6c06078b560536493256b38e5a00`. These are not interchangeable.

Before authoring patches, establish the full source identity matching the image,
the packaged webapp build inputs/output location, and the native initialization
and dispatch contracts. Do not silently upgrade Hermes to make patching easier.
If source correspondence cannot be established, record that blocker and select
an explicit reviewed source/base change before proceeding.

Relevant contracts include shared renderers in `apps/desktop/src/`, gateway
`hermes_cli/web_routers/files.py`, `webapp_page_policy.py` and
`webapp_previews.py`; `.env` parsing and configuration rendering under `scripts/`
and `components/webapp/`; and the shared Hermes image used by runtime, setup,
maintenance and fixtures. `scripts/check-updates.py` currently extracts the
official image pin from Compose, so derived-image packaging must update that
consumer without adding an image/provenance registry.

## One deployment policy

Introduce one strictly validated root `.env` / `.env.example` setting:

```dotenv
WEBAPP_EXTERNAL_CONTENT=tor_proxied
```

| Value | Behavior |
| --- | --- |
| `tor_proxied` | Default. Automatically fetch supported passive external resources through Hermes over Tor. Unsupported private loading gets a placeholder and an ordinary external link. |
| `ask` | Ask before any external resource fetch, including a Tor-proxied fetch. Prefer private loading when implemented. |
| `off` | Block external resource loading within the app, including proxy retrieval. Preserve local content and deliberate external link clicks. |
| `browser_native` | Explicitly permit automatic browser-native external loading for users relying on Tor Browser or another browser privacy arrangement. Preserve unrelated security controls. |

Do not add `WEBAPP_DIRECT_CONTENT`. The distinction between private and
browser-native retrieval belongs in consent records and explanatory UI.
Treat `off` as a deployment ceiling, with no in-app bypass. Under the two private
modes, direct in-app opt-in for unsupported content is deferred to part 2; offer
"Open externally" instead. Describe this limitation without implying a working
in-app player. Invalid settings fail before exposure.

Use root `.env` as the source for Compose configuration, passing only selected
values to the services that need them. Policy must be enforced by the gateway and
response headers, not only by a browser preference or model-editable profile.
No image versions belong in `.env` and no migration/compatibility layer is needed.
This selected deployment-environment contract does not depend on the deferred
[read-only configuration](readonly-configuration.md) or
[capability reduction](capability-reduction.md) plans. Preserve native setup and
upgrade behavior without importing those plans' broader work or adding prerelease
migration machinery. The maintained [ingress guide](../webapp.md) describes the
implemented authentication/network baseline; this plan adds browser privacy.

Define how a mode change reaches both the gateway and generated ingress policy:
document the required configuration render/recreation steps. Do not claim that
editing `.env` changes a running process. On mismatch, missing policy or startup
failure, refuse the affected operation rather than expose a permissive policy.

## State of content when this plan lands

| Content | Default `tor_proxied` behavior |
| --- | --- |
| External images, thumbnails and connector icons | Proxy first through Tor; never try the browser URL first. |
| Local images, generated graphs and files | Existing authenticated Hermes/executor file paths continue working. |
| Local audio/video | Existing authenticated playback continues working. |
| External audio/video | Placeholder and external link; no automatic source, poster, subtitle or manifest requests from the browser. A poster may use the approved image proxy. |
| Social embeds | Placeholder and external link; existing saved permissions cannot bypass the new policy. |
| HTML/plugin previews | Preserve offline rendering where its network boundary is enforceable. Otherwise provide inert rendering or a download fallback. |
| Previews requiring external libraries, APIs or nested frames | Explain the unavailable dependency; no silent direct-loading fallback. |
| Ordinary external links | Remain deliberate browser navigation. |

Classify content by where its bytes come from. An agent-generated image hosted
on a public CDN is external; a generated graph served by Hermes is local. Local
HTML containing external references still requires the external-content policy.

## Private image retrieval

1. Change shared image/icon rendering to select the authenticated gateway endpoint
   before assigning any remote URL to a browser resource-loading attribute.
   Cover Markdown, generated results, thumbnails, galleries and connector icons.
2. Expand the existing image proxy or add a narrowly scoped replacement. Require
   authentication and enforce the deployment policy and any required approval.
   In `ask` mode, rendering or prefetching must not retrieve the resource before
   approval. Isolate grants to the intended resource/origin and loading method.
3. Admit public HTTP(S) media only. Prevent access to host/VM/LAN addresses,
   loopback, cloud metadata, gateway APIs, Teep and MCP services. Validate each
   redirect, URL parsing edge cases and destination resolution using a design
   compatible with transparent Tor DNS. Do not rely solely on a hostname check
   while the fetcher retains routes to privileged internal services.
4. Never forward browser credentials, cookies, authorization or referrers.
   Do not expose a general URL fetch API or an arbitrary HTML/JavaScript proxy.
   Validate actual media type; reject or safely transform active formats such as
   SVG rather than serving attacker-controlled documents under the app origin.
5. Retain meaningful streaming size checks, timeouts and bounded caching for this
   endpoint. Do not add arbitrary container resource or storage quotas. Cache
   access must remain authenticated and permission changes must be respected.
6. Fail visibly with retry and external-link options. Proxy failure must never
   trigger an automatic browser-native retry. Avoid logging token-bearing URLs.

## Consent, CSP and preview enforcement

- Provide a consistent placeholder showing the destination and whether an action
  fetches through Tor or opens the user's browser. Implement private load-once
  and revocable remembered origin permissions for supported resources. Keep
  grants separate from model/tool configuration and inaccessible to the SSH
  executor. Untrusted preview messages cannot authorize themselves.
- Choose the smallest native persistence mechanism that can enforce those
  grants. Record scope, lifetime, logout/restart behavior and revocation semantics
  before implementation. Protect consent mutations with authentication and
  origin/CSRF checks; define how an opaque preview is denied approval authority.
  Do not create a generic permissions service, receipt engine or policy database
  merely to support image approval. Cached bytes must not bypass `off` or a
  revoked grant. Local and Funnel browser origins must not accidentally share
  approvals; document any deliberately shared server-side scope.
- Replace or integrate social embed preferences so they cannot independently
  override the deployment policy. Persistent consent must be specific to the
  loading method; private approval never implies browser-native approval.
- Enforce source restrictions on the main page and every separately served HTML
  preview/plugin shell. Audit nested frames, workers, CSS URLs, media metadata,
  redirects, resource hints, and blob/data documents and their inherited policies.
- Preserve native main-page bootstrap hashes and unrelated script protections.
  An additive CSP may restrict but cannot relax another policy. Scope policies
  appropriately instead of deleting native authentication or security headers.
- Allow required same-origin authenticated APIs and exact-origin WebSockets;
  do not permit all `ws:`/`wss:` destinations. Preserve localhost and Funnel.
  Add a no-referrer policy and disable DNS prefetching where supported.
- Treat WebRTC/STUN and scripted navigation as separate audit items, not as
  implicitly covered by `connect-src`. If supported browsers cannot enforce
  network isolation for arbitrary preview scripts, disable those scripts in
  private modes and provide an inert/download fallback. A JavaScript shim or
  camera/microphone permission restriction is not a network security boundary.
- `browser_native` permits external loading without removing authentication,
  origin validation, main-app script restrictions or preview sandboxing. Clearly
  document that browser-native traffic bypasses the stack's Tor gateway.

## Open decisions and design gate P1-DESIGN

Resolve these through read-only inspection and focused disposable experiments
before substantive implementation. Record selected answers and supporting
revisions here, not a generic research framework:

- How does the source match the packaged image, and what is the smallest derived
  build that preserves official runtime/setup behavior and checks patch mismatch?
- How can public-only proxy fetching be enforced despite privileged internal
  routes and Tor DNS behavior? Cover redirects, DNS changes, unusual IP forms
  and domain names resolving to internal addresses. No new proxy service is
  assumed; justify one only if a concrete boundary cannot otherwise be enforced.
- Which existing routes can serve arbitrary HTML/SVG/files, redirects or plugin
  content, including direct navigation and new tabs? Classify active content,
  rather than exempting an authenticated file route from policy enforcement.
- Which browsers/versions can enforce the selected preview restrictions,
  including WebRTC, navigation and resource hints? Choose an inert fallback
  wherever containment is not demonstrated. Do not widen this work into a
  general-purpose JavaScript sandbox.
- What minimal consent storage and authenticated mutation interface meets the
  scope/lifetime rules above? How will all consumers receive one authoritative
  deployment mode without independent permissive defaults?

Gate P1-DESIGN is a fresh, read-only subagent review with no inherited turns,
following the workflow. Supply the exact plan revision/snapshot, baseline,
source evidence, proposed answers and relevant guides. Review scope includes
SSRF, browser egress, packaging, functionality and unnecessary complexity.
Resolve material findings before relying on the affected design. The earlier
Chromium experiment is preliminary evidence, not this gate or final acceptance.

## Commit phases and review gates

Each phase can contain focused development/correction commits, but its completion
requires coherent behavior, documentation and checks. Commit phase results and
review exact SHAs. Until P1-3/P1-4 pass, label intermediate builds incomplete;
do not advertise safe defaults or deploy them as the finished privacy feature.

### P1-1: derived image and authoritative policy input

- Add explicit reviewed source patches and a reproducible webapp asset build
  under `components/hermes/`, based on the verified pinned official image.
  Fail on patch/source mismatch; never edit minified bundles or patch at startup.
- Add strict mode parsing and selected environment propagation, updating
  `.env.example`, Compose, configuration generation and all image consumers:
  runtime, setup/maintenance, update inventory and fixtures. Do not ship a
  permissive alternate default or invent a merged setup image.
- Verify a clean build, effective Compose model, image inventory, native CLI and
  official startup/UID behavior. Test mode validation and absent/invalid values.
  Update configuration and build/update documentation in this phase.
- Review gate P1-BUILD: independently review the phase SHA and its consumers,
  including whether source matching and patch checks actually cover the assets
  used at runtime. This review may cover other completed phase work explicitly
  included in its brief; no duplicate gate review is needed.

### P1-2: public-only image retrieval and private consent

- Implement the narrow authenticated image proxy and minimal consent storage/API.
  Enforce mode, origin/resource scope and revocation on the backend. Close old
  proxy routes that would bypass the policy; do not retain compatibility aliases.
- Test real fetch destinations with controlled fixtures: allowed public images,
  redirects, private/host/VM/Teep/MCP destinations, DNS changes, malformed URLs,
  unauthorized requests, forged consent, active content and credential stripping.
  Do not load real keys or treasury wallets. Update consent/proxy operating docs.
- Review gate P1-FETCH: independently assess the exact phase commits and relevant
  existing HTTP/file routes. Exit requires evidence that broadening the CDN
  allowlist has not created an internal-service proxy or an approval bypass.

### P1-3: proxy-first UI, all-document enforcement and fallbacks

- Integrate shared image/icon renderers, private consent UI and revocation.
  Replace conflicting social preferences; unsupported content gets honest
  non-loading placeholders and external links.
- Apply mode-aware enforcement to main, preview, plugin, active file and nested
  document paths. Preserve native trusted scripts, authenticated APIs and exact
  local/Funnel WebSockets. Disable unsafe preview execution where required.
- Extend existing browser fixtures to exercise actual rendered model/tool
  output, rather than only synthetic policy pages. Test all four modes and
  retained local images/files/media, links, auth and chat behavior.
- Update `docs/webapp.md` with the working UI and limitations. Independently
  review this phase's commits and the combined P1-1 through P1-3 boundary before
  declaring default browser containment implemented.

### P1-4: integrated qualification and documentation handoff

- Run the acceptance checks below against the built image with part 2 absent.
  Complete supported-browser and local/simulated-Funnel coverage, network failure,
  restart, policy-change and stale-page tests. An already open page must not
  regain proxy access after a stricter server policy takes effect; state what
  old browser documents cannot be recalled and when reload is required.
- Update README, maintained guides, AGENTS.md and part 2's dependency contract.
  Record exact reviewed revisions, checks, limitations and remaining decisions.
- Gate P1-FINAL independently reviews the complete accumulated implementation,
  corrections, documentation and acceptance evidence. It may serve as the
  P1-4 phase review too. Resolve material findings and revalidate affected paths.
  Retain this plan with accurate completion status; do not delete it.

## Qualification and acceptance

- Exercise real browser rendering in local HTTP and simulated Funnel HTTPS
  contexts against the built image, with isolated test state.
- Use controlled external canaries and network observation to distinguish
  browser requests, DNS/preconnect activity and gateway Tor retrieval. A DOM
  assertion or CSP console message alone is insufficient proof of no egress.
- Cover images/icons, media posters/subtitles/manifests, CSS URLs, remote frames,
  preview scripts/fetches/workers, nested blob/data documents, redirects and
  applicable WebRTC/navigation paths. Do not contact third-party tracking sites.
- Verify all four modes; no pre-consent proxy fetch in `ask`, no external in-app
  retrieval in `off`, and no automatic direct fallback in private modes. Confirm
  grant revocation and that untrusted content cannot mint approvals.
- Test proxy authentication, active content rejection, credential stripping and
  SSRF destinations including the stack's explicitly permitted internal routes.
- Confirm local/generated content, local media, login, chat streaming, downloads,
  ordinary link clicks and exact-origin WebSockets remain functional. Check both
  ingress paths and preserve SSH executor and host/VM isolation regressions.
- Run appropriate repository checks and focused browser/network tests. Document
  browser coverage, limitations and policy changes. No production wallet use,
  live Funnel enrollment or state deletion is required for qualification.

Start with `make check` and the affected unit/build checks, then `make webapp-test`
extended for this feature. Use `make test` for affected routing/executor contracts
and `make plugins-test` where image/plugin behavior changed. Serialize shared
network fixtures. Tests already establishing unchanged contracts need not be
repeated without a reason; missing required browser/egress observations remain
explicit missing evidence. Controlled fixtures can prove destination policy;
an actual Tor-routed fetch needs separate route evidence, never an inference
that any successful same-origin response must have used Tor.

## Evidence and completion status

- Implementation: not started; P1-1 through P1-4 pending.
- Design/phase/final reviews: not yet passed. Plan review alone is not a review
  of a future implementation or its unresolved technical decisions.
- Existing evidence: source inspection and the preliminary intercepted Chromium
  policy experiment described above; no full feature or cross-browser guarantee.
- Planning-only review: a fresh read-only subagent reviewed `2d0ec55` plus these
  two revised plan files. No blocking findings; the suggested clarification that
  deferred hardening plans are not prerequisites was incorporated. This is not
  P1-DESIGN acceptance of its still-unresolved source/network/browser decisions.
- Execution authority: local commits and disposable qualification within task
  scope; no production wallet operations, public exposure or state destruction.

Maintain this short record with reviewed SHAs, material finding dispositions and
focused results as work lands. Do not duplicate private logs or generated reports.

Completion requires a safe default with part 2 entirely absent. Any resource that
cannot be loaded privately and safely must have an honest, non-loading fallback.
