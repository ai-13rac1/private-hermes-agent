# Updates, plugins, and privacy defaults

The stack manages Hermes, Tor, HAProxy and Tailscale through image digest pins,
and teep/x402_treazury through source commits. Operator preferences in `.env`
do not select image versions. User plugins use Hermes's native management and
persistent profile storage.

## Check stack versions

With the stack running:

```sh
make check-updates
python3 scripts/check-updates.py --json
```

Requests run as UID 10000 inside Hermes's existing Tor-routed namespace. They
fetch public Docker Hub manifests and GitHub commit metadata with anonymous,
GET-only requests. Provider keys and stored Docker registry credentials are not
used; public registry pull tokens stay anonymous and in memory.
The checker reads the repository pins and reports:

- `matches`: the advertised artifact matches the pin, including a pinned
  platform manifest present in an advertised multi-platform index.
- `different`: the configured image channel or default source branch differs.
  This is a review signal, not proof of a newer or compatible release.
- `error`: metadata could not be checked, including anonymous rate limits.
  The command exits nonzero and does not report the component as current.

Hermes/Tor use their `latest` image channels, Tailscale uses `stable`, and
HAProxy stays on the pinned reference's version channel. Unpinned build-base
tags are listed separately: there is no recorded digest to compare for those.
The command changes no pins, installs no packages, and pulls no image layers.
Checks are operator-invoked; plugin notifications have their own cadence below.

## Apply stack updates

Review updated wrapper repository pins and upstream release information, then:

```sh
make build
make down
make up
```

Building first keeps the existing deployment available during the build.
`make down` waits for graceful financial shutdown and preserves named volumes
and bind data. `make up` reapplies offline setup and verifies research readiness.
Back up configuration, bind data, and the Hermes/treasury named volumes before
applying changes; see [backup scope](configuration.md#backup-scope).

The official Hermes image refuses in-place core updates. Its native passive
core version check currently reports an image-managed install as unsupported;
the stack checker supplies the useful version comparison. Changes to the
treasury build or configuration invalidate its preparation fingerprint, so
the workflow may require explicit `make x402_treazury-prepare` before reconnecting
research tools. Review native funding policy before that operation.

## Manage persistent user plugins

```sh
make plugins
python3 scripts/plugins.py list
python3 scripts/plugins.py install OWNER/REPOSITORY
python3 scripts/plugins.py update PLUGIN_NAME
python3 scripts/plugins.py disable PLUGIN_NAME
```

The wrapper executes the native Hermes CLI as UID/GID 10000 in the running
agent's Tor namespace. Interactive terminals retain native dependency and
capability consent prompts. For deliberate non-interactive dependency consent,
the native installer accepts `--enable --yes-deps`; the wrapper does not add
consent, scan bypasses, or force flags automatically.

Plugin code is stored under `/opt/data/plugins`. Enablement, install provenance,
and prepared dependency environments under `/opt/data/installs/` share the
existing `hermes-data` volume. They survive container recreation and ordinary
`make down`. Native plugin installation prepares Python environments in profile
storage, rather than requiring edits to the image's Python environment. Some
plugins also require system binaries or external services; those requirements
still need component-specific deployment work.

Plugin update checks run every 24 hours; automatic application is disabled.
Catalog updates follow native reviewed pins and consent checks; custom Git
sources use their native update rules. Apply updates explicitly and follow the
native interface's reload/restart guidance.

Bundled plugins remain part of the pinned Hermes image. Optional standalone
add-ons start disabled (`plugins.enabled: []`); backend/platform registrations
are selected through their normal configuration. A matching user plugin can
override a bundled plugin where its native discovery rules support that
override. Keep overrides intentional instead of covering the entire bundled
directory with persistent old code. Plugins execute with agent privileges;
they are outside the SSH executor sandbox and have no treasury wallet mount.

`make plugins-test` uses a disposable project to install and update a harmless
plugin with a locally generated wheel dependency, then checks loading after
container recreation. It uses no inference or paid research calls.

## Privacy defaults

Shared-metrics collection and uploads are explicitly disabled, with the current
consent offer recorded as declined. OTLP diagnostics export and computer-use
telemetry are off. Browser telemetry environment overrides are applied to the
agent and executor. Native update checks and plugin notifications remain enabled
independently of those settings.

HAProxy adds a CSP restricting fonts/styles to local resources and inline styles;
browsers intersect it with Hermes's own CSP. Google Fonts requests are blocked
for both local and Funnel ingress, and bundled/system font fallbacks remain
available. This does not block functional model catalogs, tool downloads, or
content the operator deliberately accesses. Those agent-side requests retain
the existing Tor route. Profile settings are writable; these are explicit
defaults, not immutable enforcement against arbitrary plugin or agent code.
