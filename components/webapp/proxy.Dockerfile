# HAProxy 3.4 LTS; digest reviewed with the ingress implementation.
FROM haproxy:3.4-alpine@sha256:5312d37032c079c4937d45ef63758852434351f3b425a3703521fd999837abcf
USER 10005:10005
ENTRYPOINT ["haproxy"]
CMD ["-W", "-db", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
