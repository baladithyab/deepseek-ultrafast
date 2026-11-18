"""Front door for the two-servers-in-one-pod KV transfer test.

Header `X-DSUF-Server: 0` or `1` picks the backend; without it requests alternate.
shortcut: test-only single-file proxy (thread per request, close-delimited responses); use a real proxy for load.
"""
import http.client
import itertools
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BACKENDS = [int(p) for p in sys.argv[2:]] or [8001, 8002]
_next = itertools.cycle(range(len(BACKENDS)))


def fetch(port, method, path, body, headers):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=600)
    conn.request(method, path, body=body, headers=headers)
    return conn, conn.getresponse()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":  # liveness: the proxy itself; wait -n covers the servers
            self.send_response(200)
            self.end_headers()
            return
        if self.path == "/readyz":  # ready only when every backend is
            try:
                ok = True
                for port in BACKENDS:
                    conn, resp = fetch(port, "GET", self.path, None, {})
                    ok = ok and resp.status == 200
                    conn.close()
            except OSError:
                ok = False
            self.send_response(200 if ok else 503)
            self.end_headers()
            return
        self.forward()

    def do_POST(self):
        self.forward()

    def forward(self):
        pick = self.headers.get("X-DSUF-Server")
        index = int(pick) % len(BACKENDS) if pick is not None else next(_next)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        skip = {"host", "connection", "content-length", "x-dsuf-server"}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in skip}
        conn, resp = fetch(BACKENDS[index], self.command, self.path, body, headers)
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in ("transfer-encoding", "content-length", "connection"):
                self.send_header(k, v)
        self.send_header("X-DSUF-Served-By", str(index))
        self.send_header("Connection", "close")
        self.end_headers()
        while chunk := resp.read1(65536):
            self.wfile.write(chunk)
            self.wfile.flush()
        conn.close()
        self.close_connection = True

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1])), Handler).serve_forever()
