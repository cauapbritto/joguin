"""O álbum da turma, no sótão da Casa.

Duas coisas moram aqui:

* As 4 fotos da turma (sempre no álbum e no varal do sótão), desenhadas na hora com os sprites
  do jogo: o Albeguinio com a Daiwone no pôr do sol, o João batendo o City de ré no poste da
  padaria, a foto da turma com o Aryel gigante colado na câmera e o Cauanzera enrolado nos cabos
  de rede do rack. Nenhuma tem legenda: é só a foto.
* As fotos que o jogo tira sozinho na campanha (o chefe caindo, alguém levantando o amigo): uma
  cópia pequena da tela vai para a pasta ``album`` do lado do progresso salvo, e a lista fica no
  progresso (chave KEY). Guarda as MAX_SHOTS mais novas.

``request(match, delay)`` marca a foto; a cena da partida chama ``maybe_snap`` depois de desenhar,
e a foto sai da tela já pronta (com os bonecos, os efeitos e o letreiro).
"""
import math
import random
import time

import pygame

from . import config, janelas, pecas, progress, theme

KEY = "album"                 # no progresso: lista com os nomes dos arquivos, do mais velho ao mais novo
MAX_SHOTS = 30
SHOT_SIZE = (320, 180)        # tamanho guardado (a tela inteira, reduzida)
IW, IH = 150, 100             # a imagem das fotos da turma
FIXED = ("albeguinio_daiwone", "joao_city", "aryel_gigante", "cauanzera_cabos")
PARADO, DANO, COMEMORA = "parado", "dano", "comemora"


# ─────────────────────────────────────────────
#  As fotos que o jogo tira
# ─────────────────────────────────────────────
def folder():
    return progress.path().parent / "album"


def shots():
    """Nomes dos arquivos das fotos da campanha que ainda existem, do mais velho ao mais novo."""
    names = progress.load().get(KEY, [])
    if not isinstance(names, list):
        return []
    base = folder()
    return [n for n in names if isinstance(n, str) and (base / n).is_file()]


def request(match, delay=30):
    """Marca uma foto para daqui a ``delay`` quadros (só a primeira marcada vale até sair)."""
    if getattr(match, "photo_at", None) is None:
        match.photo_at = match.frame + delay


def maybe_snap(match, screen):
    """Chamado depois que a partida desenhou: chegou a hora, a foto sai da tela."""
    at = getattr(match, "photo_at", None)
    if at is None or match.frame < at:
        return None
    match.photo_at = None
    return save_shot(screen)


def save_shot(screen):
    """Guarda uma cópia pequena da tela no álbum. Devolve o nome do arquivo (ou None se não deu)."""
    try:
        base = folder()
        base.mkdir(parents=True, exist_ok=True)
        name = time.strftime("foto_%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}.png"
        small = pygame.transform.smoothscale(screen.convert(), SHOT_SIZE) if screen.get_bitsize() >= 24 \
            else pygame.transform.scale(screen, SHOT_SIZE)
        pygame.image.save(small, str(base / name))
    except (OSError, pygame.error):
        return None
    data = progress.load()
    names = [n for n in data.get(KEY, []) if isinstance(n, str)] + [name]
    for old in names[:-MAX_SHOTS]:
        try:
            (folder() / old).unlink()
        except OSError:
            pass
    data[KEY] = names[-MAX_SHOTS:]
    progress.save(data)
    return name


_shot_cache = {}


def shot_image(name):
    if name not in _shot_cache:
        try:
            _shot_cache[name] = pygame.image.load(str(folder() / name))
        except (OSError, pygame.error):
            _shot_cache[name] = None
    return _shot_cache[name]


# ─────────────────────────────────────────────
#  As 4 fotos da turma
# ─────────────────────────────────────────────
def _sky(s, top, bottom):
    h = s.get_height()
    for y in range(h):
        f = y / h
        s.fill(tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3)), (0, y, s.get_width(), 1))


def _ground(s, y, c, c2):
    s.fill(c, (0, y, IW, IH - y))
    s.fill(c2, (0, y, IW, 2))


def _hero(sprites, key, kind=PARADO, direction="frente", index=0):
    sheet = sprites.get(key)
    if sheet is None:
        return None
    return sheet.pose(direction, kind, index)


def _stand(s, img, x, y, shadow=True):
    if img is None:
        return
    if shadow:
        w = int(img.get_width() * .7)
        sh = pygame.Surface((w, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        s.blit(sh, (x - w // 2, y - 5))
    s.blit(img, img.get_rect(midbottom=(x, y)))


def _albeguinio_daiwone(sprites, ui):
    """Os dois de pose no fim de tarde, com o coraçãozinho que alguém desenhou em cima."""
    s = pygame.Surface((IW, IH))
    _sky(s, (250, 170, 110), (250, 120, 140))
    pygame.draw.circle(s, (255, 230, 170), (118, 58), 16)
    _ground(s, 78, (90, 130, 80), (120, 160, 100))
    for x in range(0, IW, 9):
        s.fill((70, 110, 60), (x, 78, 2, 3))
    _stand(s, _hero(sprites, "albeguinio", COMEMORA), 58, 92)
    _stand(s, _hero(sprites, "daiwone"), 92, 92)
    x, y = 76, 18
    pygame.draw.circle(s, (240, 60, 90), (x - 3, y), 4)
    pygame.draw.circle(s, (240, 60, 90), (x + 3, y), 4)
    pygame.draw.polygon(s, (240, 60, 90), [(x - 7, y + 1), (x + 7, y + 1), (x, y + 9)])
    return s


def _joao_city(sprites, ui):
    """O João deu ré com o City direto no poste da padaria: poeira, estrelinha e a mão na cabeça."""
    s = pygame.Surface((IW, IH))
    _sky(s, (150, 196, 236), (200, 226, 246))
    s.fill((230, 210, 170), (0, 20, 70, 54))
    s.fill((200, 80, 60), (0, 20, 70, 8))
    if ui is not None:
        ui.text(s, "PADARIA", theme.XS, (250, 240, 220), (44, 24), shadow=False)
    s.fill((120, 170, 200), (8, 36, 24, 18))
    s.fill((80, 60, 40), (42, 36, 18, 38))
    _ground(s, 74, (110, 110, 118), (150, 150, 158))
    s.fill((236, 236, 236), (0, 86, IW, 2))
    pygame.draw.line(s, (90, 90, 100), (8, 80), (20, 16), 4)                  # o poste, entortado
    car = pecas.image("carro_city")
    if car is not None:
        car = pygame.transform.rotate(pygame.transform.scale(car, (112, 44)), -3)
        s.blit(car, (4, 42))
    for k in range(7):                                                       # estrelinha da batida
        a = k * math.pi * 2 / 7
        pygame.draw.line(s, (255, 230, 80), (14, 58), (14 + int(math.cos(a) * 11), 58 + int(math.sin(a) * 11)), 2)
    pygame.draw.circle(s, (255, 250, 200), (14, 58), 4)
    rng = random.Random(4)
    for _ in range(14):                                                      # poeira
        pygame.draw.circle(s, (200, 196, 186), (rng.randrange(100, 148), rng.randrange(72, 92)), rng.randrange(2, 5))
    _stand(s, _hero(sprites, "borba", DANO, "esquerda"), 134, 96)
    return s


def _aryel_gigante(sprites, ui):
    """Foto da turma no quintal: os três lá atrás e o Aryel colado na câmera, gigante."""
    s = pygame.Surface((IW, IH))
    _sky(s, (130, 190, 240), (190, 226, 250))
    s.fill((250, 240, 230), (0, 30, IW, 40))
    s.fill((180, 80, 60), (0, 24, IW, 8))
    s.fill((120, 160, 200), (20, 40, 20, 16))
    s.fill((120, 160, 200), (110, 40, 20, 16))
    _ground(s, 70, (100, 150, 80), (130, 180, 100))
    for i, key in enumerate(("cauanzera", "albeguinio", "borba")):
        img = _hero(sprites, key, COMEMORA if i == 1 else PARADO)
        if img is not None:
            _stand(s, pygame.transform.scale(img, (34, 49)), 18 + i * 26, 80)
    big = _hero(sprites, "aryel", COMEMORA)
    if big is not None:
        big = pygame.transform.scale(big, (big.get_width() * 2, big.get_height() * 2))
        s.blit(big, big.get_rect(midtop=(112, 6)))
    return s


def _cauanzera_cabos(sprites, ui):
    """O cara da TI todo enrolado nos cabos de rede, tentando organizar o rack."""
    rng = random.Random(11)
    s = pygame.Surface((IW, IH))
    s.fill((70, 76, 90))
    s.fill((56, 60, 72), (0, 76, IW, 24))
    for x in range(0, IW, 30):
        s.fill((64, 68, 80), (x, 0, 1, 76))
    rx = 98                                                                  # o rack, com os switches piscando
    s.fill((26, 26, 32), (rx, 6, 46, 72))
    s.fill((44, 44, 52), (rx, 6, 46, 3))
    for k in range(6):
        y = 12 + k * 10
        s.fill((50, 52, 62), (rx + 4, y, 38, 7))
        for p in range(6):
            s.fill((20, 20, 24), (rx + 6 + p * 6, y + 2, 4, 3))
            if rng.random() < .6:
                s.fill(rng.choice(((80, 255, 120), (255, 190, 60))), (rx + 7 + p * 6, y + 1, 2, 1))
    s.fill((30, 30, 36), (rx, 78, 46, 4))
    _stand(s, _hero(sprites, "cauanzera", DANO), 56, 94)
    cores = ((60, 140, 230), (240, 200, 60), (220, 60, 60), (80, 190, 90))
    for i, (c, wy) in enumerate(zip(cores, (58, 66, 76, 86))):
        a = (rx + 8 + i * 9, 16 + i * 14)
        b = (70, wy - 4)
        pts = [a, ((a[0] + b[0]) // 2, max(a[1], b[1]) + 10), b]
        dark = tuple(max(0, v - 40) for v in c)
        pygame.draw.lines(s, dark, False, [(x, y + 1) for x, y in pts], 2)
        pygame.draw.lines(s, c, False, pts, 2)
        pygame.draw.ellipse(s, dark, (38, wy - 4, 36, 9), 2)                 # a volta em volta do corpo
        pygame.draw.arc(s, c, (38, wy - 4, 36, 9), math.pi, 2 * math.pi, 2)
    pygame.draw.arc(s, (240, 240, 240), (40, 50, 32, 8), math.pi, 2 * math.pi, 2)
    pygame.draw.line(s, (60, 140, 230), (78, 64), (86, 56), 2)
    s.fill((200, 230, 255), (85, 54, 3, 3))
    for _ in range(14):                                                      # o bolo de cabo no chão
        pygame.draw.arc(s, rng.choice(cores), (rng.randrange(20, 96), rng.randrange(85, 95), rng.randrange(8, 16), 6),
                        0, math.pi * 2, 2)
    s.fill((240, 200, 60), (8, 88, 12, 7))                                   # a etiquetadora caída
    s.fill((30, 30, 34), (10, 90, 6, 3))
    return s


_DRAW = {"albeguinio_daiwone": _albeguinio_daiwone, "joao_city": _joao_city,
         "aryel_gigante": _aryel_gigante, "cauanzera_cabos": _cauanzera_cabos}
_fixed_cache = {}


def fixed_photo(key, assets, ui=None):
    """A imagem (sem moldura) de uma das 4 fotos da turma."""
    cache_key = (key, id(assets))
    if cache_key not in _fixed_cache:
        _fixed_cache[cache_key] = _DRAW[key](assets.sprites, ui)
    return _fixed_cache[cache_key]


def framed(img, tilt=0):
    """Papel de foto instantânea: borda branca e a faixa de baixo mais larga, sem nada escrito."""
    w, h = img.get_size()
    p = pygame.Surface((w + 12, h + 26), pygame.SRCALPHA)
    p.fill((240, 236, 226))
    pygame.draw.rect(p, (196, 190, 178), p.get_rect(), 1)
    p.blit(img, (6, 6))
    pygame.draw.rect(p, (60, 56, 60), (6, 6, w, h), 1)
    return pygame.transform.rotate(p, tilt) if tilt else p


def pages(assets, ui=None):
    """Tudo o que o álbum mostra, na ordem: as 4 fotos da turma e depois as da campanha (mais velha
    primeiro). Cada página é ("turma", chave) ou ("campanha", arquivo)."""
    return [("turma", k) for k in FIXED] + [("campanha", n) for n in shots()]


def page_image(page, assets, ui=None):
    kind, key = page
    if kind == "turma":
        return fixed_photo(key, assets, ui)
    img = shot_image(key)
    if img is None:
        return None
    return pygame.transform.smoothscale(img, (IW + 64, round((IW + 64) * SHOT_SIZE[1] / SHOT_SIZE[0])))


# ─────────────────────────────────────────────
#  A janela do álbum
# ─────────────────────────────────────────────
class AlbumMenu:
    """O álbum aberto em cima da mesa: uma foto por vez, sem legenda. Analógico para os lados (ou
    ATACAR) passa a página, ESQUIVA fecha."""

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.pages = pages(match.assets, match.game.ui)
        self.index = len(self.pages) - 1 if len(self.pages) > len(FIXED) else 0   # abre na foto mais nova
        self.age = 0
        self._last = 0

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                         # o ATACAR que abriu não vira a página
        if any(inp.pressed(a) for a in ("dodge", "special", "cancel")):
            self.match.assets.play("click", 0.3)
            return False
        x, _ = inp.axis()
        sx = 1 if x > 0.5 else -1 if x < -0.5 else 0
        if inp.pressed("attack") or inp.pressed("confirm"):
            sx = sx or 1
        elif sx == self._last:
            sx = 0
        else:
            self._last = sx
        if not (inp.pressed("attack") or inp.pressed("confirm")):
            self._last = 1 if x > 0.5 else -1 if x < -0.5 else 0
        if sx:
            self.turn(sx)
        return True

    def turn(self, step):
        self.index = (self.index + step) % len(self.pages)
        self.match.assets.play("click", 0.25)

    def pick(self, item):
        return False

    def snapshot(self):
        return None

    def size(self, ui):
        return IW + 104, IH + 100

    def draw(self, screen, ui, cam, rect=None):
        if rect is None:
            rect = janelas.default_rect(self.size(ui), cam, self.fighter)
        body = janelas.panel(screen, ui, rect, self.fighter, "ÁLBUM", f"{self.index + 1} / {len(self.pages)}",
                             accent=theme.BRASS)
        img = page_image(self.pages[self.index], self.match.assets, ui)
        if img is not None:
            photo = framed(img)
            screen.blit(photo, photo.get_rect(midtop=(rect.centerx, body.y + 2)))
        janelas.footer(screen, ui, rect, "◀ ▶ PASSAR · ESQUIVA: FECHAR")


# ─────────────────────────────────────────────
#  O desenho da caixa NÃO MEXER (segredo do sótão)
# ─────────────────────────────────────────────
def kid_drawing(assets=None):
    """Desenho de criança da turma: os 4 de palitinho, sol no canto e a casa torta."""
    s = pygame.Surface((150, 100))
    s.fill((246, 242, 230))
    for y in range(8, 100, 10):                                              # pauta do caderno
        s.fill((200, 216, 236), (0, y, 150, 1))
    s.fill((230, 160, 160), (14, 0, 1, 100))
    pygame.draw.circle(s, (250, 200, 60), (130, 16), 10, 2)
    for k in range(8):
        a = k * math.pi / 4
        pygame.draw.line(s, (250, 200, 60), (130 + int(math.cos(a) * 13), 16 + int(math.sin(a) * 13)),
                         (130 + int(math.cos(a) * 18), 16 + int(math.sin(a) * 18)), 2)
    pygame.draw.lines(s, (200, 80, 60), False, [(22, 50), (40, 30), (60, 52)], 2)   # a casa torta
    pygame.draw.rect(s, (120, 90, 60), (26, 50, 32, 26), 2)
    pygame.draw.rect(s, (120, 90, 60), (37, 60, 10, 16), 2)
    colors = ((84, 162, 222), (234, 132, 64), (236, 118, 84), (150, 130, 90))
    for i, c in enumerate(colors):
        x, h = 76 + i * 18, (30, 18, 26, 26)[i]                              # o Aryel bem pequenininho
        base = 88
        pygame.draw.circle(s, c, (x, base - h - 6), 5, 2)
        pygame.draw.line(s, c, (x, base - h - 1), (x, base - 8), 2)
        pygame.draw.line(s, c, (x - 6, base - h + 6), (x + 6, base - h + 4), 2)
        pygame.draw.line(s, c, (x, base - 8), (x - 4, base), 2)
        pygame.draw.line(s, c, (x, base - 8), (x + 4, base), 2)
    pygame.draw.line(s, (120, 200, 90), (0, 90), (150, 90), 2)
    return s


class DrawingMenu(AlbumMenu):
    """O que tinha dentro da caixa NÃO MEXER: o desenho de criança da turma. ESQUIVA ou ATACAR fecha."""

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.age = 0
        self.image = kid_drawing()

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True
        if any(inp.pressed(a) for a in ("dodge", "special", "cancel", "attack", "confirm")):
            self.match.assets.play("click", 0.3)
            return False
        return True

    def draw(self, screen, ui, cam, rect=None):
        if rect is None:
            rect = janelas.default_rect(self.size(ui), cam, self.fighter)
        body = janelas.panel(screen, ui, rect, self.fighter, "NÃO MEXER", "", accent=(210, 50, 50))
        photo = framed(self.image, 3)
        screen.blit(photo, photo.get_rect(midtop=(rect.centerx, body.y + 2)))
        janelas.footer(screen, ui, rect, "ESQUIVA: GUARDAR DE VOLTA")
