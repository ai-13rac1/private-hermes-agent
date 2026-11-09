# HAProxy 3.4 LTS; digest reviewed with the ingress implementation.
FROM haproxy:3.4-alpine@sha256:5312d37032c079c4937d45ef63758852434351f3b425a3703521fd999837abcf
USER root
RUN apk add --no-cache python3 iptables iproute2 util-linux
COPY components/webapp/proxy-start.py /usr/local/bin/proxy-start.py
ENTRYPOINT ["python3", "/usr/local/bin/proxy-start.py"]
CMD ["-W", "-db", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
