#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import urllib.parse
import time

HOST = "0.0.0.0"
PORT = 9090

AVPRO_IP = "192.168.1.239"
ITACH_IP = "192.168.1.175"

HTTPServer.allow_reuse_address = True

# -------------------------------------------------
# HDMI INPUTS
# -------------------------------------------------

HDMI_MAP = {
    "roku": 1,
    "rose": 2,
    "roon": 3,
    "appletv": 4,
}

# -------------------------------------------------
# LS28SE IR CODES
# Replace these with final learned codes as needed.
# Vol up / down are the codes you already tested.
# -------------------------------------------------

IR_CODES = {
    "volup":   "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414",
    "voldown": "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414",

    # Put real LS28SE codes here when learned.
    # Leave blank and the script will safely skip them.
    "unmute": "",
    "input1": "",
    "input2": "",
    "input3": "",
    "input4": "",
}

# -------------------------------------------------
# ACTIVITY MAP
# Each source can select HDMI + LS28 input + volume preset
# -------------------------------------------------

ACTIVITIES = {
    "roku": {
        "label": "Roku",
        "hdmi": 1,
        "ls28_input": "input3",
        "volume": 20,
    },
    "rose": {
        "label": "HiFi Rose",
        "hdmi": 2,
        "ls28_input": "input1",
        "volume": 20,
    },
    "roon": {
        "label": "Roon / BACCH",
        "hdmi": 3,
        "ls28_input": "input2",
        "volume": 20,
    },
    "appletv": {
        "label": "Apple TV",
        "hdmi": 4,
        "ls28_input": "input3",
        "volume": 20,
    },
}

# How many volume-down commands to send before setting preset.
# This forces volume down near zero before counting up.
VOLUME_RESET_STEPS = 35
IR_PAUSE = 0.18

# -------------------------------------------------
# LOW LEVEL COMMANDS
# -------------------------------------------------

def avpro_cmd(text):
    cmd = f'( printf "{text}\\r\\n"; sleep 1 ) | nc -w 3 {AVPRO_IP} 23'
    subprocess.call(cmd, shell=True)

def send_hdmi(input_num):
    # Double-send fixes the AVPro first-press reliability issue.
    avpro_cmd(f"SET OUT1 VS IN{input_num}")
    time.sleep(0.4)
    avpro_cmd(f"SET OUT1 VS IN{input_num}")

def send_ir_key(key):
    code = IR_CODES.get(key, "")
    if not code:
        print(f"IR skipped: {key} has no learned code yet")
        return

    cmd = f'( printf "{code}\\r\\n"; sleep 0.25 ) | nc -w 2 {ITACH_IP} 4998'
    subprocess.call(cmd, shell=True)
    time.sleep(IR_PAUSE)

def set_volume(level):
    print(f"Setting LS28SE volume preset to {level}")

    for _ in range(VOLUME_RESET_STEPS):
        send_ir_key("voldown")

    time.sleep(0.4)

    for _ in range(level):
        send_ir_key("volup")

def run_activity(name):
    activity = ACTIVITIES[name]

    print(f"Running activity: {activity['label']}")

    # 1. HDMI switch
    send_hdmi(activity["hdmi"])

    # 2. Select LS28SE input
    send_ir_key(activity["ls28_input"])

    # 3. Unmute LS28SE
    send_ir_key("unmute")

    # 4. Reset and set volume preset
    set_volume(activity["volume"])

# -------------------------------------------------
# WEB SERVER
# -------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/activity/"):
            key = path.split("/")[-1]
            if key in ACTIVITIES:
                run_activity(key)
                self.redirect_home()
                return

        if path.startswith("/set/"):
            key = path.split("/")[-1]
            if key in HDMI_MAP:
                send_hdmi(HDMI_MAP[key])
                self.redirect_home()
                return

        if path.startswith("/ir/"):
            key = path.split("/")[-1]
            if key in IR_CODES:
                send_ir_key(key)
                self.redirect_home()
                return

        self.show_page()

    def redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def show_page(self):
        html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ron AV Control</title>
<style>
:root {
    --bg1: #0b0f17;
    --bg2: #151b2b;
    --card: rgba(255,255,255,0.08);
    --card2: rgba(255,255,255,0.14);
    --text: #f4f4f5;
    --muted: #a7adbb;
    --accent: #d8b46a;
    --blue: #5ca7ff;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background:
        radial-gradient(circle at top left, #26324d 0%, transparent 34%),
        radial-gradient(circle at bottom right, #3a2b12 0%, transparent 36%),
        linear-gradient(135deg, var(--bg1), var(--bg2));
    color: var(--text);
}
.wrapper {
    max-width: 980px;
    margin: 0 auto;
    padding: 38px 22px 50px;
}
.header {
    text-align: center;
    margin-bottom: 30px;
}
.header h1 {
    font-size: 44px;
    margin: 0;
    letter-spacing: -1px;
}
.header p {
    margin-top: 10px;
    color: var(--muted);
    font-size: 18px;
}
.panel {
    background: rgba(0,0,0,0.28);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 28px;
    padding: 26px;
    box-shadow: 0 24px 70px rgba(0,0,0,0.45);
    backdrop-filter: blur(10px);
}
.section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 4px 4px 18px;
}
.section-title h2 {
    font-size: 24px;
    margin: 0;
}
.badge {
    color: #111;
    background: var(--accent);
    padding: 7px 12px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 13px;
}
.grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(180px, 1fr));
    gap: 18px;
}
.tile {
    position: relative;
    display: block;
    min-height: 150px;
    padding: 22px;
    border-radius: 24px;
    color: white;
    text-decoration: none;
    background: linear-gradient(145deg, var(--card), rgba(255,255,255,0.04));
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: 0 14px 35px rgba(0,0,0,0.28);
    overflow: hidden;
    transition: transform 0.12s ease, background 0.12s ease, border 0.12s ease;
}
.tile:active { transform: scale(0.97); }
.tile:hover {
    background: linear-gradient(145deg, var(--card2), rgba(255,255,255,0.07));
    border-color: rgba(216,180,106,0.65);
}
.tile .icon {
    font-size: 34px;
    margin-bottom: 14px;
}
.tile .name {
    font-size: 27px;
    font-weight: 800;
    letter-spacing: -0.3px;
}
.tile .sub {
    margin-top: 8px;
    font-size: 15px;
    color: var(--muted);
}
.tile:after {
    content: "";
    position: absolute;
    right: -30px;
    bottom: -42px;
    width: 145px;
    height: 145px;
    border-radius: 50%;
    background: rgba(216,180,106,0.12);
}
.controls {
    margin-top: 26px;
}
.vol-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(160px, 1fr));
    gap: 18px;
}
.vol {
    display: block;
    padding: 24px;
    border-radius: 24px;
    color: white;
    text-decoration: none;
    font-size: 26px;
    font-weight: 800;
    background: linear-gradient(145deg, rgba(92,167,255,0.22), rgba(255,255,255,0.05));
    border: 1px solid rgba(92,167,255,0.32);
    box-shadow: 0 14px 35px rgba(0,0,0,0.25);
}
.vol:active { transform: scale(0.97); }
.footer {
    text-align: center;
    margin-top: 22px;
    color: var(--muted);
    font-size: 13px;
}
@media (max-width: 700px) {
    .header h1 { font-size: 34px; }
    .grid { grid-template-columns: 1fr; }
    .vol-grid { grid-template-columns: 1fr; }
    .tile { min-height: 125px; }
}
</style>
</head>
<body>
<div class="wrapper">
    <div class="header">
        <h1>Ron AV Control</h1>
        <p>One-touch activities: HDMI + LS28SE input + unmute + volume preset</p>
    </div>

    <div class="panel">
        <div class="section-title">
            <h2>Activities</h2>
            <span class="badge">One Touch</span>
        </div>

        <div class="grid">
            <a class="tile" href="/activity/roku">
                <div class="icon">📺</div>
                <div class="name">Roku</div>
                <div class="sub">HDMI 1 · LS28 input 3 · Vol 20</div>
            </a>
            <a class="tile" href="/activity/rose">
                <div class="icon">🎵</div>
                <div class="name">HiFi Rose</div>
                <div class="sub">HDMI 2 · LS28 input 1 · Vol 20</div>
            </a>
            <a class="tile" href="/activity/roon">
                <div class="icon">💿</div>
                <div class="name">Roon / BACCH</div>
                <div class="sub">HDMI 3 · LS28 input 2 · Vol 20</div>
            </a>
            <a class="tile" href="/activity/appletv">
                <div class="icon"></div>
                <div class="name">Apple TV</div>
                <div class="sub">HDMI 4 · LS28 input 3 · Vol 20</div>
            </a>
        </div>

        <div class="controls">
            <div class="section-title">
                <h2>Manual Volume</h2>
                <span class="badge">LS28SE IR</span>
            </div>

            <div class="vol-grid">
                <a class="vol" href="/ir/voldown">Volume −</a>
                <a class="vol" href="/ir/volup">Volume +</a>
            </div>
        </div>

        <div class="controls">
            <div class="section-title">
                <h2>HDMI Only</h2>
                <span class="badge">Manual</span>
            </div>

            <div class="grid">
                <a class="tile" href="/set/roku"><div class="name">Roku Only</div><div class="sub">HDMI only</div></a>
                <a class="tile" href="/set/rose"><div class="name">Rose Only</div><div class="sub">HDMI only</div></a>
                <a class="tile" href="/set/roon"><div class="name">Roon Only</div><div class="sub">HDMI only</div></a>
                <a class="tile" href="/set/appletv"><div class="name">Apple TV Only</div><div class="sub">HDMI only</div></a>
            </div>
        </div>
    </div>

    <div class="footer">
        Mac server: port 9090 · AVPro: 192.168.1.239 · iTach: 192.168.1.175
    </div>
</div>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

def run():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Starting AV control server on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    run()
