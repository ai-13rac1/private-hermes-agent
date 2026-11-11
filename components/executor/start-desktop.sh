#!/bin/sh
set -eu
# /run and /tmp are fresh tmpfs mounts, hiding image-seeded directories.
mkdir -p /run/sshd /tmp/.X11-unix
chmod 0755 /run/sshd
chmod 1777 /tmp/.X11-unix
# Create the user-owned bus/runtime directory without granting sshd CHOWN.
setpriv --reuid=10000 --regid=10000 --clear-groups \
    sh -c 'mkdir -p /tmp/hermes-runtime && chmod 0700 /tmp/hermes-runtime'
exec /usr/sbin/sshd -D -e -f /etc/ssh/sshd_config
