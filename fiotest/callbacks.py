from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional


class AktualizrCallbackHandler:
    def on_install_pre(self, current_target: str):
        raise NotImplementedError()

    def on_install_post(self, current_target: str, status: str):
        raise NotImplementedError()


class AktualizrCallbacks(SimpleHTTPRequestHandler):
    callback: AktualizrCallbackHandler = AktualizrCallbackHandler()

    def do_POST(self):
        length = int(self.headers["content-length"])
        buf = self.rfile.read(length)
        parts = buf.decode().split(",")

        msg: str = ""
        current: str = ""
        status: Optional[str] = None

        try:
            if len(parts) == 3:
                msg, current, status = parts
            elif len(parts) == 2:
                msg, current = parts
            else:
                raise ValueError(buf)

            if msg == "install-post":
                assert status is not None  # for mypy
                self.callback.on_install_post(current, status)
            elif msg == "install-pre":
                self.callback.on_install_pre(current)
            else:
                self.log_message("Ignoring callback msg: %s", msg)

        except Exception as e:
            self.log_error("error: %r", e)
            self.send_response(400)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())
            return

        self.send_response(201)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK\n")


class CallbackServer:
    def __init__(self, handler: AktualizrCallbackHandler):
        AktualizrCallbacks.callback = handler
        self.httpd = HTTPServer(("", 8000), AktualizrCallbacks)

    def run_forever(self):
        self.httpd.serve_forever()
