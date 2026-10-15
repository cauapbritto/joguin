"""Ajudantes dos testes de futebol: partida sem janela e controle falso."""
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# progresso salvo dos testes vai para uma pasta temporária (não mexe no do jogador)
os.environ.setdefault("SOULSTRIKE_PROGRESS", os.path.join(tempfile.mkdtemp(prefix="soulstrike-"), "progresso.json"))

from soulstrike.ai import SoccerAI  # noqa: E402
from soulstrike.arena import Pitch  # noqa: E402
from soulstrike.game import Game  # noqa: E402
from soulstrike.matches import SoccerMatch  # noqa: E402
from soulstrike.session import Session, SlotSetup  # noqa: E402

_game = None


def game():
    global _game
    if _game is None:
        _game = Game(fullscreen=False, headless=True)
        _game.assets.load()
    return _game


class Parado(SoccerAI):
    def update(self, me, match):
        me.steer(0, 0)


class FakeInput:
    """Faz o papel do teclado/celular de um jogador humano, quadro a quadro."""

    def __init__(self):
        self._held = set()
        self._pressed = set()
        self.double_tap = None
        self.stick = (0.0, 0.0)

    def hold(self, *actions):
        for a in actions:
            if a not in self._held:
                self._pressed.add(a)
            self._held.add(a)

    def release(self, *actions):
        for a in actions:
            self._held.discard(a)

    def tap(self, action):
        self._pressed.add(action)

    def held(self, action):
        return action in self._held or action in self._pressed

    def pressed(self, action):
        return action in self._pressed

    def axis(self):
        return self.stick

    def end_frame(self):
        self._pressed.clear()


# referências no campo de futebol: linha do gol da direita (o time azul ataca para lá) e o meio
GOL_D = Pitch.goal_x(1)
MEIO = Pitch.MID_Y


def futebol(chars=(4, 2), humans=()):
    """Partida de futebol com todos parados, menos as vagas em `humans` (controle falso)."""
    g = game()
    slots = [SlotSetup(i + 1, char=c, cpu=(i + 1) not in humans) for i, c in enumerate(chars)]
    g.session = Session("soccer1" if len(chars) == 2 else "soccer2", slots)
    match = SoccerMatch(g, g.session)
    inputs = {}
    for f in match.fighters:
        if f.slot in humans:
            inputs[f.slot] = match.controllers[f] = FakeInput()
        else:
            match.controllers[f] = Parado()
    return match, inputs


def run(match, frames, inputs=()):
    for _ in range(frames):
        before = match.frame
        match.update()
        if match.frame != before:          # quadro de pausa de impacto não consome o toque
            for inp in (inputs.values() if isinstance(inputs, dict) else inputs):
                inp.end_frame()
