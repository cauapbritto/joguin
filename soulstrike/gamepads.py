"""Controles USB e Bluetooth (Xbox, PlayStation, genéricos).

Cada controle vira um jogador, na ordem em que foi conectado, a partir da vaga escolhida nas
opções (P1 ou P2). Para o resto do jogo um controle é igual ao celular: manda os mesmos nomes
de ação ("attack", "special"...) e um analógico de verdade.

Botões (nomes do Xbox; no PlayStation A = X, B = bola, X = quadrado, Y = triângulo):

    A       atacar / chutar / confirmar      B       esquiva / corte / voltar
    X       habilidade / passe               Y       trocar arma / super
    LB      marcar (futebol)                 RB      conduzir colado
    RT      correr (futebol)                 LT      esquiva
    START   pausa                            BACK    voltar nos menus
    analógico esquerdo ou direcional: mover e navegar
"""
import math

import pygame

from . import settings

DEADZONE = 0.22                 # analógico parado não fica andando sozinho
MENU_THRESHOLD = 0.6            # analógico tem que ir bem para o lado para contar como "seta"
TRIGGER_THRESHOLD = 0.5

# botão → ações do jogo
BUTTON_ACTIONS = {
    "a": ("attack", "confirm"),
    "b": ("dodge", "cancel"),
    "x": ("special",),
    "y": ("switch", "super"),
    "lb": ("mark",),
    "rb": ("dribble",),
    "rt": ("sprint",),
    "lt": ("dodge",),
    "start": ("pause",),
}
DIRECTION_ACTIONS = {
    "up": ("up", "weapon"), "down": ("down", "weapon"),
    "left": ("left", "char_left"), "right": ("right", "char_right"),
}
# nos menus (título, modos, opções) o controle vira teclas
MENU_KEYS = {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
             "a": pygame.K_RETURN, "start": pygame.K_RETURN, "b": pygame.K_ESCAPE, "back": pygame.K_ESCAPE}

# índices dos botões quando o SDL não reconhece o controle (layout do Xbox no Windows e no Linux)
_RAW_BUTTONS = {"a": 0, "b": 1, "x": 2, "y": 3, "lb": 4, "rb": 5, "back": 6, "start": 7}
_RAW_AXES = {"lx": 0, "ly": 1, "lt": 2, "rt": 5}


class _ControllerReader:
    """Controle reconhecido pelo SDL (mapeamento padrão: os botões estão sempre no mesmo lugar)."""

    BUTTONS = {"a": "CONTROLLER_BUTTON_A", "b": "CONTROLLER_BUTTON_B", "x": "CONTROLLER_BUTTON_X",
               "y": "CONTROLLER_BUTTON_Y", "lb": "CONTROLLER_BUTTON_LEFTSHOULDER",
               "rb": "CONTROLLER_BUTTON_RIGHTSHOULDER", "back": "CONTROLLER_BUTTON_BACK",
               "start": "CONTROLLER_BUTTON_START", "up": "CONTROLLER_BUTTON_DPAD_UP",
               "down": "CONTROLLER_BUTTON_DPAD_DOWN", "left": "CONTROLLER_BUTTON_DPAD_LEFT",
               "right": "CONTROLLER_BUTTON_DPAD_RIGHT"}
    AXES = {"lx": "CONTROLLER_AXIS_LEFTX", "ly": "CONTROLLER_AXIS_LEFTY",
            "lt": "CONTROLLER_AXIS_TRIGGERLEFT", "rt": "CONTROLLER_AXIS_TRIGGERRIGHT"}

    def __init__(self, controller):
        self.dev = controller
        self.name = controller.name

    def button(self, name):
        code = getattr(pygame, self.BUTTONS[name], None)
        return code is not None and bool(self.dev.get_button(code))

    def axis(self, name):
        code = getattr(pygame, self.AXES[name], None)
        return 0.0 if code is None else max(-1.0, self.dev.get_axis(code) / 32767)


class _JoystickReader:
    """Controle genérico: usa o layout do Xbox e o direcional (hat) para as setas."""

    def __init__(self, joystick):
        self.dev = joystick
        self.name = joystick.get_name()

    def button(self, name):
        if name in ("up", "down", "left", "right"):
            if not self.dev.get_numhats():
                return False
            hx, hy = self.dev.get_hat(0)
            return {"up": hy > 0, "down": hy < 0, "left": hx < 0, "right": hx > 0}[name]
        i = _RAW_BUTTONS[name]
        return i < self.dev.get_numbuttons() and bool(self.dev.get_button(i))

    def axis(self, name):
        i = _RAW_AXES[name]
        if i >= self.dev.get_numaxes():
            return 0.0
        value = self.dev.get_axis(i)
        if name in ("lt", "rt"):
            value = (value + 1) / 2              # gatilho solto = -1 no joystick cru
        return value


class Pad:
    """Estado de um controle: botões segurados, apertados neste quadro e o analógico."""

    def __init__(self, reader):
        self.reader = reader
        self.held = set()               # botões ("a", "up"...) segurados agora
        self.pressed = set()            # e os que foram apertados neste quadro
        self.stick = (0.0, 0.0)

    @property
    def name(self):
        return self.reader.name

    def update(self):
        r = self.reader
        x, y = r.axis("lx"), r.axis("ly")
        mag = math.hypot(x, y)
        if mag < DEADZONE:
            x = y = 0.0
        elif mag > 1:
            x, y = x / mag, y / mag
        self.stick = (x, y)
        held = {b for b in ("a", "b", "x", "y", "lb", "rb", "back", "start") if r.button(b)}
        for trigger in ("lt", "rt"):
            if r.axis(trigger) > TRIGGER_THRESHOLD:
                held.add(trigger)
        # setas: direcional ou analógico bem inclinado
        for d in ("up", "down", "left", "right"):
            if r.button(d):
                held.add(d)
        if x < -MENU_THRESHOLD:
            held.add("left")
        elif x > MENU_THRESHOLD:
            held.add("right")
        if y < -MENU_THRESHOLD:
            held.add("up")
        elif y > MENU_THRESHOLD:
            held.add("down")
        self.pressed = held - self.held
        self.held = held

    def axis(self):
        """Analógico para andar (o direcional também anda, nas 8 direções)."""
        if self.stick != (0.0, 0.0):
            return self.stick
        dx = ("right" in self.held) - ("left" in self.held)
        dy = ("down" in self.held) - ("up" in self.held)
        mag = math.hypot(dx, dy)
        return (dx / mag, dy / mag) if mag else (0.0, 0.0)

    def actions(self, buttons):
        out = set()
        for b in buttons:
            out.update(BUTTON_ACTIONS.get(b, ()))
            out.update(DIRECTION_ACTIONS.get(b, ()))
        return out


class Gamepads:
    """Todos os controles conectados. O jogo chama poll() uma vez por quadro."""

    def __init__(self, enabled=True):
        self.pads = []
        self.enabled = enabled
        self._controller = None
        if enabled:
            try:
                pygame.joystick.init()
                from pygame._sdl2 import controller
                controller.init()
                self._controller = controller
            except (ImportError, pygame.error):
                self._controller = None
            self.rescan()

    def rescan(self):
        """Controle entrou ou saiu: monta a lista de novo (na ordem do sistema)."""
        if not self.enabled:
            return
        pads = []
        for i in range(pygame.joystick.get_count()):
            try:
                if self._controller is not None and self._controller.is_controller(i):
                    reader = _ControllerReader(self._controller.Controller(i))
                else:
                    reader = _JoystickReader(pygame.joystick.Joystick(i))
            except pygame.error:
                continue
            pads.append(Pad(reader))
        self.pads = pads

    def handle(self, event):
        if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self.rescan()

    def first_slot(self):
        return 2 if settings.get("controle_comeca_no_p2") else 1

    def slot_of(self, index):
        slot = self.first_slot() + index
        return slot if slot <= 4 else None

    def slots(self):
        return {s for i in range(len(self.pads)) if (s := self.slot_of(i))}

    def poll(self):
        """(segurados, apertados, analógicos) no mesmo formato do celular: 'p1_attack'..."""
        held, pressed, axes = set(), set(), {}
        for i, pad in enumerate(self.pads):
            slot = self.slot_of(i)
            pad.update()
            if slot is None:
                continue
            prefix = f"p{slot}_"
            held.update(prefix + a for a in pad.actions(pad.held))
            pressed.update(prefix + a for a in pad.actions(pad.pressed))
            stick = pad.axis()
            if stick != (0.0, 0.0):
                axes[slot] = stick
        return held, pressed, axes

    def menu_events(self):
        """Botões apertados neste quadro como teclas (para as telas de menu que só leem o teclado)."""
        out = []
        for pad in self.pads:
            for button in pad.pressed:
                key = MENU_KEYS.get(button)
                if key is not None:
                    out.append(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0,
                                                  from_pad=True))
        return out
