"""Qualify desktop tool discovery against the configured SSH executor."""
import logging
import subprocess

logger = logging.getLogger(__name__)


def available():
    from tools.bot_desktop import placement, sandbox_host
    from tools.environments import streams
    where = placement.resolve()
    if where.where != placement.TERMINAL:
        logger.info("Computer use unavailable: %s", where.reason)
        return False
    try:
        env = placement.terminal_environment(create=True)
        if env is None:
            raise RuntimeError("SSH executor connection is unavailable")
        missing = sandbox_host.missing_binaries(env)
        driver = streams.run_in(env, ["sh", "-c", "command -v cua-driver"], timeout=20)
        if driver.returncode:
            missing.append("cua-driver")
        if missing:
            raise RuntimeError("executor image lacks " + ", ".join(missing) +
                               "; rebuild with COMPUTER_USE_ENABLED=true")
    except (OSError, RuntimeError, TimeoutError, subprocess.SubprocessError) as error:
        logger.info("Computer use unavailable: %s", error)
        return False
    return True
