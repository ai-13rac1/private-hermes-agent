FROM dockurr/tor:0.4.9.16@sha256:5b5c9e5036fff91bdf021ef225fdb0fc9ba4222425b9cbc1858a15681d220590
RUN apk add --no-cache python3 iptables iproute2 util-linux
COPY components/network/network.py components/network/tor-health.py /opt/
ENTRYPOINT ["python3", "/opt/network.py"]
