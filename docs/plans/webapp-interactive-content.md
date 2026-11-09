# Private webapp content: streaming and interactive opt-in

Status: planned. Part 2, dependent on
[safe defaults and passive media](webapp-private-content.md).

## Objective and starting state

Restore additional media and interactive functionality without weakening the
safe default established by part 1. This plan is not required to close known
automatic browser leaks. It must be possible to defer it indefinitely.

At the end of part 1, private image/icon loading and local content work. External
audio/video and social players have placeholders and external links. Previews
operate without external networking where enforceable, or use inert/download
fallbacks. Unsupported private loading never silently switches to the browser.

Keep the same `WEBAPP_EXTERNAL_CONTENT=tor_proxied|ask|off|browser_native` setting,
policy authority, consent vocabulary and permission storage. Do not introduce a
second conflicting switch or a compatibility/migration layer.

## Streaming external media through Tor

- Add authenticated streaming for validated public audio/video destinations,
  supporting Range requests, seeking, cancellation and appropriate response
  types. Reuse the image proxy's SSRF and credential-isolation requirements.
- Cover dependent resources: posters, subtitles, playlists, manifests, segments,
  redirects and encryption-key URLs where applicable. A privately loaded initial
  manifest must not direct subsequent browser requests to external servers.
- Only claim support for formats whose dependencies can be safely handled. Keep
  unsupported players/DRM/login-dependent media as placeholders or external links.
  Do not build a general rewriting proxy for arbitrary websites.
- Under `tor_proxied`, allow supported private playback; under `ask`, require
  approval before any external request. Under `off`, refuse retrieval even if a
  browser submits the endpoint directly. Preserve existing local playback.
- Report Tor latency or incompatibility without falling back to browser-native
  playback. Reuse endpoint safeguards rather than adding container-wide quotas.

## Runtime consent for browser-native interactive content

Extend the shared placeholder to offer direct in-app loading when supported:

- Show the destination/provider and a clear warning that this uses the user's
  browser connection, not the stack's Tor gateway. Do not infer that a browser
  is Tor Browser or that it provides network isolation.
- Offer load once, allow for this session, and revocable remembered permission.
  Scope by exact origin or a defined provider with documented dependencies, and
  distinguish browser-native grants from Tor-proxied grants.
- Keep `off` an unoverrideable deployment ceiling. `ask` requires consent before
  private or direct retrieval; `tor_proxied` requires consent for direct loading.
  `browser_native` explicitly permits automatic native resource loading while
  retaining unrelated authentication, script and sandbox protections.
- Integrate social embeds into the same policy rather than allowing a separate
  provider preference to bypass it. Display and revoke effective grants in one
  settings surface. Handle localhost and Funnel browser state explicitly; do
  not assume their independent origins share consent storage.

## Consent-scoped frames and generated previews

CSP cannot be relaxed by adding a policy after a click. Keep the main app
restricted, and load approved interactive content through a separately served,
sandboxed frame whose response policy reflects the authorized permission.

1. Design an authenticated consent and frame issuance flow. Validate session,
   origin/CSRF protections, content identity, approved dependencies and expiry.
   Keep approval authority in the trusted UI/backend, not model-generated HTML
   or preview postMessage handlers. Avoid reusable tokens in external URLs.
2. Keep parent CSP restrictive while allowing the same-origin wrapper. Scope
   the wrapper's response policy to the approved provider/origins, then preserve
   sandbox boundaries and prevent access to parent credentials or DOM. Avoid
   sharing the authenticated origin with executable untrusted content through
   an unsafe combination of script and same-origin permissions.
3. Audit social provider scripts, nested frames, redirects and subsidiary hosts.
   Approving a YouTube player must not silently grant arbitrary third-party
   access. If dependencies cannot be reasonably bounded, keep the external-link
   fallback or explain the broader grant before approval.
4. For generated HTML, inventory external dependencies where feasible. Prefer
   locally packaged libraries or safely retrieved passive assets. Unknown
   dependencies must not receive a wildcard network grant automatically.
5. Resolve WebRTC/STUN, scripted navigation, workers and resource hints for each
   supported browser before claiming network containment. If selective access
   cannot be enforced, preserve the inert/external fallback instead of enabling
   arbitrary scripts under an incomplete allowlist. A grant for browser-native
   execution must accurately describe its actual network authority.
6. Define revocation semantics: remove active frames/players and prevent new
   authorized loads. Already delivered executable content or completed remote
   requests cannot be recalled; do not imply revocation can undo them.

The permission is to load a particular class of external content, not to access
host/LAN services. Define and test local-destination handling; do not implicitly
turn public embed consent into permission to probe the user's private network.

## Implementation sequence and packaging

1. Requalify part 1's enforcement against the current pinned derived image.
2. Add streaming support for narrowly defined media formats, keeping all
   unsupported formats on the existing safe fallback.
3. Add the consent issuance/frame policy mechanism and a small set of qualified
   social providers. Expand provider support only with dependency coverage.
4. Add interactive generated previews where enforceable; retain safe fallbacks
   for unknown or overly broad requirements.
5. Extend the explicit Hermes patches and reproducible webapp build from part 1.
   Fail on upstream patch mismatches and update operator documentation and
   update inventory as needed. No topology changes are assumed; justify any
   necessary additions against the existing isolation boundaries.

## Qualification and acceptance

- Retain all part 1 no-unapproved-egress tests in the default policy. Adding a
  player or preview must not widen the main application's source permissions.
- Test each mode and permission lifetime, including saved provider grants,
  revocation during playback, logout, restart, and independent local/Funnel
  origins. Test forged grants, replay, cross-origin writes and untrusted
  messages; approval must not be obtainable by content itself.
- Observe actual browser and gateway traffic for media dependencies, seeking,
  cancellation, redirects, nested frames and rejected destinations. Use
  controlled fixtures without contacting live social accounts or trackers.
- Verify unsupported/failed proxying never silently becomes a direct browser
  request. Verify explicitly approved native requests use only the authority
  documented by the approval UI.
- Exercise authentication, sandbox/parent separation, SSRF protections and the
  retained host/VM/executor isolation checks. Check relevant WebRTC and scripted
  navigation behavior across the documented supported browser versions.
- Preserve deliberate external links and offline/local content. Run focused
  browser/media/security tests and appropriate repository checks without live
  Funnel enrollment or production wallet operations.

Completion means added functionality works within explicit permissions. It does
not require universal compatibility with arbitrary websites or executable HTML.
