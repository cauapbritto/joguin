import socket
import threading
from flask import Flask, render_template, jsonify, request

import remote_input

app = Flask(__name__, template_folder="templates", static_folder="static")

COMMANDS = [
    "p1_up", "p1_down", "p1_left", "p1_right", "p1_attack", "p1_special", "p1_dodge",
    "p2_up", "p2_down", "p2_left", "p2_right", "p2_attack", "p2_special", "p2_dodge",
    "p3_up", "p3_down", "p3_left", "p3_right", "p3_attack", "p3_special", "p3_dodge",
    "p4_up", "p4_down", "p4_left", "p4_right", "p4_attack", "p4_special", "p4_dodge",
    "p1_super", "p2_super", "p3_super", "p4_super",
    "p1_conducao", "p2_conducao", "p3_conducao", "p4_conducao",
    "p1_pass", "p2_pass", "p3_pass", "p4_pass",
    "p1_corte", "p2_corte", "p3_corte", "p4_corte",
    "p1_char_left", "p1_char_right", "p1_weapon_toggle", "p1_confirm",
    "p2_char_left", "p2_char_right", "p2_weapon_toggle", "p2_confirm",
    "p3_char_left", "p3_char_right", "p3_weapon_toggle", "p3_confirm",
    "p4_char_left", "p4_char_right", "p4_weapon_toggle", "p4_confirm",
    "p1_switch_weapon", "p2_switch_weapon", "p3_switch_weapon", "p4_switch_weapon",
]

# Dados dos personagens para a API (mesma ordem de CHARACTER_TYPES em main.py)
CHARACTERS_DATA = [
    {"name": "Guerreiro",  "image": "warrior.png",  "color": [60,120,255]},
    {"name": "Atirador",   "image": "shooter.png",  "color": [0,255,255]},
    {"name": "Tanque",     "image": "tank.png",     "color": [128,128,128]},
    {"name": "Ninja",      "image": "ninja.png",    "color": [0,200,200]},
    {"name": "Velocista",  "image": "speedster.png","color": [255,255,0]},
    {"name": "Aryel",      "image": "aryel.png",    "color": [255,165,0]},
    {"name": "Fantasma",   "image": "ghost.png",    "color": [180,0,255]},
    {"name": "Titã",       "image": "titan.png",    "color": [255,215,0]},
]

# Times do futebol
TEAMS = {1: 0, 3: 0, 2: 1, 4: 1}

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

# ── API de personagens para seleção no celular ──

@app.route("/api/characters")
def api_characters():
    return jsonify(CHARACTERS_DATA)

@app.route("/api/status")
def api_status():
    claimed = list(remote_input.get_claimed())
    chars = remote_input.get_all_player_chars()
    ready = {str(p): remote_input.is_player_ready(p) for p in range(1, 5)}
    return jsonify({
        "game_state": remote_input.get_game_state(),
        "claimed": claimed,
        "player_chars": chars,
        "player_ready": ready,
        "teams": TEAMS,
    })

@app.route("/api/claim/<int:player_num>", methods=["POST"])
def api_claim(player_num):
    if player_num < 1 or player_num > 4:
        return "invalid player", 400
    if remote_input.is_claimed(player_num):
        return "already claimed", 409
    remote_input.claim_player(player_num)
    return jsonify({"player": player_num, "team": TEAMS.get(player_num, 0)})

@app.route("/api/select_char", methods=["POST"])
def api_select_char():
    data = request.get_json(force=True)
    player_num = int(data.get("player", 0))
    char_index = int(data.get("char_index", 0))
    if player_num < 1 or player_num > 4:
        return "invalid player", 400
    if char_index < 0 or char_index >= len(CHARACTERS_DATA):
        return "invalid char_index", 400
    remote_input.set_player_char(player_num, char_index)
    return "ok", 200

@app.route("/api/ready/<int:player_num>", methods=["POST"])
def api_ready(player_num):
    if player_num < 1 or player_num > 4:
        return "invalid player", 400
    remote_input.set_player_ready(player_num, True)
    return jsonify({"ready": True})

@app.route("/api/start", methods=["POST"])
def api_start():
    remote_input.set_game_state("start_game")
    return "ok", 200

@app.route("/api/super_cooldown", methods=["GET"])
def api_super_cooldown():
    return jsonify(remote_input.get_all_super_cooldowns())

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
    print(f"  \033[1;36mhttp://{ip}:{port}?player=3\033[0m  (Jogador 3 — Futebol)")
    print(f"  \033[1;36mhttp://{ip}:{port}?player=4\033[0m  (Jogador 4 — Futebol)")
    print(f"  (certifique-se de estar na mesma rede Wi-Fi)")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)

def start_server_thread(port=5000, debug=False):
    t = threading.Thread(target=start_server, args=(port, debug), daemon=True)
    t.start()
    return t
