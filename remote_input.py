import threading

_commands = {}
_lock = threading.Lock()

_game_state = "menu"
_game_state_lock = threading.Lock()

# Estado compartilhado para seleção de personagem (futebol)
_player_chars = {1: 0, 2: 0, 3: 0, 4: 0}
_player_ready = {1: False, 2: False, 3: False, 4: False}
_players_claimed = set()
_chars_lock = threading.Lock()

# Super cooldown compartilhado (atualizado por main.py a cada frame)
_super_cooldowns = {1: 0, 2: 0, 3: 0, 4: 0}

def set_super_cooldown(player_num, frames):
    with _chars_lock:
        _super_cooldowns[player_num] = frames

def get_super_cooldown(player_num):
    with _chars_lock:
        return _super_cooldowns.get(player_num, 0)

def get_all_super_cooldowns():
    with _chars_lock:
        return dict(_super_cooldowns)

def press(key):
    with _lock:
        _commands[key] = True

def release(key):
    with _lock:
        _commands[key] = False

def release_all():
    with _lock:
        _commands.clear()

def is_pressed(key):
    with _lock:
        return _commands.get(key, False)

def get_state():
    with _lock:
        return dict(_commands)

def set_game_state(state):
    global _game_state
    with _game_state_lock:
        _game_state = state

def get_game_state():
    with _game_state_lock:
        return _game_state

def claim_player(player_num):
    with _chars_lock:
        _players_claimed.add(player_num)

def unclaim_player(player_num):
    with _chars_lock:
        _players_claimed.discard(player_num)

def is_claimed(player_num):
    with _chars_lock:
        return player_num in _players_claimed

def get_claimed():
    with _chars_lock:
        return set(_players_claimed)

def set_player_char(player_num, char_index):
    with _chars_lock:
        _player_chars[player_num] = char_index

def get_player_char(player_num):
    with _chars_lock:
        return _player_chars.get(player_num, 0)

def get_all_player_chars():
    with _chars_lock:
        return dict(_player_chars)

def set_player_ready(player_num, ready):
    with _chars_lock:
        _player_ready[player_num] = ready

def is_player_ready(player_num):
    with _chars_lock:
        return _player_ready.get(player_num, False)

def all_claimed_ready():
    with _chars_lock:
        for p in _players_claimed:
            if not _player_ready.get(p, False):
                return False
        return len(_players_claimed) > 0

def reset_lobby():
    with _chars_lock:
        _player_chars = {1: 0, 2: 0, 3: 0, 4: 0}
        _player_ready = {1: False, 2: False, 3: False, 4: False}
        _players_claimed = set()
