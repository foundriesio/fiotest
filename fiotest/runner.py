import json
import logging
from os import execv, unlink
import subprocess
from threading import Thread
from time import sleep

from fiotest.spec import Reboot, Sequence, Test, TestSpec

log = logging.getLogger()


class SpecStopped(Exception):
    pass


class SpecRunner:
    reboot_state = "/var/lib/fiotest/reboot.state"

    def __init__(self, spec: TestSpec):
        self.spec = spec
        self.running = False
        self.thread = Thread(target=self.run)

    def start(self):
        self.running = True
        self.thread.start()

    def run(self):
        completed = 0
        try:
            with open(self.reboot_state) as f:
                data = json.load(f)
                completed = data["seq_idx"]
                log.warning(
                    "Detectected rebooted sequence, continuing after sequence %d",
                    completed,
                )
            unlink(self.reboot_state)
        except FileNotFoundError:
            pass  # This is the "normal" case - no reboot has occurred

        try:
            for i, seq in enumerate(self.spec.sequence):
                self._assert_running()
                if i < completed:
                    log.debug("Skipping seq %d", i)
                    continue
                log.info("Executing seq %d", i)
                if seq.reboot:
                    self._reboot(i, seq.reboot)
                else:
                    # run_tests recursively decrements seq.repeat.total
                    # we need to keep a copy of this value so that testing
                    # can be repeated
                    if seq.repeat:
                        total = seq.repeat.total
                    self._run_tests(seq)
                    if seq.repeat:
                        seq.repeat.total = total
        except SpecStopped:
            log.warning("Sequence has been stopped before completion")
        log.info("Testing complete")

    def stop(self):
        log.info("Stopping run")
        self.running = False

    def join(self):
        self.thread.join()

    def _assert_running(self):
        if not self.running:
            raise SpecStopped()

    def _reboot(self, seq_idx: int, reboot: Reboot):
        log.warning("rebooting!!!!")
        with open(self.reboot_state, "w") as f:
            state = {"seq_idx": seq_idx + 1}
            json.dump(state, f)
        execv(reboot.command[0], reboot.command)

    def _run_test(self, test: Test):
        args = ["/usr/local/bin/fio-test-wrap", test.name] + test.command
        with open("/tmp/tmp.log", "wb") as f:
            p = subprocess.Popen(args, stderr=f, stdout=f)
            while p.poll() is None:
                if not self.running:
                    log.info("Killing test")
                    p.kill()
                    return
                sleep(1)
            rc = p.wait()
            if rc != 0:
                log.error("Test exited with %d", rc)

    def _run_tests(self, seq: Sequence):
        if seq.tests:
            for test in seq.tests:
                self._assert_running()
                log.info("Executing test: %s", test.name)
                self._run_test(test)

        if seq.repeat and seq.repeat.total != 1:
            if seq.repeat.total > 0:
                seq.repeat.total -= 1
            self._assert_running()
            log.info("Repeating sequence in %d seconds", seq.repeat.delay_seconds)
            sleep(seq.repeat.delay_seconds)
            self._run_tests(seq)
