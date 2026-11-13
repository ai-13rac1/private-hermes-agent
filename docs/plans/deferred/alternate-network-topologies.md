# Alternate network topologies

Status: deferred; retained for reference, not scheduled implementation work.
Extraction baseline: branch `main`, commit `9b536d0aefe53776f33eacb8366c8b639f1874ed`.
This was extracted from the completed capability-reduction work; the implemented
restricted-privilege result is documented in
[architecture](../../architecture.md#hermes-capability-boundary) and
[development](../../development.md#qualification-and-maintenance).
Follow the [planning workflow](../../planning-workflow.md) before reactivation.

## Why this is deferred

The topology investigation was originally motivated by a presumed rootless Podman
compatibility requirement: GRE was thought to require explicit host module loading
that would be unavailable. The supported setup instead creates GRE links through
`ip link add ... type gre` using netlink, which allows the kernel to load `ip_gre`
on demand. See [the network implementation](../../../components/network/network.py)
and [qualified engine behavior](../../development.md#qualification-and-maintenance).
This does not remove the requirement for GRE support in the host kernel or qualify
untested hosts.

With GRE working on both qualified engines, we no longer expect compatibility or
significant security gains from replacing the current topology. That is the current
prioritization judgment, not a completed comparative runtime evaluation. Retain
separate Hermes, executor and Tor namespaces, transparent Tor routing, independent
endpoint/router firewalls and exact internal grants. Capability reduction can
proceed independently with that topology unchanged.

No alternate topology has been selected, implemented or qualified. No experiments,
new services, proxy configuration or namespace-access machinery are required by
this deferred document. The concrete next action is to revisit it only if a
reproduced supported-platform blocker or specific security requirement demonstrates
a benefit the existing topology cannot reasonably provide. Reassess the then-current
pins and evidence, select a bounded investigation and revise the implementation
phases before seeking independent design acceptance; do not revive a mandatory
three-way implementation exercise.

## Retained investigation outline (inactive)

If a concrete need reopens this work, compare these candidates against the
then-current behavior, recording evidence and unresolved questions:

| Candidate | Required design detail and evidence |
| --- | --- |
| Retain GRE and separate Hermes, executor and Tor namespaces | Establish which startup and steady-state privileges can be reduced without changing topology. Record the kernel dependency, current fail-closed behavior and maintenance cost. |
| Share Hermes and Tor networking; retain a separate executor with an explicit HTTP proxy | Specify the proxy owner, exact executor grant, HTTP/CONNECT transport through Tor and remote DNS handling. Trace Tor-UID exemption risks, shared loopback/listeners and internal grants. Specify enforcement and checks demonstrating the proxy cannot reach prohibited host/VM/private or agent-only destinations on the executor's behalf. |
| Retain separate namespaces and connect them with veth pairs | Specify who creates and places each endpoint, how it obtains namespace access, actual capability requirements, rootless Podman feasibility and Docker Desktop VM implications. Trace link recreation, namespace destruction, firewall ordering and startup failure cleanup without a generic recovery service. |

For each candidate, identify affected Compose services, images, helpers,
configuration, maintenance consumers, tests and permanent guides. Explain setup
and steady-state authority, added/removed dependencies and components, and native
component guarantees. Record shared versus engine-specific requirements, including
any additional host authority a candidate would need; do not assume container
`NET_ADMIN` grants access to a sibling or host-owned namespace. Assess gains and
risks relative to retaining GRE, including independent enforcement, Tor outage behavior, local service availability,
restart/recreation, shutdown and state preservation. Include shared port binding
and abstract Unix socket exposure where namespaces are shared.

Assess representative executor workloads through the real SSH entry point:
terminal/Python execution, curl, Git over HTTPS, package downloads and clients
using direct sockets or ignoring proxy variables. Distinguish supported behavior
from proposed compatibility losses. Environment variables are client configuration;
the network firewall must deny direct bypass. Check destination policy for literal
addresses, DNS answers and redirects, plus Docker embedded DNS, TCP/UDP rpcbind,
non-loopback IPv6 and unsupported UDP. Include permitted-path controls so an
unavailable target cannot masquerade as successful isolation.

Use narrow disposable experiments only where an uncertainty could change the
decision. Name the question, candidate, supported target and acceptance evidence
before running each experiment. Leave production topology and private state
untouched; no full implementation or exhaustive prototype of every candidate is
required. The workload and security checks above define the comparison and future
implementation acceptance; run them during investigation only as needed to resolve a material
design uncertainty. Full runtime qualification belongs to the selected approach's
implementation phases. Reference repositories supply techniques to assess against exact pins:
`torproxy` at `2a538fd2ad8a09caa7282dffc7d528d6e59d1db1` and `rootless-hermes`
at `4bda68620b261ab68f3ce06c7cdbdc015308917a`. The latter runs container UID 0
under a rootless engine and replaces startup; it does not qualify a capability-free
Hermes lifecycle or this stack's network policy.

## Boundaries and acceptance if reopened

The separate Tor namespace and independent endpoint/router firewalls are the
baseline. Sharing Hermes and Tor networking deliberately changes that boundary.
Identify every weakened property and compensating mechanism; independent review
alone does not authorize accepting a weaker trust boundary. Obtain explicit
operator acceptance and reconcile governing instructions and maintained
architecture before implementing such a change. Preserve host/VM denial,
Tor-only public egress, executor separation and wallet/socket isolation. Any
proposed host grant must name its destination and port and requires separate
authorization.

Keep Make workflows, state identities, offline maintenance and authenticated
ingress intact. Do not replace native supervision or add a privilege broker,
generic recovery engine, engine socket, host networking, privileged application
container or host privilege helper. A rootless container capability does not grant
access to a sibling or host-owned namespace.

Any selected design needs coherent phases covering affected consumers, permanent
guides, rollback and allowed/forbidden paths on both engines, including dependency
failure, restart/recreation and shutdown. Use fresh independent design and final
reviews under the planning workflow. Until reactivated, none of these investigation
or implementation gates blocks capability reduction.
