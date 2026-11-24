"""Reações rápidas do app (GG, KKKK, VEM! e palmas): um balão em cima do boneco por quase dois
segundos, com um somzinho quando chega.

O app manda pelo /api/reacao (no máximo uma por segundo por jogador) e o hub guarda a última de
cada vaga (``hub.reaction``). Quem desenha o jogador chama ``draw`` com a ponta do balão: o boneco
na partida (fighter.draw_overlay), o cartão do lobby e o da escolha de personagem.

Os desenhos de ``ICONS`` são os mesmos dos botões do app: ``tools/icones_reacoes.py`` gera
os PNG de android/app/src/main/res/drawable-nodpi/ a partir daqui.
"""
import math

import pygame

from . import theme
from .net.remote import CALL_SECONDS, CALL_TEXT, CALLS, REACTION_SECONDS, REACTIONS, hub

# cores dos desenhos (a mesma letra vale no app)
PALETTE = {
    "K": (40, 32, 40), "W": (255, 255, 255), "Y": (250, 210, 70), "y": (200, 150, 40),
    "R": (220, 70, 60), "r": (150, 40, 40), "S": (244, 196, 150), "s": (206, 146, 104),
    "B": (120, 200, 255),
}

# desenho de cada reação (12x12; as palmas com 13 de largura)
ICONS = {
    "gg": (
        "..KKKKKKKK..",
        "KKKWYYYYyKKK",
        "K.KWYYYYyK.K",
        "K.KYYYYYyK.K",
        ".KKYYYYYyKK.",
        "...KYYYyK...",
        "....KYyK....",
        ".....KK.....",
        ".....KK.....",
        "...KKKKKK...",
        "...KyyyyK...",
        "...KKKKKK...",
    ),
    "kkk": (
        "...KKKKKK...",
        "..KYYYYYYK..",
        ".KYYYYYYYYK.",
        "KYYKYYYYKYYK",
        "KYKYKYYKYKYK",
        "KYYYYYYYYYYK",
        "KYKKKKKKKKYK",
        "KYKRRRRRRKYK",
        ".KYKRRRRKYK.",
        "..KYKKKKYK..",
        "...KKKKKK...",
        "............",
    ),
    "vem": (
        ".....K......",
        "....KRK.....",
        "....KRRK....",
        "...KRRRK.K..",
        "..KRRYRRKRK.",
        "..KRYYRRRRK.",
        ".KRRYYYRRRK.",
        ".KRYYWYYRRK.",
        ".KRYWWWYRK..",
        "..KRYWYRRK..",
        "...KRRRRK...",
        "....KKKK....",
    ),
    "palmas": (                      # 13 de largura: a linha onde as mãos se encostam fica no meio
        "B...K...K...B",
        ".B.KSK.KSK.B.",
        "...KSK.KSK...",
        "..KSSKKKSSK..",
        "..KSSSKSSSK..",
        ".KSSSSKSSSSK.",
        "KSKSSSKSSSKSK",
        "KSSKSsKsSKSSK",
        ".KSSSsKsSSSK.",
        "..KSSsKsSSK..",
        "...KSSKSSK...",
        "....KKKKK....",
    ),
}
# texto do balão, cor do texto, som e volume de cada reação
STYLE = {
    "gg": ("GG", (46, 140, 70), "notificacao", 0.35),
    "kkk": ("KKKK", (190, 130, 20), "bip", 0.3),
    "vem": ("VEM!", (200, 56, 46), "assobio", 0.35),
    "palmas": ("BOA!", (176, 104, 50), "torcida_abafa", 0.3),
}
BUBBLE = (244, 238, 222)
INK = (40, 32, 40)

_cache = {}


def icon(key, scale=2):
    """O desenho da reação como Surface (com transparência), em escala inteira."""
    ck = (key, scale)
    if ck not in _cache:
        rows = ICONS[key]
        surf = pygame.Surface((len(rows[0]) * scale, len(rows) * scale), pygame.SRCALPHA)
        for y, line in enumerate(rows):
            for x, ch in enumerate(line):
                color = PALETTE.get(ch)
                if color is not None:
                    surf.fill(color, (x * scale, y * scale, scale, scale))
        _cache[ck] = surf
    return _cache[ck]


def play(assets, kind):
    """O somzinho de quando a reação chega (uma vez por reação)."""
    if 0 <= kind < len(REACTIONS):
        _, _, sound, volume = STYLE[REACTIONS[kind]]
        assets.play(sound, volume)


def draw(screen, ui, kind, age, x, y):
    """Balão da reação com a pontinha em (x, y): aparece crescendo, balança um pouco e some no fim."""
    if not 0 <= kind < len(REACTIONS):
        return
    key = REACTIONS[kind]
    text, color, _, _ = STYLE[key]
    img = icon(key, 2)
    if key == "palmas" and int(age * 8) % 2:           # as mãos batendo
        img = pygame.transform.scale(img, (img.get_width() - 2, img.get_height()))
    _bubble(screen, ui, img, text, color, INK, age, REACTION_SECONDS, x, y)


def draw_call(screen, ui, kind, age, x, y, color=INK):
    """Balão da frase para a equipe (PASSA!, AJUDA!...): só o texto, com a borda na cor do time."""
    if not 0 <= kind < len(CALLS):
        return
    _bubble(screen, ui, None, CALL_TEXT[CALLS[kind]], INK, color, age, CALL_SECONDS, x, y)


def _bubble(screen, ui, img, text, color, line, age, seconds, x, y):
    pop = min(1.0, age / 0.12)                         # cresce no começo
    fade = max(0.0, min(1.0, (seconds - age) / 0.3))
    words = ui.assets.text(text, theme.XS, color) if text else None
    iw = img.get_width() if img is not None else 0
    ih = img.get_height() if img is not None else (words.get_height() if words else 8)
    w = iw + (words.get_width() + (6 if img is not None else 0) if words else 0) + 12
    h = ih + 8
    thick = 1 if line == INK else 2
    bubble = pygame.Surface((w + 2, h + 8), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, w, h)
    pygame.draw.rect(bubble, theme.SHADOW, rect.move(2, 2))
    pygame.draw.rect(bubble, BUBBLE, rect)
    pygame.draw.rect(bubble, line, rect, thick)
    tip = w // 2
    pygame.draw.polygon(bubble, BUBBLE, [(tip - 5, h - 1), (tip + 5, h - 1), (tip, h + 6)])
    pygame.draw.line(bubble, line, (tip - 5, h - 1), (tip, h + 6), thick)
    pygame.draw.line(bubble, line, (tip + 5, h - 1), (tip, h + 6), thick)
    if img is not None:
        bubble.blit(img, img.get_rect(midleft=(6, h // 2)))
    if words is not None:
        left = 6 + iw + (6 if img is not None else 0)
        bubble.blit(words, words.get_rect(midleft=(left, h // 2)))
    if pop < 1.0:
        size = (max(1, round(bubble.get_width() * (0.6 + 0.4 * pop))),
                max(1, round(bubble.get_height() * (0.6 + 0.4 * pop))))
        bubble = pygame.transform.scale(bubble, size)
    if fade < 1.0:
        bubble.set_alpha(round(255 * fade))
    bob = round(2 * math.sin(age * 9)) if age < 0.6 else 0
    rect = bubble.get_rect(midbottom=(x, y - 2 + bob))
    rect.x = max(4, min(screen.get_width() - rect.w - 4, rect.x))
    screen.blit(bubble, rect)


def draw_for(screen, ui, slot, x, y, team=None):
    """Desenha a reação (ou a frase para a equipe) desta vaga, a mais nova que estiver no ar
    (ponta do balão em x, y). A frase tem a borda na cor do time (ou do jogador, na campanha)."""
    if not slot:
        return
    r = hub.reaction(slot)
    c = hub.team_call_of(slot)
    if c is not None and (r is None or c[1] <= r[1]):
        color = theme.TEAM_COLORS.get(team) or theme.SLOT_COLORS.get(slot, INK)
        draw_call(screen, ui, c[0], c[1], x, y, color)
    elif r is not None:
        draw(screen, ui, r[0], r[1], x, y)
