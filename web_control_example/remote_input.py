import threading

_commands = {}
_lock = threading.Lock()

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
