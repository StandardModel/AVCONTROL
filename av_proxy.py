#!/usr/bin/env python3
"""
AV Control Panel - local HTTP service.

Serves the iPad panel and bridges its typed AV actions to the LAN devices.

Usage:
    python3 av_proxy.py

Open:
    http://<your-mac-ip>:8765/panel
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PROXY_PORT = int(os.environ.get("AV_PROXY_PORT", "8765"))
PANEL_FILE = Path(__file__).parent / "av_control_panel.html"


@dataclass(frozen=True)
class TcpDevice:
    name: str
    host: str
    port: int
    line_end: str
    greeting_delay: float = 0.2
    response_delay: float = 0.4


MATRIX = TcpDevice(
    name="matrix",
    host=os.environ.get("AV_MATRIX_HOST", "192.168.1.239"),
    port=int(os.environ.get("AV_MATRIX_PORT", "23")),
    line_end="\r\n",
)

PREAMP = TcpDevice(
    name="preamp",
    host=os.environ.get("AV_PREAMP_HOST", "192.168.1.254"),
    port=int(os.environ.get("AV_PREAMP_PORT", "4001")),
    line_end="\n",
)

ITACH = TcpDevice(
    name="itach",
    host=os.environ.get("AV_ITACH_HOST", "192.168.1.175"),
    port=int(os.environ.get("AV_ITACH_PORT", "4998")),
    line_end="\r\n",
    response_delay=0.2,
)

ACTIVE_MATRIX_OUTPUT = int(os.environ.get("AV_ACTIVE_HDMI_OUTPUT", "2"))
START_VOLUME = int(os.environ.get("AV_START_VOLUME", "4"))


# Audio Research LS28SE iTach IR codes.
IR_CODES = {
    "vol_up": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414",
    ),
    "vol_down": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,34,34,67,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,34,34,67,34,3414",
    ),
    "mute": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,67,68,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,67,68,3448",
    ),
    "power": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,34,34,34,34,67,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,34,34,34,34,67,34,3414",
    ),
    "input_BAL1": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,34,34,67,68,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,34,34,67,68,3448",
    ),
    "input_BAL2": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,34,34,67,34,34,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,34,34,67,34,34,34,3414",
    ),
    "input_BAL3": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,67,68,33,34,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,67,68,33,34,3448",
    ),
}

SCENES = {
    "roku": {"hdmi": 1, "preamp": "BAL3", "volume": START_VOLUME, "label": "Roku"},
    "rose": {"hdmi": 2, "preamp": "BAL1", "volume": START_VOLUME, "label": "Rose"},
    "roon": {"hdmi": 3, "preamp": "BAL2", "volume": START_VOLUME, "label": "Roon-BACCH"},
    "apple": {"hdmi": 4, "preamp": "BAL3", "volume": START_VOLUME, "label": "Apple TV"},
}

PREAMP_COMMANDS = {
    "power_on": "POWER ON",
    "power_off": "POWER OFF",
    "mute_on": "MUTE ON",
    "mute_off": "MUTE OFF",
    "mute_toggle": "MUTE",
    "volume_up": "VOLUME UP",
    "volume_down": "VOLUME DOWN",
    "volume_query": "VOLUME ?",
    "status": "STATUS ALL ?",
    "version": "VERSION ?",
}

PREAMP_INPUTS = {"BAL1", "BAL2", "BAL3", "BAL4", "SE1", "SE2", "SE3", "SE4"}


def tcp_send(device: TcpDevice, command: str, timeout: float = 3.0) -> str:
    wire_command = command if command.endswith(("\n", "\r")) else command + device.line_end

    try:
        with socket.create_connection((device.host, device.port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            time.sleep(device.greeting_delay)

            try:
                sock.recv(1024)
            except socket.timeout:
                pass

            sock.sendall(wire_command.encode("ascii"))
            time.sleep(device.response_delay)

            chunks: list[bytes] = []
            sock.settimeout(0.3)
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)

        return b"".join(chunks).decode("ascii", errors="replace")
    except OSError as exc:
        raise RuntimeError(f"TCP error connecting to {device.host}:{device.port}: {exc}") from exc


def retry_tcp(device: TcpDevice, command: str, attempts: int = 2, delay: float = 0.35) -> list[str]:
    responses = []
    for attempt in range(attempts):
        responses.append(tcp_send(device, command))
        if attempt < attempts - 1:
            time.sleep(delay)
    return responses


def send_ir(command: str) -> list[str]:
    if command not in IR_CODES:
        raise ValueError(f"Unknown IR command: {command}")

    responses = []
    code1, code2 = IR_CODES[command]
    for code in (code1, code2):
        responses.append(tcp_send(ITACH, code, timeout=2.0))
        time.sleep(0.05)
    return responses


def matrix_route(output: int, input_number: int, attempts: int = 2) -> dict[str, Any]:
    if output != ACTIVE_MATRIX_OUTPUT:
        raise ValueError(f"HDMI output {output} is disabled; active output is {ACTIVE_MATRIX_OUTPUT}")
    if input_number not in range(1, 5):
        raise ValueError("HDMI input must be 1-4")

    command = f"SET OUT{output} VS IN{input_number}"
    responses = retry_tcp(MATRIX, command, attempts=attempts)
    return {"command": command, "responses": responses}


def preamp_command(data: dict[str, Any]) -> dict[str, Any]:
    action = str(data.get("action", "")).strip()
    command = PREAMP_COMMANDS.get(action)

    if action == "input":
        input_name = str(data.get("input", "")).strip().upper()
        if input_name not in PREAMP_INPUTS:
            raise ValueError("Preamp input must be one of BAL1-BAL4 or SE1-SE4")
        command = f"INPUT SET {input_name}"
    elif action == "volume_set":
        volume = int(data.get("volume"))
        if volume < 0 or volume > 103:
            raise ValueError("Volume must be between 0 and 103")
        command = f"VOLUME SET {volume}"
    elif action == "balance_set":
        balance = int(data.get("balance"))
        if balance < -22 or balance > 22:
            raise ValueError("Balance must be between -22 and 22")
        command = f"BALANCE SET {balance}"
    elif action == "display_set":
        level = int(data.get("level"))
        if level < 1 or level > 7:
            raise ValueError("Display level must be between 1 and 7")
        command = f"DISPLAY SET {level}"

    if not command:
        raise ValueError(f"Unknown preamp action: {action}")

    response = tcp_send(PREAMP, command)
    return {"command": command, "response": response}


def run_scene(scene_name: str) -> dict[str, Any]:
    if scene_name not in SCENES:
        raise ValueError(f"Unknown scene: {scene_name}")

    scene = SCENES[scene_name]
    hdmi_result = matrix_route(ACTIVE_MATRIX_OUTPUT, int(scene["hdmi"]), attempts=2)
    time.sleep(0.4)
    input_result = preamp_command({"action": "input", "input": scene["preamp"]})
    time.sleep(0.4)
    volume_result = preamp_command({"action": "volume_set", "volume": scene["volume"]})
    time.sleep(0.4)
    mute_result = preamp_command({"action": "mute_off"})

    return {
        "scene": scene_name,
        "label": scene["label"],
        "hdmi": hdmi_result,
        "preamp_input": input_result,
        "volume": volume_result,
        "mute": mute_result,
    }


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        pass

    def send_json(self, code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/panel", "/ipad", "/v2"):
            try:
                html = PANEL_FILE.read_bytes()
            except FileNotFoundError:
                self.send_json(404, {"error": "av_control_panel.html not found"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(html)
            return

        if path in ("/health", "/api/status"):
            self.send_json(
                200,
                {
                    "ok": True,
                    "active_hdmi_output": ACTIVE_MATRIX_OUTPUT,
                    "start_volume": START_VOLUME,
                    "devices": {
                        "matrix": {"host": MATRIX.host, "port": MATRIX.port},
                        "preamp": {"host": PREAMP.host, "port": PREAMP.port},
                        "itach": {"host": ITACH.host, "port": ITACH.port},
                    },
                    "scenes": SCENES,
                    "ir_commands": sorted(IR_CODES),
                },
            )
            return

        self.send_json(404, {"error": "Not found"})

    def do_HEAD(self) -> None:
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/panel", "/ipad", "/v2"):
            try:
                size = PANEL_FILE.stat().st_size
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            return

        if path in ("/health", "/api/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        path = urllib.parse.urlsplit(self.path).path

        try:
            data = self.read_json()

            if path == "/send":
                result = self.handle_legacy_send(data)
            elif path == "/api/matrix":
                result = matrix_route(
                    int(data.get("output", ACTIVE_MATRIX_OUTPUT)),
                    int(data["input"]),
                    attempts=int(data.get("attempts", 2)),
                )
            elif path == "/api/preamp":
                result = preamp_command(data)
            elif path == "/api/ir":
                result = {"responses": send_ir(str(data["command"]))}
            elif path == "/api/scene":
                result = run_scene(str(data["scene"]))
            else:
                self.send_json(404, {"error": "Not found"})
                return

            print(f"{path} -> {json.dumps(result)[:240]}")
            self.send_json(200, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            print(f"ERROR {path}: {exc}")
            self.send_json(502, {"error": str(exc)})

    def handle_legacy_send(self, data: dict[str, Any]) -> dict[str, Any]:
        host = str(data["host"])
        port = int(data["port"])
        command = str(data["cmd"])

        known = {
            (MATRIX.host, MATRIX.port): MATRIX,
            (PREAMP.host, PREAMP.port): PREAMP,
            (ITACH.host, ITACH.port): ITACH,
        }
        device = known.get((host, port), TcpDevice("custom", host, port, ""))
        response = tcp_send(device, command)
        return {"response": response}


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "your-mac-ip"


if __name__ == "__main__":
    ip = get_local_ip()
    server = ThreadingHTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)

    print(
        f"""
╔══════════════════════════════════════════════════════╗
║           AV Control Panel Service                  ║
╠══════════════════════════════════════════════════════╣
║  Proxy running at: http://{ip}:{PROXY_PORT}
║  iPad panel:       http://{ip}:{PROXY_PORT}/panel
║  Health:           http://{ip}:{PROXY_PORT}/health
║
║  Active HDMI output: OUT{ACTIVE_MATRIX_OUTPUT}
║  Output 1 is intentionally unused.
║
║  Press Ctrl+C to stop
╚══════════════════════════════════════════════════════╝
"""
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy stopped.")
