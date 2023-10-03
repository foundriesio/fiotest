import json
import logging
import os
import requests
import sys
from typing import Optional

from fiotest.gateway_client import DeviceGatewayClient

log = logging.getLogger()


def status(msg: str, prefix: str = "== "):
    """Print a commonly formatted status message to stdout.
       It also ensures the buffer is flushed and written immediately"""
    sys.stdout.buffer.write(prefix.encode())
    sys.stdout.buffer.write(b" ")
    sys.stdout.buffer.write(msg.encode())
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


class API:
    def __init__(self, sota_dir: str, dryrun: bool):
        self.dryrun = dryrun

        self.url = self.test_url(sota_dir)
        status("Test URL: " + self.url)

        self.ca = os.path.join(sota_dir, "root.crt")
        self.cert = (
            os.path.join(sota_dir, "client.pem"),
            os.path.join(sota_dir, "pkey.pem"),
        )
        self.gateway = DeviceGatewayClient(sota_dir)
        self.sota_dir = sota_dir

    @property
    def headers(self):
        cur_target = self.target_name(self.sota_dir)
        return {"x-ats-target": cur_target}

    def start_test(self, name: str) -> str:
        data = {"name": name}
        if not self.dryrun:
            r = self.gateway.post(self.url, data, self.headers)
            if r.status_code != 201:
                sys.exit("Unable to start test: HTTP_%d: %s" % (r.status_code, r.text))
            return r.text.strip()
        return "DRYRUN"

    def _upload_item(self, artifacts_dir, artifact, urldata):
        path = os.path.join(artifacts_dir, artifact)
        headers = {"Content-Type": urldata["content-type"]}

        try:
            if urldata["url"].startswith(self.url):
                r = self.gateway.put_file(urldata["url"], path, headers=headers)
            else:
                with open(path, "rb") as f:
                    r = requests.put(urldata["url"], data=f, headers=headers,)

            if r.status_code not in (200, 201):
                status(
                    "Unable to upload %s to %s - HTTP_%d\n%s"
                    % (artifact, r.url, r.status_code, r.text)
                )
        except Exception as e:
            status("Unexpected error for %s: %s" % (artifact, str(e)))

    def complete_test(
        self, test_id: str, data: dict, artifacts_dir: Optional[str] = None
    ):
        if artifacts_dir:
            artifacts = os.listdir(artifacts_dir)
            if artifacts:
                data["artifacts"] = artifacts
        if self.dryrun:
            print(json.dumps(data, indent=2))
        else:
            r = self.gateway.put(self.url + "/" + test_id, data, self.headers)
            if r.status_code != 200:
                sys.exit(
                    "Unable to complete test: HTTP_%d: %s" % (r.status_code, r.text)
                )
            for artifact, urldata in json.loads(r.text).items():
                status("Uploading " + artifact)
                self._upload_item(artifacts_dir, artifact, urldata)

    @staticmethod
    def target_name(sota_dir: str) -> str:
        try:
            with open(os.path.join(sota_dir, "current-target")) as f:
                for line in f:
                    if line.startswith("TARGET_NAME"):
                        k, v = line.split("=")
                        return v.replace('"', "").strip()  # remove spaces and quotes
        except FileNotFoundError:
            pass  # ignore the error and exit
        sys.exit("Unable to find current target")

    @staticmethod
    def test_url(sota_dir: str) -> str:
        try:
            with open(os.path.join(sota_dir, "sota.toml")) as f:
                for line in f:
                    if line.startswith("server ="):
                        k, v = line.split("=")
                        v = v.replace('"', "").strip()  # remove spaces and quotes
                        return v + "/tests"
        except FileNotFoundError:
            pass  # ignore the error and exit
        sys.exit("Unable to find server url")

    @staticmethod
    def file_variables(sota_dir: str, file_name: str) -> dict:
        ret_dict = {}
        try:
            with open(os.path.join(sota_dir, file_name)) as f:
                for line in f:
                    k, v = line.split("=")
                    v = v.replace('"', "").strip()  # remove spaces and quotes
                    ret_dict.update({k: v})
        except FileNotFoundError:
            log.warning(f"File {file_name} not found in {sota_dir}")
            pass
        return ret_dict
