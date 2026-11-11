# Official v0.23.0, source 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19.
FROM nousresearch/hermes-agent@sha256:adb7890916de63245523492be8f68f9d2095fecbec4e2a6dab7960381f0fc002 AS upstream

FROM upstream AS webapp-build
COPY components/hermes/verify-build.mjs /tmp/verify-build.mjs
RUN node /tmp/verify-build.mjs
# Use the packaged npm CLI explicitly; do not install a second toolchain.
RUN npm_execpath="$(readlink -f /usr/local/bin/npm)" \
    node apps/desktop/scripts/build-webapp.mjs --deps-only
COPY components/hermes/ui/private-content.tsx /opt/hermes/apps/desktop/src/components/ui/private-content.tsx
COPY components/hermes/patches/ /tmp/private-hermes-patches/
RUN git apply --check /tmp/private-hermes-patches/*.patch && \
    git apply /tmp/private-hermes-patches/*.patch
# The inherited output is an overlay lower-layer directory; replacing it by
# rename fails EXDEV. Remove only this disposable build output before compiling.
RUN rm -rf apps/desktop/dist-webapp && \
    npm_execpath="$(readlink -f /usr/local/bin/npm)" \
    node apps/desktop/scripts/build-webapp.mjs --no-install

# Native browser session creation validates its agent-side cwd exists. This
# empty local directory is separate from the executor mount and contains no
# executor files; model terminal/code execution still uses SSH.
FROM upstream
RUN install -d -m 0755 -o 10000 -g 10000 /workspace
COPY --from=webapp-build /opt/hermes/hermes_bootstrap.py /opt/hermes/hermes_bootstrap.py
COPY --from=webapp-build /opt/hermes/hermes_cli/ /opt/hermes/hermes_cli/
COPY --from=webapp-build /opt/hermes/tools/registry.py /opt/hermes/tools/registry.py
COPY --from=webapp-build /opt/hermes/tools/browser_use_cli.py /opt/hermes/tools/browser_use_cli.py
COPY --from=webapp-build /opt/hermes/tools/browser_session.py /opt/hermes/tools/browser_session.py
COPY --from=webapp-build /opt/hermes/tools/browser_session_lifecycle.py /opt/hermes/tools/browser_session_lifecycle.py
COPY --from=webapp-build /opt/hermes/tools/browser_session_sandbox.py /opt/hermes/tools/browser_session_sandbox.py
COPY --from=webapp-build /opt/hermes/tools/environments/ssh.py /opt/hermes/tools/environments/ssh.py
COPY --from=webapp-build /opt/hermes/agent/inline_tool_executors.py /opt/hermes/agent/inline_tool_executors.py
COPY --from=webapp-build /opt/hermes/agent/context_references.py /opt/hermes/agent/context_references.py
COPY --from=webapp-build /opt/hermes/tools/bot_desktop/ /opt/hermes/tools/bot_desktop/
COPY --from=webapp-build /opt/hermes/tools/computer_use/ /opt/hermes/tools/computer_use/
COPY --from=webapp-build /opt/hermes/tui_gateway/methods_display.py /opt/hermes/tui_gateway/methods_display.py
COPY --from=webapp-build /opt/hermes/hermes_cli/web_routers/display.py /opt/hermes/hermes_cli/web_routers/display.py
COPY --from=webapp-build /opt/hermes/apps/desktop/dist-webapp/ /opt/hermes/apps/desktop/dist-webapp/
COPY components/hermes/external_content.py /opt/hermes/hermes_cli/private_external_content.py
COPY components/hermes/public_images.py /opt/hermes/hermes_cli/private_public_images.py
COPY components/hermes/browser_policy.py /opt/hermes/hermes_cli/private_browser_policy.py
COPY components/hermes/computer_use.py /opt/hermes/hermes_cli/private_computer_use.py
COPY components/hermes/browser_use.py /opt/hermes/hermes_cli/private_browser_use.py
ENV HERMES_WEBAPP_DIST=/opt/hermes/apps/desktop/dist-webapp
