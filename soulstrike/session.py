"""Configuração de uma partida escolhida nos menus."""
from dataclasses import dataclass, field

from . import theme

MODES = {
    "cpu": {"title": "DUELO CONTRA CPU", "soccer": False, "slots": 2},
    "duel": {"title": "DUELO LOCAL", "soccer": False, "slots": 2},
    "soccer1": {"title": "FUTEBOL 1 x 1", "soccer": True, "slots": 2},
    "soccer2": {"title": "FUTEBOL 2 x 2", "soccer": True, "slots": 4},
}


@dataclass
class SlotSetup:
    slot: int
    char: int = 0
    weapon: int = 0
    cpu: bool = False

    @property
    def label(self):
        return "CPU" if self.cpu else f"P{self.slot}"

    @property
    def name(self):
        return "CPU" if self.cpu else f"JOGADOR {self.slot}"

    @property
    def color(self):
        return theme.CPU_COLOR if self.cpu else theme.SLOT_COLORS[self.slot]


@dataclass
class Session:
    mode: str
    slots: list = field(default_factory=list)
    map_key: str = "arena_classica"
    difficulty: str = "normal"
    assist: str = "media"          # assistência do futebol: alta, media ou desligada

    @property
    def soccer(self):
        return MODES[self.mode]["soccer"]

    @property
    def title(self):
        return MODES[self.mode]["title"]

    @staticmethod
    def team_of(slot):
        return 0 if slot in (1, 3) else 1
