import json
import logging
import requests
import os
import subprocess
from threading import Thread
from time import sleep

import netifaces

from fiotest.api import API
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
        self.api = API("/var/sota", False)

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
            os.unlink(self.reboot_state)
            self.api.complete_test(data["test_id"], {})
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
        test_id = self.api.start_test("reboot")
        with open(self.reboot_state, "w") as f:
            state = {"seq_idx": seq_idx + 1, "test_id": test_id}
            json.dump(state, f)
        os.execv(reboot.command[0], reboot.command)

    def _prepare_context(self, context: dict):
        return_dict = {}
        if "url" in context.keys():
            context_dict = {}
            if os.path.exists("/var/sota/current-target"):
                context_dict = API.file_variables("/var/sota/", "current-target")
            if os.path.exists("/var/etc/os-release"):
                context_dict.update(API.file_variables("/var/etc/", "os-release"))
            target_url = context["url"]
            try:
                target_url = target_url.format(**context_dict)
            except KeyError:
                # ignore any missing keys
                pass
            log.info(f"Retrieving context from {target_url}")
            env_response = requests.get(target_url)
            if env_response.status_code == 200:
                return_dict = env_response.json()
        else:
            return_dict = context
        return return_dict

    def _run_test(self, test: Test):
        environment = os.environ.copy()
        if test.context:
            environment.update(self._prepare_context(test.context))
        host_ip = netifaces.gateways()["default"][netifaces.AF_INET][0]
        args = ["/usr/local/bin/fio-test-wrap", test.name]
        if test.on_host:
            args.extend(
                [
                    "sshpass",
                    "-pfio",
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking no",
                    "fio@" + host_ip,
                ]
            )
            # pass environment to host
            # this only works if PermitUserEnvironment is enabled
            # on host
            with open("~/.ssh/environment", "w") as sshfile:
                for env_name, env_value in environment.items():
                    sshfile.write(f"{env_name}={env_value}\n")
        args.extend(test.command)
        with open("/tmp/tmp.log", "wb") as f:
            p = subprocess.Popen(args, stderr=f, stdout=f, env=environment)
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
