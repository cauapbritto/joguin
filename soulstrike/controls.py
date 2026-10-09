"""Entrada dos jogadores: teclado e celular passam pela mesma interface."""
import math

import pygame

from . import config

K = pygame
KEYMAP = {
    1: {
        "up": (K.K_w,), "down": (K.K_s,), "left": (K.K_a,), "right": (K.K_d,),
        "attack": (K.K_g,), "special": (K.K_f,), "dodge": (K.K_LSHIFT, K.K_SPACE),
        "switch": (K.K_q,), "super": (K.K_q,), "dribble": (K.K_e,),
        "char_left": (K.K_a,), "char_right": (K.K_d,), "weapon": (K.K_w, K.K_s),
        "confirm": (K.K_g,), "cancel": (K.K_f,),
    },
    2: {
        "up": (K.K_UP,), "down": (K.K_DOWN,), "left": (K.K_LEFT,), "right": (K.K_RIGHT,),
        "attack": (K.K_SEMICOLON, K.K_KP1), "special": (K.K_SLASH, K.K_KP2),
        "dodge": (K.K_PERIOD, K.K_KP3), "switch": (K.K_u, K.K_COMMA, K.K_KP0),
        "super": (K.K_u, K.K_COMMA, K.K_KP0), "dribble": (K.K_RSHIFT, K.K_KP4),
        "char_left": (K.K_LEFT,), "char_right": (K.K_RIGHT,), "weapon": (K.K_UP, K.K_DOWN),
        "confirm": (K.K_SEMICOLON, K.K_m, K.K_KP1), "cancel": (K.K_SLASH, K.K_KP2),
    },
}

# Nome das teclas para as telas de ajuda
KEY_LABELS = {
    1: {"move": "W A S D", "attack": "G", "special": "F", "dodge": "SHIFT", "switch": "Q", "dribble": "E"},
    2: {"move": "SETAS", "attack": ";", "special": "/", "dodge": ".", "switch": "U", "dribble": "SHIFT DIR"},
}

DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class PlayerInput:
    """Estado dos comandos de um jogador neste quadro (teclado + celular)."""

    def __init__(self, slot):
        self.slot = slot
        self.keys = KEYMAP.get(slot, {})
        self.prefix = f"p{slot}_"
        self._held = set()
        self._pressed = set()
        self._last_tap = {}
        self.double_tap = None
        self.analog = None

    def update(self, keys_down, keys_pressed, remote_held, remote_pressed, now_ms, analog=None):
        self.analog = analog
        held, pressed = set(), set()
        for action, codes in self.keys.items():
            if any(keys_down[c] for c in codes):
                held.add(action)
            if any(c in keys_pressed for c in codes):
                pressed.add(action)
        n = len(self.prefix)
        for key in remote_held:
            if key.startswith(self.prefix):
                held.add(key[n:])
        for key in remote_pressed:
            if key.startswith(self.prefix):
                pressed.add(key[n:])
                held.add(key[n:])
        self._held, self._pressed = held, pressed

        # duplo toque numa direção = esquiva
        self.double_tap = None
        for d in DIRECTIONS:
            if d in pressed:
                if now_ms - self._last_tap.get(d, -10_000) < config.DOUBLE_TAP_MS:
                    self.double_tap = DIRECTIONS[d]
                    self._last_tap[d] = -10_000
                else:
                    self._last_tap[d] = now_ms

    def held(self, action):
        return action in self._held

    def pressed(self, action):
        return action in self._pressed

    def axis(self):
        dx = self.held("right") - self.held("left")
        dy = self.held("down") - self.held("up")
        mag = math.hypot(dx, dy)
        if mag:
            return dx / mag, dy / mag
        # analógico do celular: 360 graus e meia velocidade com o polegar perto do centro
        if self.analog and (abs(self.analog[0]) > 0.05 or abs(self.analog[1]) > 0.05):
            return self.analog
        return 0.0, 0.0
