from flask import Flask, redirect
import socket
import time

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================

AVPRO_IP = "192.168.1.239"
AVPRO_PORT = 23

ITACH_IP = "192.168.1.67"
ITACH_PORT = 4998

DEFAULT_VOLUME_STEPS = 20

# =========================
# AVPRO HDMI SWITCHING
# =========================

def send_avpro(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)

        s.connect((AVPRO_IP, AVPRO_PORT))
        s.send((command + "\r\n").encode())

        response = s.recv(1024).decode(errors="ignore")
        print("AVPRO:", response)

        s.close()

    except Exception as e:
        print("AVPRO ERROR:", e)

# =========================
# ITACH IR SENDING
# =========================
def send_pair(code1, code2):
    send_itach(code1)
    time.sleep(0.05)
    send_itach(code2)
def send_itach(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)

        s.connect((ITACH_IP, ITACH_PORT))
        s.send((command + "\r").encode())

        response = s.recv(1024).decode(errors="ignore")
        print("ITACH:", response)

        s.close()

    except Exception as e:
        print("ITACH ERROR:", e)

IR_CODES = {

    "vol_up": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,67,34,34,34,3414"
    ),

    "vol_down": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,34,34,67,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,34,34,67,34,3414"
    ),

    "mute": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,67,68,33,34,67,68,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,67,68,33,34,67,68,3448"
    ),

    "input_BAL1": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,34,34,67,68,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,34,34,67,68,3448"
    ),

    "input_BAL2": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,34,34,67,34,34,34,3414",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,34,34,67,34,34,34,3414"
    ),

    "input_BAL3": (
        "sendir,1:1,1,38000,1,1,34,34,68,67,68,33,34,34,34,67,68,33,34,34,34,67,68,33,34,3448",
        "sendir,1:1,1,38000,1,1,34,34,34,34,34,34,68,33,34,34,34,67,68,33,34,34,34,67,68,33,34,3448"
    ),
}

# =========================
# ACTIVITY ENGINE
# =========================

def set_volume_baseline():
    for _ in range(DEFAULT_VOLUME_STEPS):
        send_itach(VOL_DOWN)
        time.sleep(0.08)

def run_activity(hdmi_input, ls28_command):

    # HDMI SWITCH
    send_avpro(f"SET OUT1 VS IN{hdmi_input}")

    time.sleep(0.5)

    # LS28 INPUT
    code1, code2 = IR_CODES[ls28_command]
    send_pair(code1, code2)

    time.sleep(0.3)

    # UNMUTE
    code1, code2 = IR_CODES["mute"]
    send_pair(code1, code2)

    time.sleep(0.3)

    # RESET VOLUME LOW
    set_volume_baseline()

    # BRING TO START LEVEL
    for _ in range(DEFAULT_VOLUME_STEPS):
        code1, code2 = IR_CODES["vol_up"]
        send_pair(code1, code2)
        time.sleep(0.08)
@app.route("/")
def home():

    return """
    <html>
    <head>
    <title>AV Control</title>

    <style>
    body {
        background-color: #111;
        color: white;
        font-family: Arial;
        text-align: center;
    }

    .button {
        display: inline-block;
        width: 260px;
        padding: 30px;
        margin: 20px;
        font-size: 32px;
        border-radius: 20px;
        background-color: #333;
        color: white;
        text-decoration: none;
    }

    .volbutton {
        display: inline-block;
        width: 120px;
        padding: 25px;
        margin: 15px;
        font-size: 28px;
        border-radius: 20px;
        background-color: #555;
        color: white;
        text-decoration: none;
    }
    </style>

    </head>

    <body>

    <h1>Ron AV Control</h1>

    <a class="button" href="/activity/1/input_BAL1">Roku</a>
    <a class="button" href="/activity/2/input_BAL2">HiFi Rose</a>
    <a class="button" href="/activity/3/input_BAL3">Roon/BACCH</a>
    <a class="button" href="/activity/4/input_BAL1">Apple TV</a>

    <br><br><br>

    <a class="volbutton" href="/volup">VOL +</a>
    <a class="volbutton" href="/voldown">VOL -</a>
    <a class="volbutton" href="/mute">MUTE</a>

    </body>
    </html>
    """

@app.route("/activity/<hdmi>/<ls28>")
def activity(hdmi, ls28):

    run_activity(hdmi, ls28)

    return redirect("/")

@app.route("/volup")
def volup():

    code1, code2 = IR_CODES["vol_up"]
    send_pair(code1, code2)

    return redirect("/")

@app.route("/voldown")
def voldown():

    code1, code2 = IR_CODES["vol_down"]
    send_pair(code1, code2)

    return redirect("/")

@app.route("/mute")
def mute():

    code1, code2 = IR_CODES["mute"]
    send_pair(code1, code2)

    return redirect("/")

if __name__ == "__main__":

app.run(
    host="0.0.0.0",
    port=9090,
    debug=False
)
