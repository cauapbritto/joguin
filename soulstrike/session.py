"""Configuração de uma partida escolhida nos menus."""
from dataclasses import dataclass, field

from . import theme

MODES = {
    "cpu": {"title": "DUELO CONTRA CPU", "soccer": False, "slots": 2},
    "duel": {"title": "DUELO LOCAL", "soccer": False, "slots": 2},
    "soccer1": {"title": "FUTEBOL 1 x 1", "soccer": True, "slots": 2},
    "duel2": {"title": "DUELO 2 x 2", "soccer": False, "slots": 4, "teams": True},
    "soccer2": {"title": "FUTEBOL 2 x 2", "soccer": True, "slots": 4, "teams": True},
    "basket2": {"title": "BASQUETE 2 x 2", "soccer": True, "basket": True, "slots": 4, "teams": True},
    "campaign": {"title": "CAMPANHA", "soccer": False, "slots": 4},
    "treino": {"title": "TREINO", "soccer": False, "slots": 2},
    "treino_futebol": {"title": "TREINO DE FUTEBOL", "soccer": True, "slots": 2},
    "treino_basquete": {"title": "TREINO DE BASQUETE", "soccer": True, "basket": True, "slots": 4, "teams": True},
    # pênaltis com visão de frente (scenes/penalty.py): sem partida antes
    "penaltis": {"title": "DISPUTA DE PÊNALTIS", "soccer": True, "slots": 4, "teams": True, "penalty": True},
    "treino_penaltis": {"title": "TREINO DE PÊNALTIS", "soccer": True, "slots": 2, "penalty": True},
    "desafio_goleiro": {"title": "DESAFIO DO GOLEIRO", "soccer": True, "slots": 2, "penalty": True},
}

# Como as vagas formam os times nos modos 2 x 2 (escolhido no lobby)
TEAM_LAYOUTS = {
    "alternado": ((1, 3), (2, 4)),     # P1 e P2 (teclado) em times diferentes
    "juntos": ((1, 2), (3, 4)),        # P1 e P2 juntos (por exemplo, contra a CPU)
}
TEAM_LAYOUT_ORDER = ("alternado", "juntos")


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
    layout: str = "alternado"      # times no 2 x 2 (veja TEAM_LAYOUTS)
    weapon_pick: bool = False      # duelo: escolher as armas antes de cada round
    soccer_length: str = "3"       # futebol: "3", "5" ou "7" gols, ou "tempo" (config.SOCCER_LENGTHS)
    chapter: int = 1               # campanha: capítulo onde começa (2 só depois de zerar o 1)

    @property
    def soccer(self):
        return MODES[self.mode]["soccer"]

    @property
    def basket(self):
        """Basquete: usa o elenco, os uniformes e as teclas do futebol, mas é outra partida."""
        return MODES[self.mode].get("basket", False)

    @property
    def team_mode(self):
        """Dois times de dois (futebol 2 x 2 e duelo 2 x 2)."""
        return MODES[self.mode].get("teams", False)

    @property
    def penalty(self):
        """Disputa de pênaltis direto do menu (sem partida antes)."""
        return MODES[self.mode].get("penalty", False)

    @property
    def campaign(self):
        return self.mode == "campaign"

    @property
    def title(self):
        return MODES[self.mode]["title"]

    def team_of(self, slot):
        first, _ = TEAM_LAYOUTS.get(self.layout, TEAM_LAYOUTS["alternado"])
        return 0 if slot in first else 1

    def teammates(self, team):
        """Vagas de um time, em ordem."""
        return [s for s in (1, 2, 3, 4) if self.team_of(s) == team]
