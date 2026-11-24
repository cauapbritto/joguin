"""O sótão da Casa (abre ao zerar o capítulo 1): o álbum da turma.

Da Casa, ATACAR na porta do sótão aberta leva o grupo inteiro para cima (a escada, em
``scenes/escada.py``). A parede inclinada do telhado é o fundo: o varal com as 4 fotos da turma,
o mural de cortiça com as fotos mais novas que o jogo tirou na campanha, a janela redonda, o quadro
torto e a prateleira de brinquedos. No chão, a mesinha com o álbum (ATACAR abre o ``AlbumMenu``),
caixas de mudança, a cadeira de balanço, o espelho coberto, o cabideiro, a mala e o ventilador.
O alçapão do canto volta para a Casa.

Segredo (``nao_mexer``): a caixa da faixa vermelha só abre quando todo mundo aperta ATACAR nela
quase junto. Dentro, um desenho de criança da turma.
"""
import math

import pygame

from . import album, casa_art as art, config, janelas, pecas, segredos, theme
from .arena import MAPS_BY_KEY
from .campaign import CoopMatch, _spread
from .casa import Decor
from .matches import Result

SOTAO_MAP = "sotao_casa"
T = 40
TOP = 3 * T                                         # as linhas de folga do mapa em texto (lobbies.HEADROOM)
BACK = pygame.Rect(T, TOP + T, 24 * T, 4 * T)       # a parede inclinada do telhado (o fundo)
HATCH = pygame.Rect(56, TOP + 7 * T, 96, 72)   # o alçapão de volta à Casa
TABLE = (520, TOP + 7 * T + 10)                          # a mesinha do álbum (pé no chão, meio)
SECRET_BOX = (900, TOP + 11 * T + 10)               # a caixa NÃO MEXER
TOGETHER = 90                                       # quadros para todo mundo apertar na caixa
WOBBLE = 34
REACH = 60
CORK = pygame.Rect(616, TOP + T + 14, 216, 118)     # o mural das fotos da campanha
CORK_SHOTS = 6

# (peça, x, y do pé, largura do pé que ninguém atravessa)
FURNITURE = (
    ("sotao_espelho", 92, TOP + 12 * T - 4, 44),
    ("sotao_cabideiro", 156, TOP + 12 * T - 10, 22),
    ("sotao_mala", 250, TOP + 12 * T - 6, 48),
    ("sotao_ventilador", 372, TOP + 6 * T + 10, 24),
    ("sotao_cadeira_balanco", 612, TOP + 7 * T + 16, 44),
    ("sotao_caixa_4", 852, TOP + 6 * T + 26, 56),
    ("sotao_caixa_3", 918, TOP + 6 * T + 10, 44),
    ("sotao_caixa_1", 950, TOP + 6 * T + 40, 52),
    ("sotao_caixa_2", 788, TOP + 6 * T + 40, 40),
)


def _piece(name, shadow=True):
    """Peça HD de assets/pecas com a sombra no chão; (x, y) da Decor é o pé, no meio."""
    img = pecas.image(name)
    if img is None:
        img = pygame.Surface((24, 24), pygame.SRCALPHA)
        img.fill((120, 90, 60))
    w, h = img.get_size()
    s = pygame.Surface((w + 8, h + 6), pygame.SRCALPHA)
    if shadow:
        pygame.draw.ellipse(s, (0, 0, 0, 80), (2, h - 6, w + 4, 12))
    s.blit(img, (4, 0))
    return art.Baked(s, -(w + 8) // 2, -h)


def _pin(s, x, y, color=(220, 60, 60)):
    pygame.draw.circle(s, (40, 20, 20), (x, y + 1), 3)
    pygame.draw.circle(s, color, (x, y), 3)
    s.set_at((x - 1, y - 1), (255, 220, 220))


def _half(img):
    return pygame.transform.smoothscale(img, (img.get_width() // 2, img.get_height() // 2))


def draw_backdrop(s, assets, ui=None):
    """A parede inclinada do telhado com tudo o que fica pendurado nela."""
    r = BACK
    s.fill((70, 48, 32), r)
    for x in range(r.x, r.right, 24):                                         # tábuas do forro
        s.fill((80, 56, 36), (x + 1, r.y, 23, r.h))
        s.fill((56, 38, 24), (x, r.y, 1, r.h))
    for x0 in range(r.x + 60, r.right, 240):                                  # caibros na diagonal
        pygame.draw.line(s, (48, 32, 20), (x0, r.y), (x0 + 60, r.bottom), 10)
        pygame.draw.line(s, (96, 66, 42), (x0 - 4, r.y), (x0 + 56, r.bottom), 2)
    s.fill((44, 30, 18), (r.x, r.y, r.w, 10))                                 # a viga de cima
    s.fill((100, 70, 44), (r.x, r.y + 10, r.w, 2))
    s.fill((40, 28, 18), (r.x, r.bottom - 8, r.w, 8))                         # rodapé
    # a janela redonda, com a lua e o brilho entrando
    wx, wy = 566, r.y + 74
    glow = pygame.Surface((160, 160), pygame.SRCALPHA)
    for k in range(8):
        pygame.draw.circle(glow, (255, 230, 170, 8), (80, 80), 78 - k * 8)
    s.blit(glow, (wx - 80, wy - 80))
    pygame.draw.circle(s, (60, 40, 26), (wx, wy), 34)
    pygame.draw.circle(s, (40, 52, 96), (wx, wy), 27)
    pygame.draw.circle(s, (250, 240, 200), (wx + 9, wy - 8), 8)
    pygame.draw.circle(s, (40, 52, 96), (wx + 13, wy - 11), 6)
    for k in range(5):
        s.set_at((wx - 16 + k * 7, wy + (k * 5) % 13 - 4), (230, 230, 250))
    s.fill((60, 40, 26), (wx - 27, wy - 2, 54, 4))
    s.fill((60, 40, 26), (wx - 2, wy - 27, 4, 54))
    # a lâmpada pendurada no fio
    lamp = pecas.image("sotao_lampada")
    if lamp is not None:
        lx = 494
        s.fill((30, 30, 30), (lx - 1, r.y + 10, 2, 16))
        s.blit(lamp, lamp.get_rect(midtop=(lx, r.y + 24)))
        halo = pygame.Surface((90, 90), pygame.SRCALPHA)
        for k in range(6):
            pygame.draw.circle(halo, (255, 230, 160, 10), (45, 45), 44 - k * 7)
        s.blit(halo, (lx - 45, r.y + 6))
    # o varal com as 4 fotos da turma (prendedor de madeira em cada uma)
    x0, x1, y0 = r.x + 24, 404, r.y + 26
    points = [(x0 + (x1 - x0) * i // 20, y0 + round(math.sin(math.pi * i / 20) * 10)) for i in range(21)]
    pygame.draw.lines(s, (200, 196, 186), False, points, 2)
    for i, key in enumerate(album.FIXED):
        photo = _half(album.framed(album.fixed_photo(key, assets, ui), (-4, 3, -2, 5)[i]))
        cx = x0 + 44 + i * 88
        ty = y0 + round(math.sin(math.pi * (cx - x0) / (x1 - x0)) * 10)
        s.blit(photo, photo.get_rect(midtop=(cx, ty)))
        s.fill((170, 120, 70), (cx - 2, ty - 4, 5, 10))
    # o quadro torto
    quadro = pecas.image("sotao_quadro")
    if quadro is not None:
        s.blit(quadro, quadro.get_rect(center=(438, r.y + 112)))
    # o mural de cortiça com as fotos mais novas da campanha
    c = CORK
    s.fill((60, 40, 24), c.inflate(8, 8))
    s.fill((176, 130, 84), c)
    for k in range(c.w * c.h // 30):
        px, py = c.x + (k * 37) % c.w, c.y + (k * 53) % c.h
        s.set_at((px, py), (150, 104, 64) if k % 2 else (196, 150, 100))
    shots = album.shots()[-CORK_SHOTS:]
    if shots:
        for i, name in enumerate(reversed(shots)):
            img = album.shot_image(name)
            if img is None:
                continue
            small = pygame.transform.smoothscale(img, (60, 34))
            card = pygame.Surface((66, 44), pygame.SRCALPHA)
            card.fill((240, 236, 226))
            card.blit(small, (3, 3))
            card = pygame.transform.rotate(card, (-3, 2, -1, 4, -2, 1)[i])
            cx, cy = c.x + 38 + (i % 3) * 70, c.y + 32 + (i // 3) * 56
            s.blit(card, card.get_rect(center=(cx, cy)))
            _pin(s, cx, cy - 20, ((220, 60, 60), (60, 140, 220), (240, 200, 60))[i % 3])
    else:
        note = pygame.Rect(0, 0, 120, 40)
        note.center = c.center
        s.fill((250, 240, 150), note)
        _pin(s, note.centerx, note.y + 4)
        if ui is not None:
            ui.text(s, "FOTOS DA", theme.XS, (90, 70, 50), (note.centerx, note.y + 16), shadow=False)
            ui.text(s, "CAMPANHA", theme.XS, (90, 70, 50), (note.centerx, note.y + 30), shadow=False)
    # a prateleira de brinquedos
    toys = pecas.image("sotao_brinquedos")
    if toys is not None:
        s.blit(toys, toys.get_rect(midtop=(916, r.y + 40)))


def draw_hatch(s, rect):
    """O alçapão aberto no chão: o buraco escuro, a tampa levantada e a escada descendo."""
    s.fill((30, 20, 12), rect.inflate(8, 8))
    s.fill((10, 8, 8), rect)
    for k in range(4):                                                        # degraus da escada
        y = rect.y + 10 + k * 15
        s.fill((120, 82, 50), (rect.x + 18, y, rect.w - 36, 5))
        s.fill((150, 110, 70), (rect.x + 18, y, rect.w - 36, 1))
    s.fill((96, 64, 40), (rect.x + 14, rect.y, 6, rect.h))
    s.fill((96, 64, 40), (rect.right - 20, rect.y, 6, rect.h))
    lid = pygame.Rect(rect.x, rect.y - 26, rect.w, 24)                        # a tampa encostada
    s.fill((110, 74, 46), lid)
    for x in range(lid.x, lid.right, 16):
        s.fill((86, 56, 34), (x, lid.y, 1, lid.h))
    s.fill((200, 170, 70), (lid.centerx - 6, lid.bottom - 8, 12, 4))


class SotaoMatch(janelas.Janelas, CoopMatch):
    """O sótão. ``story`` e ``walk`` só passam adiante para a Casa na volta."""

    lobby = True
    music = "casa"
    walk = False
    hud_title = "SÓTÃO"

    def __init__(self, game, run, story=False, walk=False):
        self.story = story
        self.walk = walk
        cfg = MAPS_BY_KEY[SOTAO_MAP]
        starts = _spread(cfg.markers["S"], len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (0.0, -1.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()
        self.going_down = False
        self.photo_at = None
        self.box_presses = {}                       # jogador -> quadro do último ATACAR na caixa
        self.box_open = segredos.is_found("nao_mexer")
        self._furnish()

    # ── montagem ─────────────────────────────
    def _put(self, baked, x, y, foot_w=0, flat=False):
        from .entities import Wall
        d = Decor(x, y, baked, flat=flat)
        self.props.append(d)
        if foot_w:
            self.arena.walls.append(Wall(x - foot_w // 2, y - 12, foot_w, 14, visible=False))
        return d

    def _furnish(self):
        from .entities import Wall
        floor = self.arena.floor
        draw_backdrop(floor, self.assets, self.game.ui)
        draw_hatch(floor, HATCH)
        self.arena.walls.append(Wall(BACK.x, BACK.y, BACK.w, BACK.h - 16, visible=False))
        for name, x, y, w in FURNITURE:
            self._put(_piece(name), x, y, w)
        self.table = self._put(_piece("sotao_mesa_album"), *TABLE, 84)
        self.box = self._put(self._box_piece(), *SECRET_BOX, 58)

    def _box_piece(self):
        """A caixa da faixa vermelha, com o NÃO MEXER escrito à mão na faixa."""
        baked = _piece("sotao_caixa_nao_mexer_aberta" if self.box_open else "sotao_caixa_nao_mexer")
        img = baked.image.copy()
        word = pygame.Surface((90, 20), pygame.SRCALPHA)
        self.game.ui.text(word, "NÃO MEXER", theme.XS, (250, 240, 230), (45, 10), shadow=False)
        r = word.get_bounding_rect()
        if r.w and r.h:                                  # cabe na faixa vermelha da caixa
            k = min(1.0, 50 / r.w, 9 / r.h)
            word = pygame.transform.smoothscale(word.subsurface(r), (max(1, round(r.w * k)), max(1, round(r.h * k))))
            img.blit(word, word.get_rect(center=(img.get_width() // 2, 25)))
        return art.Baked(img, baked.dx, baked.dy)

    # ── consultas ────────────────────────────
    @property
    def objective_text(self):
        return "SÓTÃO · O ÁLBUM ESTÁ NA MESINHA"

    def objective(self):
        return None

    def hatch_near(self, f):
        return f.alive_in_match and HATCH.inflate(30, 30).collidepoint(f.x, f.y)

    def table_near(self, f):
        x, y = TABLE
        return f.alive_in_match and math.hypot(f.x - x, f.y - y) < REACH + 20

    def box_near(self, f):
        x, y = SECRET_BOX
        return f.alive_in_match and math.hypot(f.x - x, f.y - y) < REACH

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            self._set_banner("SÓTÃO", "O ÁLBUM DA TURMA", theme.BRASS)
        if self.banner and self.banner[3] > 130:
            self.banner = None
        self.update_windows()

    def interact(self, f):
        if self.hatch_near(f):
            if self.leaving_in:
                return True
            self.going_down = True
            self.assets.play("select", 0.45)
            self.leave_soon(self.leave)
            return True
        if self.table_near(f):
            self.menus[f] = album.AlbumMenu(self, f)
            self.assets.play("click", 0.45)
            return True
        if self.box_near(f):
            self.poke_box(f)
            return True
        return self.pick_ground(f)

    def poke_box(self, f):
        """ATACAR na caixa NÃO MEXER. Sozinho ela só balança; com todo mundo junto, ela abre."""
        if self.box_open:
            self.menus[f] = album.DrawingMenu(self, f)
            self.assets.play("click", 0.45)
            return
        self.box_presses[f] = self.frame
        everyone = [p for p in self.alive_players]
        if everyone and all(self.frame - self.box_presses.get(p, -10 ** 6) <= TOGETHER for p in everyone):
            self.open_box(f)
            return
        self.box.wobble = WOBBLE
        self.assets.play("cancel", 0.3)

    def open_box(self, f):
        self.box_open = True
        self.box.baked = self._box_piece()
        x, y = SECRET_BOX
        self.burst(x, y - 30, (230, 220, 200), 22, speed=3)
        self.assets.play("confirm", 0.5)
        segredos.find("nao_mexer", self, x, y - 90)
        self.menus[f] = album.DrawingMenu(self, f)

    def _finish(self, won):
        self.won = won
        self.result = Result("SÓTÃO", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.campaign import hub_scene
        from .scenes.escada import StairsTripScene
        return StairsTripScene(self.game, lambda: hub_scene(self.game, self.run, story=self.story, walk=self.walk,
                                                            arrive="sotao"), "DESCENDO PARA A CASA", up=False)

    def restart_scene(self):
        from .scenes.campaign import sotao_scene
        return sotao_scene(self.game, self.run, story=self.story, walk=self.walk)

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        free = [p for p in self.alive_players if p not in self.menus]
        blink = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
        if any(self.hatch_near(p) for p in free):
            sx, sy = cam.to_screen(HATCH.centerx, HATCH.y - 40)
            ui.text(screen, "ATACAR: DESCER PARA A CASA", theme.XS, blink, (round(sx), round(sy)))
        else:
            sx, sy = cam.to_screen(HATCH.centerx, HATCH.bottom + 12)
            ui.text(screen, "ALÇAPÃO · CASA", theme.XS, theme.MUTED, (round(sx), round(sy)))
        if any(self.table_near(p) for p in free):
            sx, sy = cam.to_screen(TABLE[0], TABLE[1] - 100)
            ui.text(screen, "ATACAR: VER O ÁLBUM", theme.XS, blink, (round(sx), round(sy)))
        if self.box_open and any(self.box_near(p) for p in free):
            sx, sy = cam.to_screen(SECRET_BOX[0], SECRET_BOX[1] - 70)
            ui.text(screen, "ATACAR: OLHAR O DESENHO", theme.XS, blink, (round(sx), round(sy)))
        self.draw_ground(screen, cam, ui)
        janelas.draw(self, screen, ui)


__all__ = ("SotaoMatch", "SOTAO_MAP")
