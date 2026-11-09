# Private webapp content: safe defaults and passive media

Status: planned. Part 1 of the browser privacy work. Part 2 is
[interactive content and media](webapp-interactive-content.md).

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

## Packaging and implementation sequence

1. Inventory all browser resource-loading paths in the pinned runtime and record
   the required restrictions and fallback behavior before editing.
2. Add policy parsing, gateway enforcement and generated CSP configuration.
3. Add the safe image endpoint, proxy-first renderers and shared consent UI.
   Close unsupported content paths with the documented placeholders/fallbacks.
4. Build the modified webapp assets reproducibly. Use a derived image based on
   the pinned official image, with explicit reviewed patches under
   `components/hermes/`; do not edit minified bundles or patch at startup.
   Match source to the packaged revision and fail builds on patch mismatch.
5. Update image inventory/update checks, setup/runtime image references and
   operator docs as required. Keep the official initialization behavior and
   existing network topology; no merged setup image or new service is assumed.

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

Completion requires a safe default with part 2 entirely absent. Any resource that
cannot be loaded privately and safely must have an honest, non-loading fallback.
