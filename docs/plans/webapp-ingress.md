# Authenticated webapp: localhost and optional Tailscale Funnel

Status: implemented and locally qualified. Live Tailscale
enrollment and public-path qualification require operator configuration.
See `docs/webapp.md` for the implementation workflow.

## Objective and scope

Expose the Hermes webapp by default to the operator on host loopback and, when explicitly
enabled, through Tailscale Funnel. Preserve the existing SSH executor, host/VM
isolation, transparent Tor egress, direct teep inference, and selected MCP grants.

The initial authentication mechanism is Hermes's native username/password
provider. OIDC is not intrinsically stronger and is not a prerequisite. Funnel
is a public HTTPS endpoint: visitors need neither tailnet membership nor a
Tailscale account. A strong password does not eliminate authentication-bypass,
pre-authentication, session, or availability risks. Upstream recommends its
password provider for trusted networks/VPN use rather than public exposure;
this deployment must document that distinction without claiming Funnel removes it.

Onion ingress, OIDC/MFA, capability reduction, read-only configuration, and
resource/storage limits are outside this implementation. Do not bundle them
into this change or silently restrict ordinary webapp features.

## Authority of the webapp

Treat an authenticated webapp user as a trusted administrator of the agent
container, not as an untrusted user confined to the SSH executor. Audit the
browser terminal, file browser, settings, and plugin/MCP administration surfaces
in the pinned image. The browser terminal may run under the gateway even when
model-generated shell/Python tools use SSH.

Preserve the existing execution boundary for model-generated code. Document
the distinct authority of the browser UI prominently. Moving or restricting
the interactive browser terminal is a separate explicit feature decision;
hiding a button does not establish a backend security boundary.

## Intended topology

```text
host 127.0.0.1 -----------------------------------+
                                                   v
public HTTPS -> optional Funnel -----------------> webapp proxy -> Hermes :9120
```

- Add an isolated internal webapp backend network to `agent-net`. Permit new
  inbound connections only from the proxy's exact IP to TCP 9120. Keep the
  executor off every ingress network and deny its access to the webapp.
- Give the proxy no general outbound network access. Its configuration has one fixed upstream:
  Hermes's webapp address and port. It must not become a general forward proxy.
- Publish the proxy directly on host loopback and give it a default-deny
  firewall. Its only permitted new outbound connection is to the Hermes backend;
  local and Funnel ingress use separate interfaces/listeners. Install the rules
  before serving, then switch to an unprivileged UID and irreversibly drop all
  process capabilities. Keep the agent off the host-publication network.
- Run the optional Tailscale component with userspace networking, its own
  direct uplink, persistent node state, and no engine socket or host networking.
  Its proxy target is the exact isolated HAProxy address and port. Keep its credentials out of the
  agent and executor, and keep the agent off its uplink.
- Publish neither the underlying gateway API nor the separate dashboard. Keep
  Tor egress and teep routing unchanged.

## Configuration and activation

1. Introduce strictly parsed, documented settings in the root `.env` and
   `.env.example` for localhost binding/port, Funnel
   enablement, and Tailscale node identity. Keep image pins in `compose.yaml`
   and component Dockerfiles. Pass each service only its selected settings.
2. Integrate optional Compose service activation with the Make workflow. Invalid
   booleans or inconsistent settings must fail before startup. With Funnel
   disabled, run no Tailscale service and require no Tailscale credentials.
3. Store webapp authentication and Tailscale secrets outside Git, with scoped
   mounts/environment injection and restrictive file permissions. Use the root
   `.env` for supplied deployment settings, `config/` for editable mounted
   configuration, and private persistent storage for generated identities.
   Keep container implementation files under `components/`. Generate a
   strong unique password and persistent random session-signing secret through
   an explicit operator workflow; never log credentials or pass them to code
   execution. Preserve credentials across ordinary restarts.
4. Enable native webapp authentication for both ingress paths. Do not rely on
   a loopback authentication exemption, Funnel, or an unadvertised hostname.
   Missing or invalid authentication configuration must not produce an
   unauthenticated listener.
5. Require explicit Funnel enablement and legitimate Tailscale enrollment.
   Ordinary builds, local startup, and automated tests must not enroll a node,
   change tailnet policy, or enable public Funnel exposure.
6. Make disabling Funnel remove its active public forwarding configuration,
   including any configuration persisted in Tailscale state. Preserve node
   identity unless the operator intentionally resets it.

## Host, origin, and session handling

Qualify the exact pinned Hermes image before choosing final configuration:

- Qualified design: non-loopback webapp bind on the isolated backend,
  password authentication required, and no fixed `webapp.public_url`, allowing
  each browser origin to remain itself. Browser tests against the pinned image
  verify simultaneous local HTTP and simulated external HTTPS origins.
- Enforce exact configured external hosts at ingress. Reject unexpected hosts,
  including DNS-rebinding shapes. Preserve the real external host; do not
  rewrite all origins to an internal container name.
- Strip incoming `Forwarded` and `X-Forwarded-*` values, then construct trusted
  values according to the ingress path. The localhost path uses its actual
  scheme; Funnel's externally HTTPS path must remain HTTPS in Hermes's view.
- Trust only the proxy's exact backend IP in Hermes. Do not use wildcard proxy
  trust or widen CORS/CSRF/WebSocket origin policies to work around failures.
- Check cookie names, `Secure`, `HttpOnly`, paths, and login/logout independently
  on each hostname. Do not assume localhost and Funnel share a session.
- Inspect native password throttling and how client addresses traverse Funnel
  and the proxy. Verify what address is actually available before configuring
  trust or reporting per-client protection. Do not accept spoofable headers.
- Determine actual session expiry, logout, and password/signing-secret rotation
  behavior. Do not infer full token revocation from removal of a browser cookie.

If simultaneous origins do not work safely with upstream behavior, document
the specific incompatibility and select a supported design before exposure.
Do not disable authentication or origin protections to force compatibility.

## Implementation sequence

1. Audit the pinned image's webapp startup, password provider, public paths,
   origin controls, browser terminal authority, and required streaming routes.
2. Implement localhost ingress and authentication first, retaining the official
   image initialization and the current configuration maintenance workflow.
3. Add local tests for the HTTPS proxy path and exact-host enforcement, without
   creating a public endpoint. Qualify browser login and streaming behavior.
4. Add the optional Funnel service, persistent configuration, enable/disable
   workflow, and secret handling. Keep local access usable when Funnel is off
   or unavailable.
5. Run the existing execution/network suite and new ingress qualification.
   Document configuration, initial login, credential rotation, diagnostics, and
   rollback. Commit the reviewable implementation after local checks pass.
6. Qualify a real Funnel with the operator's configured node. Report that live
   external access remains unverified until enrollment and public-path tests
   actually succeed; a simulated HTTPS proxy test is not equivalent.

## Qualification and acceptance

- Check fresh setup, repeated initialization, ordinary restart, and clean
  shutdown. Refuse exposure when authentication is missing.
- Test unauthenticated page, API, download/upload, and WebSocket requests. A
  successful login-page redirect alone is insufficient evidence of protection.
- Test successful and failed login, native throttling, session persistence,
  logout, and credential rotation without leaking secret values into logs.
- Exercise actual browser cookie/origin behavior on localhost and an HTTPS
  ingress. Cover cross-origin writes, forged forwarding headers, unexpected
  hosts, and authenticated/unauthenticated WebSocket handshakes.
- Exercise streamed responses and representative browser-terminal/file
  operations, recording where those operations execute.
- Confirm the executor still cannot reach host/VM addresses, agent APIs, teep,
  MCP services, or the new webapp. Retain all existing routing regressions.
- Confirm Funnel is public when enabled, not tailnet-authenticated; verify
  actual external login, streaming, and WebSockets after real enrollment.
- Disable Funnel and demonstrate that public access stops, while localhost
  remains available and the existing stack continues to operate.

Run `make check`, `make test`, and the focused ingress/browser checks. Preserve
state volumes during rollback; restore the prior repository revision and config
without changing executor privileges or deleting credentials, workspaces,
conversations, or Tor state.

## Implementation and local qualification record

Local ingress lives in the main `compose.yaml`; only `compose.funnel.yaml` is
optional and selected from `.env` by `scripts/stack.py`. `make init` creates
missing credentials and renders HAProxy configuration. The existing networkless
bootstrap installs native webapp settings, replacing the separate setup service. Operator instructions and the
remaining live-Funnel qualification are in `docs/webapp.md`.

The pinned Hermes image supports the two origins without a fixed public URL.
Its browser terminal executes in the agent container. Its workspace file API
uses the SSH backend when the canonical `terminal.ssh_*` configuration fields are
set; process environment alone does not configure that API. The template and
bootstrap now write those fields explicitly.

The disposable ingress suite passed real browser login/logout on HTTP and HTTPS,
cookie flags, native throttling, forbidden origins and hosts, forwarding-header
spoofing, authenticated and unauthenticated WebSockets, terminal streaming,
SSH workspace file access, staged upload/download, session persistence across
restart, password/signing-secret rotation, executor isolation, and ingress
shutdown. No real Tailscale service was started or enrolled. Unit checks also
exercise disabled Funnel startup, DNS-name mismatch, reset/shutdown failures,
and deployment reconfiguration. The pinned Tailscale binary and containerboot
entrypoint were checked offline.

`make check` passed all 17 unit checks, Compose validation and Python compilation.
`make test` also passed the existing Tor/direct-inference routing, host/VM and
rpcbind denial, SSH terminal/code execution, selected MCP streaming, and Tor
outage regressions. `make webapp-test` passed the browser qualification above.

Live enrollment, public login/streaming/WebSockets, and external verification
that disabling Funnel stops access remain pending operator configuration. The
TLS fixture does not establish those results.

The ingress topology was subsequently consolidated: HAProxy now performs host
publication and accepts Funnel directly, replacing both TCP forwarding services.
Its startup firewall denies all new outbound connections except the fixed Hermes
backend, then the process drops UID and all capabilities before serving. The
qualification suite checks those process credentials and network restrictions,
including listener separation and a proxy restart.

Local access is now always part of the base Compose deployment, with no separate
enable flag. Initialization preserves existing credentials, and bootstrap refuses
invalid authentication input before replacing the native profile configuration.
Funnel enrollment remains explicit; no wallet initialization or funding occurs
in `make init` or bootstrap.
