"""Fiotest environment module."""

import os


_TRUES = ("1", "true", "yes", "on")


def _get_bools(env_var: str, default: bool) -> bool:
    """Get boolean value from environment variable."""
    if env_var not in os.environ:
        return default
    return os.environ.get(env_var).lower() in _TRUES


def docker_host() -> str:
    """Get the docker host IP address."""
    return os.environ.get("FIO_TEST_DOCKER_HOST", "172.17.0.1")


def debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return _get_bools("FIO_TEST_DEBUG", False)


def dry_run() -> bool:
    """Check if dry run mode is enabled."""
    return _get_bools("FIO_TEST_DRYRUN", os.environ.get("DRYRUN"))
