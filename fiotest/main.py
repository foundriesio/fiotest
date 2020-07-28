import logging
import os
import sys
from threading import Timer

import yaml

from fiotest.callbacks import (
    AktualizrCallbackHandler,
    CallbackServer,
)
from fiotest.host import sudo_execute as host_sudo
from fiotest.runner import SpecRunner
from fiotest.spec import TestSpec

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger()

CBFILE = os.environ.get("CALLBACK_SCRIPT", "/var/sota/aklite-callback.sh")


class Coordinator(AktualizrCallbackHandler):
    def __init__(self, spec: TestSpec):
        self.timer = Timer(600, self._assert_callbacks)
        self.timer.start()
        self.callbacks_enabled = False
        self.runner = None
        self.spec = spec
        if os.path.exists(SpecRunner.reboot_state):
            self.runner = SpecRunner(self.spec)
            self.runner.start()

    def on_check_for_updates_pre(self, current_target: str):
        if not self.callbacks_enabled:
            log.info("fiotest receiving callbacks from aktualizr-lite")
            self.callbacks_enabled = True
            self.timer.cancel()

    def _assert_callbacks(self):
        if self.callbacks_enabled:
            return

        log.info(
            "aklite doesn't appear to be configured for fiotest callbacks. Restarting now!"
        )
        rc = host_sudo("systemctl restart aktualizr-lite")
        if rc != 0:
            log.error("Unable to restart aktualizr-lite")

    def on_install_pre(self, current_target: str):
        if self.runner:
            log.info("New target about to be installed, stopping testing")
            self.runner.stop()
            self.runner = None

    def on_install_post(self, current_target: str, status: str):
        if status == "OK":
            log.info("New target installed - kicking off testing")
            self.runner = SpecRunner(self.spec)
            self.runner.start()


def ensure_callbacks_configured():
    for x in ("aklite-callback.sh", "trigger-target-tests.sh"):
        script = "/var/sota/" + x
        with open(os.path.basename(script)) as fin:
            with open(script, "w") as f:
                f.write(fin.read())
                os.fchmod(f.fileno(), 0o755)

    cbtoml = "/etc/sota/conf.d/z-90-fiotest.toml"
    cur = ""
    new = (
        """[pacman]
callback_program = "%s"
"""
        % CBFILE
    )
    try:
        with open(cbtoml) as f:
            cur = f.read()
            if cur != new:
                log.info("Configuration of %s changing from %s -> %s", cbtoml, cur, new)
    except FileNotFoundError:
        log.info("Configuring aktualizr-lite callback with %s", cbtoml)
        log.info(
            "aktualizr-lite will be restarted in 10 minutes if callbacks aren't automatically detected"
        )

    with open(cbtoml, "w") as f:
        f.write(new)


def main(spec: TestSpec):
    log.info("Test Spec is: %r", spec)
    ensure_callbacks_configured()
    cb_server = CallbackServer(Coordinator(spec))
    cb_server.run_forever()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: %s <test-spec.yml>" % sys.argv[0])
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    main(TestSpec.parse_obj(data))
