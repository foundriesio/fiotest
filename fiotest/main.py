import logging
import os
import sys

import yaml

from fiotest.callbacks import (
    AktualizrCallbackHandler,
    CallbackServer,
)
from fiotest.host import execute as host_execute
from fiotest.runner import SpecRunner
from fiotest.spec import TestSpec

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger()

CBFILE = os.environ.get(
    "CALLBACK_SCRIPT", "/var/sota/compose/fiotest/aklite-callback.sh"
)


class Coordinator(AktualizrCallbackHandler):
    def __init__(self, spec: TestSpec):
        self.runner = None
        self.spec = spec
        if os.path.exists(SpecRunner.reboot_state):
            self.runner = SpecRunner(self.spec)
            self.runner.start()

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
    cbtoml = "/etc/sota/conf.d/z-90-fiotest.toml"
    if not os.path.exists(cbtoml):
        log.info("Configuring aktualizr-lite callback...")
        with open(cbtoml, "w") as f:
            f.write("[pacman]\n")
            f.write('callback_program = "%s"\n' % CBFILE)
        host_execute("sudo systemctl restart aktualizr-lite")


def main(spec: TestSpec):
    ensure_callbacks_configured()
    cb_server = CallbackServer(Coordinator(spec))
    cb_server.run_forever()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: %s <test-spec.yml>" % sys.argv[0])
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    main(TestSpec.parse_obj(data))
