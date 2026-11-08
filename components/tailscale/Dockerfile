# Official stable image inspected as Tailscale 1.104.4, Go 1.27.3.
FROM tailscale/tailscale@sha256:ed6480b33c6eb67c9cbd203ed42b9fb57e361986725b6856def71b7a3d9e276c
RUN apk add --no-cache python3
COPY components/tailscale/funnel.py /opt/funnel.py
ENTRYPOINT ["python3", "/opt/funnel.py"]
