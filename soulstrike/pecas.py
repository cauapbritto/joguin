"""Peças do cenário desenhadas como os heróis (tools/gerar_pecas.py → assets/pecas): os vendedores e
ferreiros de cada capítulo, as bancas em duas camadas, o baú, o armário e a fogueira.

Sem o arquivo (ou sem o pygame.image conseguir ler), ``image`` devolve None e quem chamou desenha
do jeito antigo."""
import pygame

from . import config

PECAS_DIR = config.ASSETS_DIR / "pecas"

# quem atende cada banca em cada capítulo
NPCS = {
    ("loja", 1): "mascate", ("ferreiro", 1): "ferreiro",
    ("loja", 2): "tecnico", ("ferreiro", 2): "soldador",
    ("loja", 3): "atendente", ("ferreiro", 3): "esteticista",
    ("loja", 4): "mordomo", ("ferreiro", 4): "ourives",
}
NPC_DX = {("loja", 2): 32}      # o técnico fica do lado da máquina de venda, não no meio

_cache = {}


def chapter_of(chapter):
    """O capítulo cuja arte vale (fora da campanha, a do capítulo 1)."""
    return chapter if chapter in (1, 2, 3, 4) else 1


def image(name):
    if name not in _cache:
        img = None
        path = PECAS_DIR / f"{name}.png"
        if path.is_file():
            try:
                img = pygame.image.load(str(path))
                if pygame.display.get_surface() is not None:
                    img = img.convert_alpha()
            except pygame.error:
                img = None
        _cache[name] = img
    return _cache[name]


def npc_frame(kind, chapter, pose="parado", i=0):
    name = NPCS.get((kind, chapter_of(chapter)))
    return image(f"npc_{name}_{pose}{i}") if name else None


def shadow(w, h, alpha=80):
    """Sombra translúcida no chão (elipse)."""
    key = ("sombra", w, h, alpha)
    if key not in _cache:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
        _cache[key] = s
    return _cache[key]
