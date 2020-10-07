#!/usr/bin/python3

import ctypes
from io import BytesIO
import json
import os
import logging
import subprocess
from time import sleep
from typing import Dict, NamedTuple, Optional

import pycurl

log = logging.getLogger()
module = b"/usr/lib/softhsm/libsofthsm2.so"


def _find_serial(module: str) -> str:
    in_slot = False
    out = subprocess.check_output(["pkcs11-tool", "--module", module, "-L"])
    for line in out.decode().splitlines():
        key, val = line.split(":", 1)
        key = key.strip()
        if key == "token label":
            in_slot = val.strip() == "aktualizr"
        if key == "serial num" and in_slot:
            return val.strip()
    raise ValueError("Unable to find pkcs11 serial number of slot")


def _init_engine(module: str):
    libcrypto = ctypes.cdll.LoadLibrary("libcrypto.so.1.1")
    if libcrypto.ENGINE_load_builtin_engines() != 1:
        raise RuntimeError("Error in libcrypto.ENGINE_load_builtin_engines")

    e = libcrypto.ENGINE_by_id(b"dynamic")
    if e is None:
        raise RuntimeError("Error in libcrypto.ENGINE_by_id")

    def _cmd_str(key: bytes, val: Optional[bytes]):
        if libcrypto.ENGINE_ctrl_cmd_string(e, key, val, 0) != 1:
            k = key.decode()
            v = None
            if val:
                v = val.decode()
            raise RuntimeError(f"Error in libcrypto.ENGINE_ctrl_cmd_string({k}, {v})")

    _cmd_str(b"SO_PATH", b"/usr/lib/engines-1.1/pkcs11.so")
    _cmd_str(b"ID", b"pkcs11")
    _cmd_str(b"LIST_ADD", b"1")
    _cmd_str(b"LOAD", None)
    _cmd_str(b"MODULE_PATH", module.encode())
    _cmd_str(b"PIN", b"87654321")
    if libcrypto.ENGINE_init(e) != 1:
        raise RuntimeError("Unable to call libcrypto.ENGINE_init")


class Response(NamedTuple):
    url: str
    status_code: int
    text: str


class DeviceGatewayClient:
    _initialized = None

    def __init__(self, sota_dir: str):
        self.verbose = False
        self._root_crt = os.path.join(sota_dir, "root.crt")
        with open(os.path.join(sota_dir, "sota.toml")) as f:
            source = module = pin = pk = cert = None
            for line in f:
                if line.startswith("module"):
                    module = line.split('"')[1]
                if line.startswith("pass"):
                    pin = line.split('"')[1]
                if line.startswith("tls_pkey_id"):
                    pk = line.split('"')[1]
                if line.startswith("tls_clientcert_id"):
                    cert = line.split('"')[1]
                if line.startswith("pkey_source"):
                    source = line.split('"')[1]

            log.info("pkey_source for configuration is: %s", source)
            if source == "pkcs11":
                if not all((module, pin, pk, cert)):
                    raise ValueError("Missing required p11 values in sota.toml")

                if not DeviceGatewayClient._initialized:
                    assert module is not None  # for mypy
                    serial = _find_serial(module)
                    _init_engine(module)

                    cert_uri = f"pkcs11:serial={serial};pin-value={pin};id=%{cert}"
                    pkey_uri = f"pkcs11:serial={serial};pin-value={pin};id=%{pk}"
                    DeviceGatewayClient._initialized = ("ENG", cert_uri, pkey_uri)
            else:
                cert = os.path.join(sota_dir, "client.pem")
                pkey = os.path.join(sota_dir, "pkey.pem")
                DeviceGatewayClient._initialized = ("PEM", cert, pkey)

    def _curl_init(self, url: str) -> pycurl.Curl:
        c = pycurl.Curl()
        c.setopt(pycurl.SSL_VERIFYPEER, 1)
        c.setopt(pycurl.SSL_VERIFYHOST, 2)
        c.setopt(pycurl.USE_SSL, pycurl.USESSL_ALL)
        c.setopt(pycurl.SSLENGINE, "pkcs11")
        c.setopt(pycurl.SSLENGINE_DEFAULT, 1)

        c.setopt(pycurl.CAINFO, self._root_crt)

        assert DeviceGatewayClient._initialized is not None  # for mypy
        c.setopt(pycurl.SSLCERT, DeviceGatewayClient._initialized[1])
        c.setopt(pycurl.SSLCERTTYPE, DeviceGatewayClient._initialized[0])

        c.setopt(pycurl.SSLKEY, DeviceGatewayClient._initialized[2])
        c.setopt(pycurl.SSLKEYTYPE, DeviceGatewayClient._initialized[0])

        c.setopt(pycurl.URL, url)

        if self.verbose:
            c.setopt(pycurl.VERBOSE, 1)
        return c

    def _op(self, op: int, url: str, data: dict, headers: Dict[str, str]) -> Response:
        buf = BytesIO()
        headers["Content-type"] = "application/json"
        header_array = [k + ": " + v for k, v in headers.items()]
        c = self._curl_init(url)
        try:
            if op in (pycurl.PUT, pycurl.POST):
                if op == pycurl.PUT:
                    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
                c.setopt(pycurl.POSTFIELDS, json.dumps(data))
            c.setopt(pycurl.HTTPHEADER, header_array)
            c.setopt(pycurl.WRITEDATA, buf)
            c.perform()
            status = c.getinfo(pycurl.RESPONSE_CODE)
            return Response(url, status, buf.getvalue().decode())
        finally:
            c.close()

    def _retriable_op(
        self, op: int, url: str, data: dict, headers: Dict[str, str]
    ) -> Response:
        for i in (0, 1, 2, 4, 8, 16):
            sleep(i)
            r = self._op(op, url, data, headers)
            if r.status_code in (200, 201):
                break
            else:
                log.error("HTTP_%d: %s: %s", r.status_code, r.url, r.text)
        return r

    def post(self, url: str, data: dict, headers: Dict[str, str]) -> Response:
        return self._retriable_op(pycurl.POST, url, data, headers)

    def put(self, url: str, data: dict, headers: Dict[str, str]) -> Response:
        return self._retriable_op(pycurl.PUT, url, data, headers)

    def put_file(self, url: str, path: str, headers: Dict[str, str]) -> Response:
        for i in (0, 1, 2, 4, 8, 16):
            sleep(i)
            buf = BytesIO()
            header_array = [k + ": " + v for k, v in headers.items()]
            c = self._curl_init(url)
            try:
                c.setopt(pycurl.CUSTOMREQUEST, "PUT")
                c.setopt(pycurl.HTTPHEADER, header_array)
                c.setopt(pycurl.WRITEDATA, buf)
                c.setopt(pycurl.UPLOAD, 1)
                with open(path) as f:
                    c.setopt(pycurl.READDATA, f)
                    c.perform()
                status = c.getinfo(pycurl.RESPONSE_CODE)
                r = Response(url, status, buf.getvalue().decode())
                if r.status_code in (200, 201):
                    break
                else:
                    log.error("HTTP_%d: %s: %s", r.status_code, r.url, r.text)
            finally:
                c.close()
        return r
