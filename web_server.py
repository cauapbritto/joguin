import socket
import threading
from flask import Flask, render_template, jsonify

import remote_input

app = Flask(__name__, template_folder="templates", static_folder="static")

COMMANDS = [
    "p1_up", "p1_down", "p1_left", "p1_right", "p1_attack", "p1_special", "p1_dodge",
    "p2_up", "p2_down", "p2_left", "p2_right", "p2_attack", "p2_special", "p2_dodge",
    "p1_char_left", "p1_char_right", "p1_weapon_toggle", "p1_confirm",
    "p2_char_left", "p2_char_right", "p2_weapon_toggle", "p2_confirm",
    "p1_switch_weapon", "p2_switch_weapon",
]

@app.route("/")
def index():
    return render_template("controller.html")

@app.route("/press/<key>", methods=["POST"])
def do_press(key):
    if key in COMMANDS:
        remote_input.press(key)
    return "ok", 200

@app.route("/release/<key>", methods=["POST"])
def do_release(key):
    if key in COMMANDS:
        remote_input.release(key)
    return "ok", 200

@app.route("/release_all", methods=["POST"])
def do_release_all():
    remote_input.release_all()
    return "ok", 200

@app.route("/state")
def get_state():
    return jsonify(remote_input.get_state())

@app.route("/api/game-state")
def game_state():
    return jsonify({"state": remote_input.get_game_state()})

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def start_server(port=5000, debug=False):
    ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  Servidor de controle remoto iniciado!")
    print(f"  Abra no celular:")
    print(f"  \033[1;36mhttp://{ip}:{port}?player=1\033[0m  (Jogador 1)")
    print(f"  \033[1;36mhttp://{ip}:{port}?player=2\033[0m  (Jogador 2)")
    print(f"  (certifique-se de estar na mesma rede Wi-Fi)")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)

def start_server_thread(port=5000, debug=False):
    t = threading.Thread(target=start_server, args=(port, debug), daemon=True)
    t.start()
    return t
