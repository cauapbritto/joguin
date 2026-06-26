import threading

_commands = {}
_lock = threading.Lock()

_game_state = "menu"
_game_state_lock = threading.Lock()

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
