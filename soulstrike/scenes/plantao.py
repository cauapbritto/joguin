"""PLANTÃO SOUL STRIKE: a tela de novidades como um telejornal.

Cada versão é uma "edição" e cada página de novidades.py é uma "notícia". A tela abre sozinha
quando o jogo é atualizado (NewsScene, com a abertura dos âncoras e todas as versões que o jogador
ainda não viu) e fica em OPÇÕES > NOVIDADES como ARQUIVO de todas as edições (ArchiveScene).

Partes da tela: a TV com a imagem "ao vivo" e a tarja com o título, o texto da notícia embaixo,
o espelho NESTA EDIÇÃO à direita (com ✓ no que já viu), o celular que acompanha e vira a página,
e o letreiro das edições anteriores. Trocar de notícia passa um chuvisco de troca de canal.
"""
import math
import os

import pygame

from .. import config, novidades, theme
from ..updater import parse_version
from .menus import NEWS_SCENES, _InfoScene, cover_image

W, H = config.SCREEN_W, config.SCREEN_H
RED = (214, 52, 52)
RED_D = (120, 24, 30)
TICK = (18, 15, 24)

TV = pygame.Rect(32, 66, 520, 292)            # a imagem "ao vivo" (16:9)
SIDE = pygame.Rect(584, 66, 344, 300)         # NESTA EDIÇÃO + NO SEU CELULAR
BODY = pygame.Rect(32, 378, 528, 116)         # o texto da notícia
TICKER = pygame.Rect(0, 494, W, 20)

MAX_AUTO = 6              # sozinha, mostra até 6 versões não vistas (as mais novas)
STATIC_FRAMES = 14        # chuvisco ao trocar de notícia
SLIDE_FRAMES = 16         # a tarja entra deslizando
REVEAL_EVERY = 14         # na abertura, uma manchete a cada tanto de quadros

# assunto de cada cena antiga: o que vai na etiqueta da tarja e a cor dela
TOPICS = {
    "campanha": ("CAMPANHA", theme.MOSS), "celular": ("CELULAR", theme.SKY), "futebol": ("FUTEBOL", (96, 200, 120)),
    "basquete": ("BASQUETE", theme.EMBER), "jogo": ("JOGO", theme.BRASS), "plantao": ("PLANTÃO", RED),
}
SCENE_TOPIC = {
    "almas": "campanha", "loja": "campanha", "lag": "campanha", "perigos": "campanha", "chefao_lag": "campanha",
    "armas_lag": "campanha", "clepalovers": "campanha", "clinica": "campanha", "oi_sumido": "campanha",
    "mansao": "campanha", "iara": "campanha", "casa": "campanha", "computador": "campanha", "cantos": "campanha",
    "corredores": "campanha",
    "hud": "celular", "controle": "celular",
    "futebol": "futebol", "penalti": "futebol", "disputa": "futebol", "bate": "futebol", "agarra": "futebol",
    "enterrada": "basquete", "ultra": "basquete",
    "modos": "jogo", "novidades": "jogo", "coroa": "jogo",
}
# imagens feitas para o plantão (as demais notícias usam a cena antiga, do tamanho da TV)
TV_BY_TITLE = {
    ("1.19.0", "O CELULAR VIBRA"): "vibra",
    ("1.19.0", "CHAMADA NA PORTA"): "porta",
    ("1.18.0", "A FASE VAI EM FRENTE"): "fase",
    ("1.18.0", "TODOS JUNTOS NA PORTA"): "porta",
    ("1.18.0", "INICIAR BATALHA"): "batalha",
    ("1.14.0", "CAPÍTULO 4: MANSÃO DO CARIMBO"): "mansao",
}
TV_TOPIC = {"vibra": "celular", "porta": "campanha", "fase": "campanha", "batalha": "campanha",
            "mansao": "campanha", "estudio": "plantao"}


class Story:
    """Uma notícia: a página de novidades.py já cortada no tamanho do texto da tela."""

    def __init__(self, version, title, scene, lines, tv=None, part=None):
        self.version, self.title, self.scene, self.lines = version, title, scene, lines
        self.tv = tv or TV_BY_TITLE.get((version, title))
        self.part = part                         # (n, total) quando a página foi dividida

    @property
    def label(self):
        return f"{self.title} ({self.part[0]}/{self.part[1]})" if self.part else self.title

    @property
    def topic(self):
        key = TV_TOPIC.get(self.tv) if self.tv else SCENE_TOPIC.get(self.scene)
        return TOPICS.get(key or "jogo", TOPICS["jogo"])


def _tv_of(version, title):
    entry = novidades.NEWS.get(version)
    if isinstance(entry, list):
        for page in entry:
            if isinstance(page, dict) and page.get("title") == title:
                return page.get("tv")
    return None


def stories_of(ui, version, entry):
    """As notícias de uma versão. Página com texto demais para a tela vira duas (ou mais)."""
    out = []
    for _, title, scene, lines in novidades.pages_of(version, entry):
        chunks, chunk, height = [], [], 0
        for line in lines:
            h = _line_height(ui, line)
            if chunk and height + h - 8 > BODY.h:
                chunks.append(chunk)
                chunk, height = [], 0
            chunk.append(line)
            height += h
        chunks.append(chunk)
        tv = _tv_of(version, title)
        for i, part in enumerate(chunks):
            out.append(Story(version, title, scene or _guess_scene(part), part, tv,
                             (i + 1, len(chunks)) if len(chunks) > 1 else None))
    return out


# versões antigas (só frases, sem cena): a imagem vem do assunto da primeira frase que casar
GUESS = (("basquete", "enterrada"), ("enterrada", "enterrada"), ("pênalti", "penalti"), ("futebol", "futebol"),
         ("gol", "futebol"), ("campanha", "almas"), ("loja", "loja"), ("arma", "loja"))


def _guess_scene(lines):
    for line in lines:
        low = line.lower()
        for word, scene in GUESS:
            if word in low:
                return scene
    return None


def _line_height(ui, line):
    return len(ui.wrap(line, theme.XS, BODY.w - 16)) * 15 + 8


# ── peças da tela ────────────────────────────────────────────────────────
_CACHE = {}


def _scanlines(size):
    key = ("scan", size)
    if key not in _CACHE:
        layer = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, size[1], 2):
            layer.fill((0, 0, 0, 34), (0, y, size[0], 1))
        # vidro do tubo: cantos escuros e um reflexo fraco no alto
        for i in range(14):
            a = round(110 * (1 - i / 14) ** 2)
            pygame.draw.rect(layer, (0, 0, 0, a), (i, i, size[0] - 2 * i, size[1] - 2 * i), 1, border_radius=18)
        for y in range(40):
            layer.fill((255, 255, 255, round(10 * (1 - y / 40))), (0, y + 4, size[0], 1))
        _CACHE[key] = layer
    return _CACHE[key]


def _noise(size, n):
    """Chuvisco de TV: alguns quadros prontos, em meia resolução (custa pouco por quadro)."""
    key = ("noise", size, n % 4)
    if key not in _CACHE:
        w, h = size[0] // 2, size[1] // 2
        grey = os.urandom(w * h)
        rgb = bytes(b for v in grey for b in (30 + v * 200 // 255,) * 3)
        img = pygame.image.frombuffer(rgb, (w, h), "RGB")
        _CACHE[key] = pygame.transform.scale(img, size)
    return _CACHE[key]


def tv_frame(screen, ui, rect):
    ui.panel(screen, rect.inflate(16, 16), fill=(26, 22, 34), border=theme.LINE_HI)
    screen.fill((4, 3, 6), rect.inflate(4, 4))


def live_tag(screen, ui, rect, ticks, text):
    on = (ticks // 30) % 2 == 0
    tag = pygame.Rect(rect.x + 12, rect.y + 12, ui.assets.text_width(text, theme.XS) + 22, 16)
    screen.fill(RED_D, tag.move(0, 2))
    screen.fill(RED, tag)
    pygame.draw.circle(screen, (255, 255, 255) if on else (255, 160, 160), (tag.x + 8, tag.centery), 3)
    ui.text(screen, text, theme.XS, (255, 255, 255), (tag.x + 15, tag.centery), anchor="midleft", shadow=False)


def lower_third(screen, ui, rect, kicker, title, color, slide=1.0):
    """Tarja de telejornal: a etiqueta na cor do assunto e o título grande, entrando da esquerda."""
    size = theme.M
    tw = ui.assets.text(title, size, theme.BONE).get_width() + 28
    if tw > rect.w - 36:                                 # título comprido: letra menor
        size = theme.S
        tw = ui.assets.text(title, size, theme.BONE).get_width() + 28
    kw = ui.assets.text(kicker, theme.XS, theme.INK).get_width() + 16
    ease = 1 - (1 - max(0.0, min(1.0, slide))) ** 3
    x = rect.x + 18 - round((1 - ease) * (max(tw, kw) + 40))
    y = rect.bottom - 58
    clip = screen.get_clip()
    screen.set_clip(rect)
    k = pygame.Rect(x, y, kw, 16)
    bar = pygame.Rect(x, y + 16, max(tw, kw + 40), 34)
    screen.fill((0, 0, 0), bar.move(3, 3))
    screen.fill(color, k)
    ui.text(screen, kicker, theme.XS, theme.INK, k.center, shadow=False)
    screen.fill(theme.INK, bar)
    screen.fill(color, (bar.x, bar.y, 4, bar.h))
    screen.fill(theme.INK_3, (bar.x + 4, bar.y, bar.w - 4, 1))
    ui.text(screen, title, size, theme.BONE, (bar.x + 16, bar.centery + 1), anchor="midleft")
    screen.set_clip(clip)


def header(screen, ui, ticks, edition, right):
    on = (ticks // 30) % 2 == 0
    pill = pygame.Rect(32, 22, 86, 22)
    screen.fill(RED_D, pill.move(0, 2))
    screen.fill(RED, pill)
    pygame.draw.circle(screen, (255, 255, 255) if on else (255, 170, 170), (pill.x + 11, pill.centery), 4)
    ui.text(screen, "PLANTÃO", theme.XS, (255, 255, 255), (pill.x + 20, pill.centery), anchor="midleft", shadow=False)
    r = ui.text(screen, "SOUL STRIKE", theme.S, theme.BRASS, (pill.right + 12, pill.centery + 1), anchor="midleft")
    screen.fill(theme.LINE, (r.right + 12, pill.y + 4, 1, pill.h - 8))
    ui.text(screen, edition, theme.XS, theme.BONE, (r.right + 26, pill.centery + 1), anchor="midleft", shadow=False)
    ui.text(screen, right, theme.XS, theme.MUTED, (W - 32, pill.centery + 1), anchor="midright", shadow=False)
    screen.fill(theme.LINE, (32, 52, W - 64, 1))


def body(screen, ui, rect, lines, age=99):
    y = rect.y
    for i, line in enumerate(lines):
        if age < 6 + i * 4:                       # as frases entram uma depois da outra
            break
        screen.fill(theme.BRASS, (rect.x, y + 4, 6, 2))
        y = ui.paragraph(screen, line, theme.XS, theme.BONE, (rect.x + 16, y), rect.w - 16, spacing=15) + 8


def ticker(screen, ui, text, offset):
    if not text:
        return
    screen.fill(TICK, TICKER)
    screen.fill(theme.LINE, (0, TICKER.y, W, 1))
    label_text = "EDIÇÕES ANTERIORES"
    label = pygame.Rect(0, TICKER.y + 1, ui.assets.text_width(label_text, theme.XS) + 40, TICKER.h - 1)
    span = ui.assets.text_width(text, theme.XS) + 80
    clip = screen.get_clip()
    screen.set_clip(pygame.Rect(label.right, TICKER.y, W - label.right, TICKER.h))
    x = label.right + 12 - offset % span
    while x < W:
        ui.text(screen, text, theme.XS, theme.MUTED, (x, TICKER.centery + 1), anchor="midleft", shadow=False)
        x += span
    screen.set_clip(clip)
    screen.fill(theme.BRASS, label)
    ui.text(screen, label_text, theme.XS, theme.INK, label.center, shadow=False)


def phone_card(screen, ui, title, index, total, ticks):
    """NO SEU CELULAR: qualquer celular conectado vira a notícia e mostra o resumo."""
    top = SIDE.bottom - 92
    ui.text(screen, "NO SEU CELULAR", theme.XS, theme.MUTED, (SIDE.x, top), anchor="midleft", shadow=False)
    screen.fill(theme.LINE, (SIDE.x + 118, top, SIDE.w - 118, 1))
    ph = pygame.Rect(SIDE.x, top + 16, 196, 92)
    pygame.draw.rect(screen, (0, 0, 0), ph.move(3, 3), border_radius=12)
    pygame.draw.rect(screen, (40, 36, 50), ph, border_radius=12)
    pygame.draw.rect(screen, theme.LINE_HI, ph, 2, border_radius=12)
    scr = ph.inflate(-22, -14)
    screen.fill(theme.INK, scr)
    screen.fill(RED, (scr.x, scr.y, scr.w, 2))
    count = f"PLANTÃO · {index}/{total}" if index else "PLANTÃO · ABERTURA"
    ui.text(screen, count, theme.XS, theme.MUTED, (scr.centerx, scr.y + 11), shadow=False)
    while ui.assets.text_width(title, theme.XS) > scr.w - 10 and len(title) > 4:
        title = title[:-4].rstrip() + "..."
    ui.text(screen, title, theme.XS, theme.BRASS, (scr.centerx, scr.y + 30), shadow=False)
    for i, (label, x) in enumerate((("<", scr.x + 30), ("PULAR", scr.centerx), (">", scr.right - 30))):
        b = pygame.Rect(0, 0, 44 if i == 1 else 30, 18)
        b.center = (x, scr.bottom - 15)
        lit = i == 2 and (ticks // 40) % 2 == 0
        screen.fill(theme.LINE if lit else theme.INK_3, b)
        pygame.draw.rect(screen, theme.LINE_HI, b, 1)
        ui.text(screen, label, theme.XS, theme.BONE, b.center, shadow=False)
    ui.paragraph(screen, "Qualquer celular vira a notícia, e o resumo fica lá para ler com calma.",
                 theme.XS, theme.MUTED, (ph.right + 14, ph.y + 8), SIDE.right - ph.right - 14, spacing=14)


# ── as imagens "ao vivo" ────────────────────────────────────────────────
class _Cam:
    def __init__(self, x=0, y=0):
        self.x, self.y, self.zoom = x, y, 1


def _big(img, k):
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k)) if k != 1 else img


def actor(screen, ui, name, x, y, direction="frente", kind="parado", i=0, k=1, slot=None, flash=False):
    sprites = ui.assets.sprites
    if name not in sprites:
        return pygame.Rect(x, y, 0, 0)
    img = _big(sprites[name].pose(direction, kind, i), k)
    pygame.draw.ellipse(screen, (8, 6, 12), (x - 14 * k, y - 4 * k, 28 * k, 8 * k))
    if flash:
        img = img.copy()
        img.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGB_ADD)
    r = img.get_rect(midbottom=(x, y + 2))
    screen.blit(img, r)
    if slot:
        ui.text(screen, f"P{slot}", theme.XS, theme.SLOT_COLORS[slot], (x, r.y - 6))
    return r


def _cover(screen, ui, key, rect):
    try:
        screen.blit(cover_image(ui.assets, key, rect.size), rect)
    except Exception:                                    # mapa que não carregou: fundo liso
        screen.fill((20, 18, 28), rect)


def tv_estudio(screen, ui, rect, t, edition=""):
    """Abertura: a bancada do plantão, dois âncoras e o telão com o logo entre eles."""
    screen.fill((16, 12, 26), rect)
    for i in range(7):                                   # luzes do estúdio no teto
        x = rect.x + 40 + i * (rect.w - 80) // 6
        pygame.draw.circle(screen, (60, 50, 80), (x, rect.y + 10), 5)
        lit = (255, 230, 170) if (t // 20 + i) % 9 else (255, 255, 230)
        pygame.draw.circle(screen, lit, (x, rect.y + 10), 2)
    wall = pygame.Rect(0, 0, 228, 128)
    wall.midtop = (rect.centerx, rect.y + 30)
    screen.fill((44, 38, 58), wall.inflate(10, 10))
    _cover(screen, ui, "chapter4", wall)
    shade = pygame.Surface(wall.size, pygame.SRCALPHA)
    shade.fill((10, 6, 20, 150))
    screen.blit(shade, wall.topleft)
    ui.logo(screen, (wall.centerx, wall.centery - 10), theme.M)
    if edition:
        ui.text(screen, edition, theme.XS, theme.BRASS, (wall.centerx, wall.bottom - 22))
    floor = pygame.Rect(rect.x, rect.y + 170, rect.w, rect.h - 170)
    screen.fill((30, 24, 42), floor)
    for x in range(rect.x - 40, rect.right + 40, 32):
        pygame.draw.line(screen, (40, 33, 54), (x, floor.y), (x + (x - rect.centerx) // 3, floor.bottom), 1)
    talk = (t // 90) % 2                                 # os âncoras se revezam: quem fala balança
    for side, name in ((-1, "cauanzera"), (1, "aryel")):
        bob = round(math.sin(t * 0.25)) if talk == (side > 0) else 0
        actor(screen, ui, name, rect.centerx + side * 172, rect.y + 222 + bob, "frente", "parado", 0, k=2)
    desk = pygame.Rect(rect.x + 40, rect.y + 176, rect.w - 80, 50)
    screen.fill((8, 6, 12), desk.move(0, 6))
    screen.fill((52, 44, 70), desk)
    screen.fill((90, 80, 112), (desk.x, desk.y, desk.w, 4))
    screen.fill(theme.BRASS, (desk.x, desk.y + 4, desk.w, 2))
    screen.fill((40, 34, 54), (desk.x, desk.bottom - 8, desk.w, 8))
    for side in (-1, 1):                                 # papéis na bancada
        screen.fill(theme.BONE, (rect.centerx + side * 172 - 10, desk.y - 3, 20, 4))


def _portal(screen, cx, cy, t):
    halo = pygame.Surface((180, 220), pygame.SRCALPHA)
    for r in range(90, 0, -6):
        pygame.draw.ellipse(halo, (170, 110, 250, int(16 * (1 - r / 90))), (90 - r * 0.7, 110 - r, r * 1.4, r * 2))
    screen.blit(halo, (cx - 90, cy - 110), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.ellipse(screen, (20, 8, 32), (cx - 34, cy - 56, 68, 112))
    for k in range(4):
        pygame.draw.ellipse(screen, (120 + 30 * k, 70 + 24 * k, 220 + 8 * k),
                            (cx - 34 + k * 5, cy - 56 + k * 8, (34 - k * 5) * 2, (56 - k * 8) * 2), 2)
    for k in range(8):
        a = t * 0.1 + k * math.tau / 8
        screen.fill((240, 220, 255), (round(cx + math.cos(a) * 26) - 1, round(cy + math.sin(a) * 44) - 1, 3, 3))


def _props(*items):
    for p in items:
        for _ in range(40):
            p.age = getattr(p, "age", 0) + 1
    return items


def tv_fase(screen, ui, rect, t):
    """A FASE VAI EM FRENTE: o grupo passa pelo corredor (baú, fogueira, loja) até o portal."""
    from ..dungeon import Campfire, Chest
    from ..market import Stall
    _cover(screen, ui, "campanha", rect)
    cam = _Cam(-rect.x, -rect.y)
    for p in _props(Chest(70, 84), Stall("loja", 270, 96), Campfire(110, 170)):
        p.age += t
        p.draw(screen, cam)
    _portal(screen, rect.x + 450, rect.y + 136, t)
    walk = (t * 0.6) % 60
    for i, (name, dx, dy) in enumerate((("cauanzera", 250, 200), ("aryel", 310, 186), ("borba", 196, 222),
                                        ("albeguinio", 362, 214))):
        actor(screen, ui, name, rect.x + dx - 30 + round(walk), rect.y + dy, "direita", "andar", t // 6 + i, slot=i + 1)
    for x in range(rect.x + 150, rect.x + 400, 22):
        screen.fill(theme.BRASS, (x, rect.y + 228, 10, 2))
    ui.arrow(screen, (rect.x + 404, rect.y + 229), "right", 5, theme.BRASS)


def _phone_upright(screen, ui, center, t, label, shake=True):
    dx = (3 if (t // 2) % 2 else -3) if shake else 0
    ph = pygame.Rect(0, 0, 96, 168)
    ph.center = (center[0] + dx, center[1])
    pygame.draw.rect(screen, (0, 0, 0), ph.move(4, 4), border_radius=14)
    pygame.draw.rect(screen, (40, 36, 50), ph, border_radius=14)
    pygame.draw.rect(screen, theme.LINE_HI, ph, 2, border_radius=14)
    scr = ph.inflate(-14, -30)
    screen.fill(theme.INK, scr)
    screen.fill(theme.BLOOD, (scr.x, scr.y, scr.w, 3))
    ui.text(screen, "P1", theme.XS, theme.SLOT_COLORS[1], (scr.centerx, scr.y + 14))
    pygame.draw.circle(screen, theme.INK_3, (scr.centerx, scr.bottom - 30), 18)
    pygame.draw.circle(screen, theme.SLOT_COLORS[1], (scr.centerx, scr.bottom - 30), 18, 2)
    ui.text(screen, label, theme.XS, theme.BONE, (scr.centerx, scr.centery - 10))
    if shake:
        for side in (-1, 1):
            for k in range(3):
                x = ph.centerx + side * (ph.w // 2 + 10 + k * 9)
                pygame.draw.arc(screen, theme.BRASS, (x - 8, ph.centery - 22 - k * 6, 16, 44 + k * 12),
                                -math.pi / 2 if side > 0 else math.pi / 2,
                                math.pi / 2 if side > 0 else 3 * math.pi / 2, 2)
    return ph


def tv_vibra(screen, ui, rect, t):
    """O CELULAR VIBRA: o herói leva o golpe na arena e, ao lado, o celular treme."""
    _cover(screen, ui, "duelos", rect)
    k = t % 90
    hit = 30 <= k < 52
    hx, hy = rect.x + 150, rect.y + 214
    actor(screen, ui, "matador", hx + 120 - (8 if hit else 0), hy, "esquerda", "ataque" if 22 <= k < 40 else "parado",
          k // 6, k=2)
    actor(screen, ui, "guerreiro", hx - (6 if hit else 0), hy, "direita", "dano" if hit else "parado", 0, k=2,
          flash=hit and k % 6 < 3)
    if hit:
        for a in range(0, 360, 45):
            r = math.radians(a)
            pygame.draw.line(screen, (255, 240, 200), (hx + 40 + math.cos(r) * 14, hy - 80 + math.sin(r) * 14),
                             (hx + 40 + math.cos(r) * 30, hy - 80 + math.sin(r) * 30), 2)
        ui.text(screen, "-18", theme.M, theme.BLOOD, (hx + 4, hy - 160 - (k - 30)))
    _phone_upright(screen, ui, (rect.right - 92, rect.centery - 18), t, "VIBRA", shake=hit)


def tv_porta(screen, ui, rect, t):
    """TODOS JUNTOS NA PORTA: três heróis na área da porta, a contagem e o celular chamando quem falta."""
    _cover(screen, ui, "chapter4", rect)
    area = pygame.Rect(rect.x + 150, rect.y + 76, 200, 140)
    layer = pygame.Surface(area.size, pygame.SRCALPHA)
    layer.fill((*theme.BRASS, 40 + round(20 * math.sin(t * 0.15))))
    screen.blit(layer, area.topleft)
    for i in range(0, area.w, 16):
        screen.fill(theme.BRASS, (area.x + i, area.y, 8, 2))
        screen.fill(theme.BRASS, (area.x + i, area.bottom - 2, 8, 2))
    for i in range(0, area.h, 16):
        screen.fill(theme.BRASS, (area.x, area.y + i, 2, 8))
        screen.fill(theme.BRASS, (area.right - 2, area.y + i, 2, 8))
    door = pygame.Rect(area.centerx - 30, area.y - 46, 60, 60)
    screen.fill((20, 16, 26), door)
    pygame.draw.rect(screen, theme.LINE_HI, door, 3)
    for i, (name, dx, dy) in enumerate((("cauanzera", 50, 112), ("aryel", 100, 100), ("borba", 150, 116))):
        actor(screen, ui, name, area.x + dx, area.y + dy, "costas", "parado", 0, slot=i + 1)
    k = t % 150                                          # o P4 chega e a contagem corre
    x4 = rect.x + 40 + min(1.0, k / 70) * 110
    actor(screen, ui, "albeguinio", round(x4), area.y + 132, "direita", "andar", t // 6, slot=4)
    if k >= 70:
        n = 2 - min(2, (k - 70) // 30)
        ui.text(screen, str(n) if n else "VAI!", theme.L, theme.BRASS, (door.centerx, door.centery))
    else:
        _phone_upright(screen, ui, (rect.right - 92, rect.centery - 18), t, "CHAMANDO", shake=(k // 30) % 2 == 0)


def tv_batalha(screen, ui, rect, t):
    """INICIAR BATALHA: o grupo se arruma, alguém aperta o botão e os inimigos saem da sombra."""
    _cover(screen, ui, "campanha", rect)
    k = t % 160
    pressed = k >= 70
    btn = pygame.Rect(0, 0, 70, 26)
    btn.center = (rect.x + 150, rect.y + 92)
    screen.fill((10, 8, 12), btn.move(0, 5))
    screen.fill(theme.BLOOD if pressed else (150, 40, 40), btn.move(0, 3 if pressed else 0))
    ui.text(screen, "INICIAR", theme.XS, theme.BONE, btn.move(0, 3 if pressed else 0).center, shadow=False)
    actor(screen, ui, "cauanzera", btn.centerx, btn.bottom + 86, "costas", "ataque" if 60 <= k < 76 else "parado",
          k // 5, slot=1)
    for i, (name, dx, dy) in enumerate((("aryel", 70, 206), ("borba", 232, 214), ("albeguinio", 300, 176))):
        actor(screen, ui, name, rect.x + dx, rect.y + dy, "direita", "parado", 0, slot=i + 2)
    if pressed:
        f = min(1.0, (k - 70) / 40)
        for i, (name, dx, dy) in enumerate((("esqueleto", 410, 96), ("diabrete", 470, 170), ("golem", 390, 214))):
            ring = pygame.Rect(0, 0, 56, 18)
            ring.center = (rect.x + dx, rect.y + dy)
            pygame.draw.ellipse(screen, (120, 60, 170), ring, 2)
            if f > 0.4:
                img = ui.assets.sprites[name].frame("esquerda", t // 8) if name in ui.assets.sprites else None
                if img is not None:
                    img = img.copy()
                    img.set_alpha(round(255 * min(1.0, (f - 0.4) / 0.6)))
                    screen.blit(img, img.get_rect(midbottom=ring.center))
        if k < 90:
            ui.text(screen, "LUTA!", theme.L, theme.BLOOD, (rect.centerx + 40, rect.y + 40))
    else:
        ui.text(screen, "QUANDO QUISEREM", theme.XS, theme.BONE, (btn.centerx, btn.y - 16))


def tv_mansao(screen, ui, rect, t):
    """CAPÍTULO 4: o Cauanzera Corrompido e a IARA na fila da Mansão, com a turma chegando."""
    _cover(screen, ui, "chapter4", rect)
    sprites = ui.assets.sprites
    if "iara_nucleo" in sprites:
        iara = sprites["iara_nucleo"].frame("frente", t // 8)
        screen.blit(iara, iara.get_rect(center=(rect.x + 420, rect.y + 96 + round(4 * math.sin(t * 0.08)))))
    actor(screen, ui, "cauanzera_corrompido", rect.x + 330, rect.y + 214, "esquerda", "parado", 0, k=2)
    for i, (name, dx) in enumerate((("aryel", 70), ("borba", 140), ("albeguinio", 205))):
        actor(screen, ui, name, rect.x + dx, rect.y + 200 - (i % 2) * 18, "direita", "parado", 0, slot=i + 1)
    heat = round(2 * math.sin(t * 0.1))
    ui.text(screen, "47°C", theme.S, theme.EMBER, (rect.x + 40 + 20, rect.y + 46 + heat))


FOOTAGE = {"vibra": tv_vibra, "porta": tv_porta, "fase": tv_fase, "batalha": tv_batalha, "mansao": tv_mansao}


def draw_footage(screen, ui, story, rect, t):
    """A imagem da notícia: a feita para o plantão, a cena antiga no tamanho da TV ou o estúdio."""
    if story is None:
        return tv_estudio(screen, ui, rect, t)
    if story.tv == "estudio":
        return tv_estudio(screen, ui, rect, t, f"EDIÇÃO {story.version}")
    draw = FOOTAGE.get(story.tv)
    if draw is not None:
        return draw(screen, ui, rect, t)
    old = NEWS_SCENES.get(story.scene)
    if old is not None:                                  # cena antiga: em cima da tarja, sem ficar escondida
        screen.fill(theme.INK, rect)
        return old(screen, ui, pygame.Rect(rect.x, rect.y, rect.w, rect.h - 62), t)
    tv_estudio(screen, ui, rect, t, f"VERSÃO {story.version}")


def draw_tv(screen, ui, rect, story, t, tag, count="", static=0):
    tv_frame(screen, ui, rect)
    clip = screen.get_clip()
    screen.set_clip(rect)
    draw_footage(screen, ui, story, rect, t)
    if static > 0:
        noise = _noise(rect.size, t // 2)
        noise.set_alpha(round(255 * min(1.0, static)))
        screen.blit(noise, rect.topleft)
    screen.blit(_scanlines(rect.size), rect.topleft)
    screen.set_clip(clip)
    live_tag(screen, ui, rect, t, tag)
    if count:
        ui.text(screen, count, theme.XS, theme.BONE, (rect.right - 12, rect.y + 20), anchor="midright")


def old_editions_text(after_version):
    """O letreiro: as edições mais velhas que a última mostrada, com as manchetes de cada uma."""
    last = parse_version(after_version) if after_version else None
    parts = []
    for version, entry in novidades.history():
        if last is not None and parse_version(version) >= last:
            continue
        titles = [t for _, t, s, _ in novidades.pages_of(version, entry) if s is not None]
        if titles:
            parts.append(f"{version}  " + "  ·  ".join(titles))
        if len(parts) >= 6:
            break
    return "     ".join(parts)


# ── a tela ──────────────────────────────────────────────────────────────
class NewsScene(_InfoScene):
    """O plantão. `news` = [(versão, entrada)], da mais nova para a mais velha.

    Sozinha (back=None) abre com a abertura dos âncoras e as manchetes; vindo do arquivo
    (back = função que monta a tela de volta) vai direto para a primeira notícia."""
    heading = "NOVIDADES"
    phase = "news"

    def __init__(self, game, news, back=None):
        super().__init__(game)
        self.news = list(news) if back is not None else list(news)[:MAX_AUTO]
        self.back = back
        self.opening = back is None and bool(self.news)
        self.stories = [s for version, entry in self.news for s in stories_of(self.ui, version, entry)]
        # pages: o que ENTER/setas percorrem (a abertura é a página 0 quando existe)
        self.pages = ([None] if self.opening else []) + self.stories
        self.page = 0
        self.age = 0
        self.seen = {0}
        self.reveal = 0 if self.opening else len(self.stories)
        self.ticker = old_editions_text(self.news[-1][0]) if self.news else ""
        self.summary = [line for _, entry in self.news[:1] for line in novidades.summary(entry)]

    # ── navegação ──
    def enter(self):
        from ..net.remote import hub
        hub.news = self.summary
        hub.news_taps()                                   # descarta toques velhos do celular
        super().enter()
        self._tell_phone()

    def _tell_phone(self):
        from ..net.remote import hub
        if not self.news:
            return
        story = self.current
        title = story.label if story else "AS MANCHETES"
        n = len(self.stories)
        hub.news_page = {"index": self.story_index + 1 if story else 0, "total": n, "title": title}
        hub.set_phase("news", banner=f"NOVIDADES DA {self.news[0][0]}")

    @property
    def current(self):
        return self.pages[self.page] if self.pages else None

    @property
    def story_index(self):
        return self.page - (1 if self.opening else 0)

    def leave(self):
        from ..net.remote import hub
        hub.news_page = None
        self.sfx("confirm", 0.4)
        if self.back is not None:
            self.game.change(self.back(self.game))
        else:
            from .menus import TitleScene
            self.game.change(TitleScene(self.game))

    def turn(self, step):
        page = max(0, min(len(self.pages) - 1, self.page + step))
        if page != self.page:
            self.page, self.age = page, 0
            self.seen.add(page)
            self.reveal = len(self.stories)                # saiu da abertura: a lista inteira aparece
            self.sfx("pagina", 0.5)
            self._tell_phone()

    def jump_edition(self, step):
        """LB/RB: primeira notícia da edição seguinte (ou anterior)."""
        story = self.current
        versions = [v for v, _ in self.news]
        if not versions:
            return
        at = versions.index(story.version) if story else -1
        target = max(0, min(len(versions) - 1, at + step))
        for i, s in enumerate(self.pages):
            if s is not None and s.version == versions[target]:
                self.turn(i - self.page)
                return

    def advance(self):
        if self.page >= len(self.pages) - 1:
            self.leave()
        else:
            self.turn(1)

    def update(self):
        super().update()
        self.age += 1
        if self.reveal < len(self.stories) and self.age % REVEAL_EVERY == 0 and self.age > 20:
            self.reveal += 1
            self.sfx("click", 0.25)
        from ..net.remote import hub
        for go in hub.news_taps():
            if go == "next":
                self.advance()
            elif go == "prev":
                self.turn(-1)
            elif go == "skip":
                self.leave()
                return

    def handle(self, event):
        if self.is_back(event) or not self.pages:
            if self.is_back(event) or event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.leave()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.turn(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.turn(1)
            elif event.key in (pygame.K_PAGEUP, pygame.K_q):
                self.jump_edition(-1)
            elif event.key in (pygame.K_PAGEDOWN, pygame.K_e):
                self.jump_edition(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.advance()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                self.turn(-1)
            elif event.button == 1:
                self.advance()

    # ── desenho ──
    def draw(self, screen):
        self.draw_background(screen)
        self.draw_body(screen)

    def draw_body(self, screen):
        ui, t = self.ui, self.ticks
        if not self.news:
            header(screen, ui, t, "SEM NOVIDADES", "")
            draw_tv(screen, ui, TV, None, t, "AO VIVO")
            lower_third(screen, ui, TV, "PLANTÃO", "NADA DE NOVO HOJE", RED)
            self.footer(screen, [("ENTER", "CONTINUAR")])
            return
        story = self.current
        n = len(self.stories)
        newest = self.news[0][0]
        if story is None:                                 # abertura
            versions = len(self.news)
            plural = "VERSÕES NOVAS" if versions > 1 else "VERSÃO NOVA"
            header(screen, ui, t, f"EDIÇÃO {newest}", f"{versions} {plural} · {n} NOTÍCIA{'S' if n > 1 else ''}")
            draw_tv(screen, ui, TV, None, t, "AO VIVO")
            lower_third(screen, ui, TV, "BOA NOITE", "AS MANCHETES DE HOJE", theme.BRASS, self.age / SLIDE_FRAMES)
            what = "uma versão nova" if versions == 1 else f"{versions} versões novas"
            body(screen, ui, BODY, [f"O jogo foi atualizado: {what}, com {n} novidade{'s' if n > 1 else ''}.",
                                    "ENTER mostra uma por uma. ESC pula direto para o jogo."], self.age)
        else:
            header(screen, ui, t, f"EDIÇÃO {story.version}", f"NOTÍCIA {self.story_index + 1} DE {n}")
            static = max(0.0, 1 - self.age / STATIC_FRAMES) * 0.9 if self.age < STATIC_FRAMES else 0
            draw_tv(screen, ui, TV, story, t, "AO VIVO" if self.back is None else "REPRISE",
                    f"{self.story_index + 1}/{n}", static)
            name, color = story.topic
            lower_third(screen, ui, TV, f"VERSÃO {story.version} · {name}", story.label, color,
                        (self.age - STATIC_FRAMES // 2) / SLIDE_FRAMES)
            body(screen, ui, BODY, story.lines, self.age - STATIC_FRAMES // 2)
        self.draw_rundown(screen)
        phone_card(screen, ui, story.label if story else "AS MANCHETES", self.story_index + 1 if story else 0, n, t)
        ticker(screen, ui, self.ticker, t // 2)
        last = self.page >= len(self.pages) - 1
        if story is None:
            hints = [("ENTER", "COMEÇAR"), ("ESC", "PULAR")]
        else:
            hints = [("←→", "NOTÍCIA")]
            if len(self.news) > 1:
                hints.append(("LB RB", "EDIÇÃO"))
            hints += [("ENTER", "SAIR" if last else "PRÓXIMA"), ("ESC", "SAIR")]
        ui.hints(screen, hints, (W // 2, H - 14))

    def _head_shown(self, version):
        return any(s.version == version for s in self.stories[:self.reveal])

    def draw_rundown(self, screen):
        """NESTA EDIÇÃO: versões como cabeçalho e as manchetes embaixo, rolando até a atual."""
        ui = self.ui
        top, bottom = SIDE.y, SIDE.bottom - 108
        ui.text(screen, "NESTA EDIÇÃO", theme.XS, theme.MUTED, (SIDE.x, top + 4), anchor="midleft", shadow=False)
        screen.fill(theme.LINE, (SIDE.x + 104, top + 4, SIDE.w - 104, 1))
        rows = []                                        # (altura, tipo, dados)
        last_version = None
        for i, s in enumerate(self.stories):
            if s.version != last_version:
                if last_version is not None:
                    rows.append((8, "gap", None))
                rows.append((20, "head", s.version))
                last_version = s.version
            rows.append((22, "item", i))
        current = self.story_index if self.current is not None else -1
        # rolagem: a notícia atual fica sempre à vista
        y0 = top + 24
        avail = bottom - y0
        offset = 0
        acc = 0
        for h, kind, data in rows:
            if kind == "item" and data == current:
                if acc + h > avail:
                    offset = acc + h - avail + 30
                break
            acc += h
        clip = screen.get_clip()
        screen.set_clip(pygame.Rect(SIDE.x, y0 - 2, SIDE.w, avail + 2))
        y = y0 - offset
        for h, kind, data in rows:
            if kind == "head" and not self._head_shown(data):
                y += h
                continue
            if kind == "head":
                ui.text(screen, data, theme.XS, theme.BRASS, (SIDE.x, y + 6), anchor="midleft", shadow=False)
                if self.back is None:
                    box = pygame.Rect(SIDE.x + 62, y, ui.assets.text_width("NOVA", theme.XS) + 10, 13)
                    screen.fill(theme.MOSS, box)
                    ui.text(screen, "NOVA", theme.XS, theme.INK, box.center, shadow=False)
            elif kind == "item":
                if data >= self.reveal:
                    y += h
                    continue
                s = self.stories[data]
                row = pygame.Rect(SIDE.x, y - 2, SIDE.w, 20)
                page = data + (1 if self.opening else 0)
                if data == current:
                    screen.fill(theme.INK_3, row)
                    screen.fill(theme.BRASS, (row.x, row.y, 3, row.h))
                    ui.arrow(screen, (row.x + 13, row.centery), "right", 4, theme.BRASS)
                    color = theme.BRASS
                elif page in self.seen:
                    color = theme.MUTED
                    pygame.draw.lines(screen, theme.MOSS, False, [(row.right - 18, row.centery),
                                                                  (row.right - 14, row.centery + 4),
                                                                  (row.right - 7, row.centery - 4)], 2)
                else:
                    color = theme.BONE
                ui.text(screen, s.label, theme.XS, color, (row.x + 24, row.centery), anchor="midleft", shadow=False)
            y += h
        screen.set_clip(clip)
        if offset:                                       # sinal de que tem mais em cima
            ui.arrow(screen, (SIDE.right - 8, y0 + 2), "up", 4, theme.FAINT)
        if y > bottom:
            ui.arrow(screen, (SIDE.right - 8, bottom - 2), "down", 4, theme.FAINT)


class ArchiveScene(_InfoScene):
    """OPÇÕES > NOVIDADES: todas as edições, da mais nova para a mais velha, com a reprise na TV."""
    heading = "NOVIDADES"
    phase = "news"
    ROW_H = 32
    LIST = pygame.Rect(32, 66, 360, 410)

    def __init__(self, game, index=0):
        super().__init__(game)
        self.news = novidades.history()
        self.index = max(0, min(len(self.news) - 1, index))
        self.age = 0

    def enter(self):
        from ..net.remote import hub
        hub.news = []
        hub.news_page = None
        super().enter()
        hub.set_phase("news", banner="ARQUIVO DAS NOVIDADES")

    def move(self, step):
        index = max(0, min(len(self.news) - 1, self.index + step))
        if index != self.index:
            self.index, self.age = index, 0
            self.sfx("click", 0.4)

    def watch(self):
        version, entry = self.news[self.index]
        index = self.index
        self.sfx("confirm", 0.4)
        self.game.change(NewsScene(self.game, [(version, entry)], back=lambda g: ArchiveScene(g, index)))

    def back(self):
        from .menus import OptionsScene
        self.sfx("cancel", 0.4)
        self.game.change(OptionsScene(self.game))

    def update(self):
        super().update()
        self.age += 1

    def handle(self, event):
        if self.is_back(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            self.back()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
            elif event.key in (pygame.K_PAGEUP, pygame.K_q):
                self.move(-5)
            elif event.key in (pygame.K_PAGEDOWN, pygame.K_e):
                self.move(5)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.watch()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in self._rows():
                if rect.collidepoint(event.pos):
                    if i == self.index:
                        self.watch()
                    else:
                        self.index, self.age = i, 0
                    return
        elif event.type == pygame.MOUSEWHEEL:
            self.move(-event.y)

    def _rows(self):
        lst = self.LIST
        visible = (lst.h - 22) // self.ROW_H
        first = max(0, min(len(self.news) - visible, self.index - visible // 2))
        for i in range(first, min(len(self.news), first + visible)):
            yield i, pygame.Rect(lst.x, lst.y + 22 + (i - first) * self.ROW_H, lst.w, self.ROW_H - 2)

    def draw(self, screen):
        self.draw_background(screen)
        self.draw_body(screen)

    def draw_body(self, screen):
        ui, t = self.ui, self.ticks
        header(screen, ui, t, "ARQUIVO", f"{len(self.news)} EDIÇÕES")
        lst = self.LIST
        ui.text(screen, "EDIÇÕES", theme.XS, theme.MUTED, (lst.x, lst.y + 4), anchor="midleft", shadow=False)
        screen.fill(theme.LINE, (lst.x + 64, lst.y + 4, lst.w - 64, 1))
        rows = list(self._rows())
        for i, row in rows:
            version, entry = self.news[i]
            stories = stories_of(ui, version, entry)
            chosen = i == self.index
            if chosen:
                screen.fill(theme.INK_3, row)
                screen.fill(theme.BRASS, (row.x, row.y, 3, row.h))
            head = _first_words(entry[0]) if _plain(entry) else stories[0].title
            while ui.assets.text_width(head, theme.XS) > lst.w - 120 and len(head) > 4:
                head = head[:-4].rstrip() + "..."
            ui.text(screen, version, theme.XS, theme.BRASS if chosen else theme.MUTED, (row.x + 14, row.centery),
                    anchor="midleft", shadow=False)
            ui.text(screen, head, theme.XS, theme.BONE if chosen else theme.MUTED, (row.x + 76, row.centery),
                    anchor="midleft", shadow=False)
            ui.text(screen, str(len(stories)), theme.XS, theme.FAINT, (row.right - 10, row.centery), anchor="midright",
                    shadow=False)
        # barra de rolagem
        track = pygame.Rect(lst.right + 8, lst.y + 22, 2, lst.h - 26)
        screen.fill(theme.LINE, track)
        if rows and len(self.news) > len(rows):
            first = rows[0][0]
            h = max(12, track.h * len(rows) // len(self.news))
            y = track.y + (track.h - h) * first // max(1, len(self.news) - len(rows))
            screen.fill(theme.BRASS, (track.x, y, 2, h))
        # a TV com a reprise da edição escolhida
        version, entry = self.news[self.index]
        stories = stories_of(ui, version, entry)
        tv = pygame.Rect(424, 82, 504, 284)
        first = stories[0]
        static = max(0.0, 1 - self.age / STATIC_FRAMES) * 0.9 if self.age < STATIC_FRAMES else 0
        draw_tv(screen, ui, tv, first, t, "REPRISE", "", static)
        name, color = first.topic
        lower_third(screen, ui, tv, f"VERSÃO {version} · {name}", first.label, color, (self.age - 4) / SLIDE_FRAMES)
        y = tv.bottom + 24
        titles = []
        for s in stories:
            if s.label not in titles:
                titles.append(s.label)
        if _plain(entry):
            titles = list(entry)
        for text in titles[:5]:
            screen.fill(theme.BRASS, (tv.x, y + 3, 6, 2))
            while ui.assets.text_width(text, theme.XS) > tv.w - 20 and len(text) > 4:
                text = text[:-4].rstrip() + "..."
            ui.text(screen, text, theme.XS, theme.BONE, (tv.x + 16, y + 4), anchor="midleft", shadow=False)
            y += 20
        ui.hints(screen, [("↑↓", "EDIÇÃO"), ("ENTER", "ASSISTIR"), ("ESC", "VOLTAR")], (W // 2, H - 14))


def _plain(entry):
    """Versão antiga: só uma lista de frases, sem páginas com título."""
    return all(isinstance(item, str) for item in entry)


def _first_words(line):
    return line.split(".")[0].split("!")[0].upper()
