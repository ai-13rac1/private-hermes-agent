FROM alpine:3.24
RUN apk add --no-cache bash python3 py3-pip py3-yaml git curl openssh-server openssh-client nodejs npm tar coreutils \
    && addgroup -g 10000 runner \
    && adduser -D -u 10000 -G runner -s /bin/bash runner \
    && passwd -u runner \
    && mkdir -p /workspace /run/sshd \
    && chown runner:runner /workspace
COPY components/provisioning/bootstrap.py /opt/bootstrap.py
COPY components/executor/sshd_config /etc/ssh/sshd_config
WORKDIR /workspace
CMD ["/usr/sbin/sshd", "-D", "-e", "-f", "/etc/ssh/sshd_config"]
