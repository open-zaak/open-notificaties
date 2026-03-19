#!/usr/bin/env python3
import os
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import defaultdict
from datetime import datetime, timezone

TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", 15))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("webhook")

counts = defaultdict(int)


def now():
    return datetime.now(timezone.utc).isoformat()


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence default httpserver logs

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def send_json(self, status, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            log.info("CLIENT disconnected before response was sent")

    def handle_webhook(self, method):
        path = self.path
        counts[path] += 1
        count = counts[path]

        body = self.read_body()
        content_type = self.headers.get("Content-Type", "")

        # Try to parse body
        parsed_body = None
        if body:
            if "application/json" in content_type:
                try:
                    parsed_body = json.loads(body)
                except Exception:
                    parsed_body = body.decode(errors="replace")
            else:
                parsed_body = body.decode(errors="replace")

        log.info(
            "REQUEST #%d | %s %s | content-type: %s | body: %s",
            count,
            method,
            path,
            content_type or "none",
            json.dumps(parsed_body) if parsed_body is not None else "(empty)",
        )

        self.send_json(200, {
            "received": True,
            "timestamp": now(),
            "method": method,
            "path": path,
            "count": count,
            "body": parsed_body,
        })

    def do_GET(self):
        if self.path == "/stats":
            self.do_stats()
        elif self.path == "/reset":
            self.do_reset()
        self.do_unknown()

    def do_POST(self):
        if self.path == "/204":
            self.do_204()
        elif self.path == "/400":
            self.do_400()
        elif self.path == "/timeout":
            self.do_timeout()
        else:
            self.do_unknown()

    def do_204(self):
        counts["/204"] += 1
        log.info("204 | count: %d", counts["/204"])
        self.send_response(204)
        self.end_headers()

    def do_400(self):
        counts["/400"] += 1
        log.info("400 | count: %d", counts["/400"])
        self.send_json(400, {"error": "Bad Request"})

    def do_timeout(self):
        counts["/timeout"] += 1
        log.info("TIMEOUT started | count: %d | sleeping %ds", counts["/timeout"], TIMEOUT_SECONDS)
        time.sleep(TIMEOUT_SECONDS)
        log.info("TIMEOUT finished")
        self.send_json(200, {"message": f"Finished after {TIMEOUT_SECONDS}s"})

    def do_stats(self):
        log.info("STATS requested | counts: %s", dict(counts))
        self.send_json(200, {
            "timestamp": now(),
            "counts": dict(counts),
            "total": sum(counts.values()),
        })

    def do_reset(self):
        old = dict(counts)
        counts.clear()
        log.info("RESET | cleared counts: %s", old)
        self.send_json(200, {"reset": True, "cleared": old})

    def do_unknown(self):
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    server = ThreadingHTTPServer((host, port), WebhookHandler)
    log.info("Webhook tester listening on %s:%d", host, port)
    log.info("  POST/GET/PUT/PATCH/DELETE any path to log + count")
    log.info("  GET /204     — return 204")
    log.info("  GET /400     — return 400")
    log.info("  GET /timeout — sleep %ds then return 200", TIMEOUT_SECONDS)
    log.info("  GET /stats   — show counts")
    log.info("  GET /reset   — reset all counts")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
