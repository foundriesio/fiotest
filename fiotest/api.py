import json
import os
import requests
import sys
from time import sleep


def status(msg: str, prefix: str = "== "):
    """Print a commonly formatted status message to stdout.
       It also ensures the buffer is flushed and written immediately"""
    sys.stdout.buffer.write(prefix.encode())
    sys.stdout.buffer.write(b" ")
    sys.stdout.buffer.write(msg.encode())
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _requests_op(op, *args, **kwargs):
    """A retriable requests helper."""
    for i in (1, 2, 4, 8, 16):
        r = op(*args, **kwargs)
        if r.status_code in (200, 201):
            break
        else:
            status("ERROR with %s - HTTP_%d: %s" % (r.url, r.status_code, r.text))
            sleep(i)
    return r


def post(*args, **kwargs):
    return _requests_op(requests.post, *args, **kwargs)


def put(*args, **kwargs):
    return _requests_op(requests.put, *args, **kwargs)


class API:
    def __init__(self, sota_dir: str, dryrun: bool):
        self.dryrun = dryrun

        cur_target = self.target_name(sota_dir)
        self.url = self.test_url(sota_dir)
        status("Test URL: " + self.url)

        self.ca = os.path.join(sota_dir, "root.crt")
        self.cert = (
            os.path.join(sota_dir, "client.pem"),
            os.path.join(sota_dir, "pkey.pem"),
        )
        self.headers = {"x-ats-target": cur_target}

    def start_test(self, name: str) -> str:
        data = {"name": name}
        if not self.dryrun:
            r = post(
                self.url,
                json=data,
                headers=self.headers,
                verify=self.ca,
                cert=self.cert,
            )
            if r.status_code != 201:
                sys.exit("Unable to start test: HTTP_%d: %s" % (r.status_code, r.text))
            return r.text.strip()
        return "DRYRUN"

    def _upload_item(self, artifacts_dir, artifact, urldata):
        with open(os.path.join(artifacts_dir, artifact), "rb") as f:
            try:
                headers = {"Content-Type": urldata["content-type"]}
                r = requests.put(
                    urldata["url"],
                    verify=self.ca,
                    cert=self.cert,
                    data=f,
                    headers=headers,
                )
                if r.status_code not in (200, 201):
                    status(
                        "Unable to upload %s to %s - HTTP_%d\n%s"
                        % (artifact, r.url, r.status_code, r.text)
                    )
            except Exception as e:
                status("Unexpected error for %s: %s" % (artifact, str(e)))

    def complete_test(self, test_id: str, data: dict, artifacts_dir: str):
        artifacts = os.listdir(artifacts_dir)
        if artifacts:
            data["artifacts"] = artifacts
        if self.dryrun:
            print(json.dumps(data, indent=2))
        else:
            r = put(self.url + "/" + test_id, json=data, verify=self.ca, cert=self.cert)
            if r.status_code != 200:
                sys.exit(
                    "Unable to complete test: HTTP_%d: %s" % (r.status_code, r.text)
                )
            for artifact, urldata in r.json().items():
                self._upload_item(artifacts_dir, artifact, urldata)

    @staticmethod
    def target_name(sota_dir: str) -> str:
        with open(os.path.join(sota_dir, "current-target")) as f:
            for line in f:
                if line.startswith("TARGET_NAME"):
                    k, v = line.split("=")
                    return v.replace('"', "").strip()  # remove spaces and quotes
        sys.exit("Unable to find current target")

    @staticmethod
    def test_url(sota_dir: str) -> str:
        with open(os.path.join(sota_dir, "sota.toml")) as f:
            for line in f:
                if line.startswith("server ="):
                    k, v = line.split("=")
                    v = v.replace('"', "").strip()  # remove spaces and quotes
                    return v + "/tests"
        sys.exit("Unable to find server url")
