"""Modo LUTA: 1 x 1 de lado no Coliseu, com lutadores altos (esqueleto + peças, luta_rig.py).

As regras ficam em soulstrike/luta.py; aqui ficam o cenário, o desenho dos lutadores, das armas,
dos projéteis e dos efeitos, o HUD (vida, relógio, rounds e barra de SUPER) e a entrada.
"""
import math
import random
from types import SimpleNamespace

import pygame

from .. import config, luta as L, luta_rig as R, theme
from ..data import CHARACTERS
from ..matches import Result
from ..net.remote import hub
from .base import Scene

W, H = config.SCREEN_W, config.SCREEN_H
FLOOR = L.FLOOR
HOR = 372                       # onde o muro encontra o chão
ENERGY = (90, 170, 255)
GOLD = (236, 188, 62)

_BACKDROP = {}


# ── cenário: o Coliseu de lado ────────────────────────────────────────
def mix_light(c):
    """Cor do rastro: a cor do jogador, clara."""
    return tuple(min(255, int(v * 0.6 + 110)) for v in c[:3])


def coliseu_backdrop(assets=None):
    """Arquibancada com a torcida, muro de blocos com colunas, tochas e o chão de areia em
    perspectiva (feito uma vez; as tochas e as brasas mexem por cima)."""
    if "coliseu" in _BACKDROP:
        return _BACKDROP["coliseu"]
    rng = random.Random(7)
    s = pygame.Surface((W, H))
    for y in range(H):
        k1, k2 = max(0, 1 - y / 170), max(0, 1 - y / 210)
        s.fill((int(40 + 60 * k1), int(22 + 30 * k1), int(46 + 20 * k2)), (0, y, W, 1))
    for row in range(8):                        # torcida em silhueta
        y = 64 + row * 16
        pygame.draw.rect(s, (38 - row, 28, 40), (0, y + 8, W, 10))
        for x in range(-4, W, 9):
            cx = x + (row % 2) * 4 + rng.randint(-1, 1)
            tone = rng.choice(((70, 46, 52), (58, 40, 60), (88, 60, 52), (50, 36, 48), (120, 80, 60)))
            tone = tuple(int(c * (0.55 + row * 0.07)) for c in tone)
            pygame.draw.circle(s, tone, (cx, y + 4 + rng.randint(-1, 1)), 3)
            pygame.draw.rect(s, tone, (cx - 3, y + 6, 7, 8))
            if rng.random() < 0.06:
                pygame.draw.line(s, tone, (cx + 3, y + 4), (cx + 5, y - 3), 2)
    blk = _tile("blococoliseu.png")
    col = _tile("colunacoliseu.png")
    top = 196
    if blk is not None:
        for y in range(top, HOR, blk.get_height()):
            for x in range(0, W, blk.get_width()):
                s.blit(blk, (x, y))
    else:
        s.fill((96, 80, 70), (0, top, W, HOR - top))
    pygame.draw.rect(s, (30, 22, 20), (0, top - 6, W, 8))
    pygame.draw.rect(s, (120, 100, 80), (0, top - 8, W, 3))
    dark = pygame.Surface((W, HOR - top + 6), pygame.SRCALPHA)
    dark.fill((10, 6, 16, 120))
    s.blit(dark, (0, top - 6))
    if col is not None:
        c2 = pygame.transform.scale(col, (round(col.get_width() * 1.6), round(col.get_height() * 1.6)))
        for x in range(30, W, 180):
            s.blit(c2, (x, HOR - c2.get_height() + 6))
    for x in range(120, W, 180):                 # suportes das tochas
        pygame.draw.rect(s, (60, 44, 32), (x - 5, 266, 10, 18))
        pygame.draw.rect(s, (90, 70, 50), (x - 7, 264, 14, 4))
    floor = _tile("fundocoliseu.png")
    if floor is not None:
        floor = floor.subsurface((300, 300, 1200, 500)).copy()
        for i in range(H - HOR):
            t = i / (H - HOR)
            src = int(t ** 0.8 * 499)
            row = floor.subsurface((0, src, 1200, 1))
            w = int(W * (1.1 + 0.9 * t))
            s.blit(pygame.transform.scale(row, (w, 1)), ((W - w) // 2, HOR + i))
    else:
        s.fill((150, 120, 80), (0, HOR, W, H - HOR))
    g = pygame.Surface((W, H - HOR), pygame.SRCALPHA)
    for i in range(H - HOR):
        g.fill((0, 0, 0, max(0, 150 - i * 2)), (0, i, W, 1))
    s.blit(g, (0, HOR))
    pool = pygame.Surface((W, H))
    for r, a in ((300, 10), (200, 14), (120, 14)):
        pygame.draw.ellipse(pool, (a * 2, a + a // 2, a), (W // 2 - r, FLOOR - r // 5, r * 2, r * 2 // 5))
    s.blit(pool, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    vignette = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(50):
        pygame.draw.rect(vignette, (0, 0, 0, 3), (i, i, W - 2 * i, H - 2 * i), 1)
    s.blit(vignette, (0, 0))
    _BACKDROP["coliseu"] = s
    return s


def _tile(name):
    try:
        img = pygame.image.load(str(config.TILES_DIR / "coliseu" / name))
        return img.convert_alpha() if pygame.display.get_surface() is not None else img
    except (pygame.error, FileNotFoundError):
        return None


def _torch_light():
    if "luz" not in _BACKDROP:
        light = pygame.Surface((W, H))
        for x in range(120, W, 180):
            for r, a in ((90, 10), (55, 16), (28, 26)):
                pygame.draw.circle(light, (a * 2, a, a // 3), (x, 258), r)
        _BACKDROP["luz"] = light
    return _BACKDROP["luz"]


def fighter_key(index):
    """Personagem escolhido → lutador do modo (quem ainda não luta aqui vira o Aryel)."""
    key = CHARACTERS[index].key if 0 <= index < len(CHARACTERS) else "aryel"
    return key if key in L.FIGHTER_KEYS else L.FIGHTER_KEYS[0]


def portrait(key, size=60):
    """Rosto do lutador (recorte da cabeça do quadro de guarda) para o HUD."""
    cache = _BACKDROP.setdefault("rostos", {})
    if (key, size) not in cache:
        img, _, P = L.Bank.get(key, "guarda")
        hx, hy = P["head"]
        u = R.U
        box = pygame.Rect(round((hx - 14) * u), round((hy - 17) * u), 30 * u, 30 * u).clip(img.get_rect())
        head = img.subsurface(box).copy()
        cache[(key, size)] = pygame.transform.smoothscale(head, (size, size))
    return cache[(key, size)]


class LutaScene(Scene):
    music = "arena"
    phase = "playing"
    show_cursor = False

    def __init__(self, game, keys=None, slots=(1, 2), seed=None):
        super().__init__(game)
        session = game.session
        if keys is None:
            chars = {s.slot: s.char for s in session.slots} if session is not None else {}
            keys = tuple(fighter_key(chars.get(s, 0)) for s in slots)
        self.slots = slots
        controls = []
        for s in slots:
            inp = game.inputs.get(s)
            if inp is not None:
                inp.set_layout("soccer")          # CORRER = FORTE, CONDUZIR = ESPECIAL, MARCAR = DEFESA
            controls.append(inp)
        self.fight = L.Fight(keys, slots, controls, seed=seed, sound=self._sound, buzz=self._buzz)
        self.paused = False
        self.show_boxes = False
        self.embers = [(random.randrange(W), random.uniform(120, FLOOR), random.uniform(0.2, 0.7)) for _ in range(36)]
        self._published = None
        self._lost = [f.hp for f in self.fight.fighters]     # vida "fantasma" que desce devagar
        self._trail = [[] for _ in self.fight.fighters]       # quadros de antes, para o rastro do golpe
        self._ghosts = {}
        coliseu_backdrop(game.assets)

    # ── celular ───────────────────────────
    def phone_mode(self):
        return "luta"

    def hud_layout(self):
        return "soccer"

    def active_slots(self):
        return tuple(s for s in self.slots if s is not None)

    def _sound(self, name, volume=0.5, at=None):
        self.assets.play(name, volume)

    def _buzz(self, slot, pattern):
        try:
            hub.buzz(slot, pattern)
        except Exception:
            pass

    def _publish(self):
        state = tuple((round(f.energy, 2), self.fight.state) for f in self.fight.fighters)
        if state == self._published:
            return
        self._published = state
        for f in self.fight.fighters:
            if f.slot is not None:
                hub.publish_slot(f.slot, energy=round(f.energy * 10), emax=round(L.MAX_ENERGY * 10),
                                 ecost=round(L.SPECIAL_COST * 10))

    # ── laço ──────────────────────────────
    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.paused:
                    self._leave()
                else:
                    self.paused = True
                    hub.set_phase("paused", mode="luta", active=self.active_slots())
            elif event.key == pygame.K_F4:
                self.show_boxes = not self.show_boxes      # caixas de golpe, corpo e empurrão
            elif self.paused and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._resume()

    def _resume(self):
        self.paused = False
        hub.set_phase("playing", mode="luta", active=self.active_slots())

    def update(self):
        super().update()
        inputs = [self.game.inputs[s] for s in self.active_slots() if s in self.game.inputs]
        if self.paused:
            if any(i.pressed("attack") or i.pressed("pause") for i in inputs):
                self._resume()
            elif any(i.pressed("cancel") and not i.pressed("special") for i in inputs) and self.ticks > 1:
                pass
            return
        if any(i.pressed("pause") for i in inputs):
            self.paused = True
            hub.set_phase("paused", mode="luta", active=self.active_slots())
            return
        self.fight.update()
        for i, f in enumerate(self.fight.fighters):
            self._record_trail(i, f)
            self._lost[i] = max(f.hp, self._lost[i] - 4) if self._lost[i] > f.hp else f.hp
        if self.ticks % 6 == 0:
            self._publish()
        if self.fight.state == "fim" and self.fight.t > 170:
            self._finish()

    def _finish(self):
        from .play import ResultsScene
        fight = self.fight
        a, b = fight.fighters
        if fight.winner is None:
            title, color, winners = "EMPATE", theme.BONE, [a, b]
        else:
            w = fight.fighters[fight.winner]
            title, color, winners = f"{w.spec.name.upper()} VENCEU", w.spec.color, [w]
        lines = [("ROUNDS", f"{a.wins} x {b.wins}")]
        for f in (a, b):
            label = f"P{f.slot}" if f.slot is not None else "CPU"
            lines.append((f"{label} {f.spec.name.upper()}", f"{max(0, f.hp)} DE VIDA"))
        sprites = [SimpleNamespace(sprites=self.assets.sprites[w.key]) for w in winners]
        for s in self.active_slots():
            self.game.inputs[s].set_layout("battle")
        self.game.change(ResultsScene(self.game, Result(title, color, sprites, lines, score=(a.wins, b.wins))))

    def _leave(self):
        from .menus import TitleScene
        for s in self.active_slots():
            self.game.inputs[s].set_layout("battle")
        self.game.change(TitleScene(self.game))

    # ── desenho ───────────────────────────
    def draw(self, screen):
        fight = self.fight
        sx = sy = 0
        if fight.shake:
            sx = random.randint(-fight.shake // 2, fight.shake // 2)
            sy = random.randint(-fight.shake // 3, fight.shake // 3)
        view = screen
        view.blit(coliseu_backdrop(self.assets), (sx, sy))
        self._draw_torches(view, sx, sy)
        order = sorted(fight.fighters, key=lambda f: f.state in ("golpe", "especial"))
        for f in fight.fighters:
            self._draw_shadow(view, f, sx, sy)
        for f in order:
            self._draw_vehicle(view, f, sx, sy, behind=True)
            self._draw_fighter(view, f, sx, sy)
            self._draw_vehicle(view, f, sx, sy, behind=False)
            self._draw_weapon(view, f, sx, sy)
            self._draw_held_ball(view, f, sx, sy)
        for p in fight.projectiles:
            self._draw_projectile(view, p, sx, sy)
        self._draw_effects(view, sx, sy)
        if self.show_boxes:
            self._draw_boxes(view)
        if fight.super_freeze:
            self._draw_super_cutin(view)
        self._draw_hud(view)
        self._draw_banner(view)
        if self.paused:
            self._draw_pause(view)

    def _draw_torches(self, s, sx, sy):
        t = self.ticks
        s.blit(_torch_light(), (sx, sy), special_flags=pygame.BLEND_RGB_ADD)
        for i, x in enumerate(range(120, W, 180)):
            flick = math.sin(t * 0.3 + i * 1.7) * 1.5
            for k, (c, rr) in enumerate((((255, 120, 40), 7), ((255, 190, 80), 5), ((255, 245, 190), 2))):
                pygame.draw.circle(s, c, (x + sx, int(258 - k * 2 - abs(flick) + sy)), max(1, rr + int(flick * 0.4)))
        for i, (x, y, v) in enumerate(self.embers):
            yy = (y - t * v) % (FLOOR - 110) + 110
            xx = x + math.sin(t * 0.03 + i) * 8
            s.fill((255, 170, 80) if i % 3 else (255, 230, 160), (int(xx) + sx, int(yy) + sy, 2, 2))

    def _draw_shadow(self, s, f, sx, sy):
        w = 110 if f.pose != "caido" else 200
        k = max(0.35, 1 - f.y / 300)
        rect = pygame.Rect(0, 0, int(w * k), int(18 * k))
        rect.center = (int(f.x) + sx + (30 * f.facing if f.pose == "caido" else 0), FLOOR + sy)
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())
        s.blit(shadow, rect)

    def _fighter_image(self, f):
        right, left, _ = f.view_frame()
        img = right if f.facing > 0 else left
        if f.flash and f.flash % 2:
            img = img.copy()
            img.fill((90, 60, 60, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return img

    # ── rastro dos golpes ─────────────────
    def _trail_on(self, f):
        """Rastro só no golpe saindo (passo ativo e o de antes) e nos especiais."""
        if f.state == "especial":
            return True
        if f.state != "golpe" or f.move is None:
            return False
        i, _ = f.move_step()
        return any(a - 1 <= i <= a for a in f.move.active)

    def _record_trail(self, i, f):
        if self.fight.freeze or self.fight.super_freeze:
            return
        trail = self._trail[i]
        if self._trail_on(f):
            trail.append((f.view, f.facing, f.x, f.y))
            del trail[:-6]
        elif trail:
            del trail[0]

    def _ghost(self, f, view, facing):
        key = (f.key, view, facing, f.side)
        img = self._ghosts.get(key)
        if img is None:
            right, left, _ = L.Bank.get(f.key, view)
            img = (right if facing > 0 else left).copy()
            tint = theme.SLOT_COLORS.get(f.slot, (255, 255, 255))
            img.fill((*mix_light(tint), 255), special_flags=pygame.BLEND_RGBA_MULT)
            img.fill((40, 40, 50, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if len(self._ghosts) > 160:
                self._ghosts.clear()
            self._ghosts[key] = img
        return img

    def _draw_trail(self, s, f, sx, sy):
        trail = self._trail[self.fight.fighters.index(f)]
        u = R.U
        for n, back in enumerate((4, 2)):
            if len(trail) <= back:
                continue
            view, facing, x, y = trail[-1 - back]
            if view == f.view and abs(x - f.x) < 2:
                continue
            img = self._ghost(f, view, facing)
            img.set_alpha(40 + 32 * n)
            ox = x - (R.ROOT_X * u if facing > 0 else (R.CW - R.ROOT_X) * u)
            oy = FLOOR - y - R.GROUND * u
            s.blit(img, (round(ox) + sx, round(oy) + sy))

    def _draw_fighter(self, s, f, sx, sy):
        self._draw_trail(s, f, sx, sy)
        img = self._fighter_image(f)
        u = R.U
        ox = f.x - (R.ROOT_X * u if f.facing > 0 else (R.CW - R.ROOT_X) * u)
        oy = FLOOR - f.y - R.GROUND * u
        if f.state == "levantando" and f.t % 4 < 2 or f.invuln and f.state == "livre" and f.t % 4 < 2:
            img = img.copy()
            img.set_alpha(150)
        if f.special and f.special.get("super") and self.fight.super_freeze:
            glow = img.copy()
            glow.fill((*ENERGY, 0), special_flags=pygame.BLEND_RGBA_MAX)
            glow.set_alpha(110 + int(60 * math.sin(self.ticks * 0.5)))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                s.blit(glow, (ox + dx + sx, oy + dy + sy))
        s.blit(img, (round(ox) + sx, round(oy) + sy))

    def _draw_weapon(self, s, f, sx, sy):
        """A arma de perto aparece só no golpe FORTE."""
        if f.state != "golpe" or f.move is None or not f.move.weapon:
            return
        P = f.view_frame()[2]
        hx, hy = f.to_world(P["near_hand"])
        ang = P["near_hand_dir"]
        d = R.dirv(ang)
        dx, dy = d[0] * f.facing, d[1]
        hx, hy = hx + sx, hy + sy
        if f.key == "aryel":                     # capacete de moto na mão
            cx, cy = hx + dx * 14, hy + dy * 14
            pygame.draw.circle(s, (20, 14, 24), (int(cx), int(cy)), 17)
            pygame.draw.circle(s, (210, 60, 54), (int(cx), int(cy)), 15)
            pygame.draw.circle(s, (240, 120, 100), (int(cx - 5), int(cy - 6)), 5)
            visor = pygame.Rect(0, 0, 18, 9)
            visor.center = (int(cx + dx * 6), int(cy + dy * 6))
            pygame.draw.ellipse(s, (30, 34, 50), visor)
            pygame.draw.line(s, (160, 200, 230), (visor.x + 3, visor.y + 2), (visor.x + 9, visor.y + 2))
            pygame.draw.line(s, (250, 250, 250), (int(cx - 12), int(cy + 4)), (int(cx + 12), int(cy + 4)), 2)
        else:                                    # cabo de rede: chicote com o plugue na ponta
            length = 30 + (f.move.reach if f.pose == "forte2" else 6)
            sway = math.sin(self.ticks * 0.6) * 6 if f.pose != "forte2" else 0
            pts = []
            for i in range(9):
                t = i / 8
                bend = math.sin(t * math.pi) * (10 if f.pose == "forte1" else 3) + sway * t
                pts.append((hx + dx * length * t - dy * bend * f.facing, hy + dy * length * t + dx * bend * f.facing))
            pygame.draw.lines(s, (14, 20, 40), False, pts, 6)
            pygame.draw.lines(s, (70, 130, 220), False, pts, 4)
            pygame.draw.lines(s, (150, 196, 250), False, [(x, y - 1) for x, y in pts], 1)
            ex, ey = pts[-1]
            plug = pygame.Rect(0, 0, 10, 10)
            plug.center = (int(ex), int(ey))
            pygame.draw.rect(s, (20, 20, 26), plug.inflate(2, 2))
            pygame.draw.rect(s, (226, 232, 236), plug)
            pygame.draw.rect(s, (236, 188, 62), (plug.x + 2, plug.y + 2, 6, 2))

    def _draw_vehicle(self, s, f, sx, sy, behind):
        """SUPER do Aryel: a moto (a roda de trás atrás dele, o resto na frente)."""
        if f.pose not in ("moto", "moto_grau"):
            return
        wheelie = 16 if f.pose == "moto_grau" else 0
        base = pygame.Surface((240, 140), pygame.SRCALPHA)
        c = (40, 40, 48)
        red = (210, 60, 54)
        # rodas
        for wx in (50, 190):
            pygame.draw.circle(base, (14, 12, 18), (wx, 112), 25)
            pygame.draw.circle(base, (44, 42, 52), (wx, 112), 21)
            pygame.draw.circle(base, (170, 170, 180), (wx, 112), 9)
            for k in range(6):
                a = k * math.pi / 3 + self.ticks * 0.6
                pygame.draw.line(base, (120, 120, 130), (wx, 112), (wx + math.cos(a) * 18, 112 + math.sin(a) * 18), 2)
        if not behind:
            pygame.draw.polygon(base, (20, 18, 24), [(56, 100), (92, 66), (168, 62), (196, 104), (150, 104), (120, 92)])
            pygame.draw.polygon(base, red, [(60, 98), (94, 70), (164, 66), (190, 100), (152, 100), (120, 88)])
            pygame.draw.polygon(base, (240, 120, 100), [(100, 72), (160, 68), (150, 76), (104, 78)])
            pygame.draw.rect(base, (24, 22, 30), (70, 60, 50, 10), border_radius=4)          # banco
            pygame.draw.line(base, (180, 180, 190), (176, 64), (196, 40), 4)                  # garfo
            pygame.draw.line(base, (60, 60, 70), (186, 40), (206, 36), 4)                     # guidão
            pygame.draw.circle(base, (255, 240, 170), (206, 64), 6)                           # farol
            pygame.draw.line(base, c, (40, 96), (80, 96), 6)                                  # escapamento
            pygame.draw.circle(base, (200, 200, 210), (36, 96), 4)
        img = base if f.facing > 0 else pygame.transform.flip(base, True, False)
        if wheelie:
            img = pygame.transform.rotate(img, wheelie * f.facing)
        rect = img.get_rect(midbottom=(int(f.x) + sx + 10 * f.facing, FLOOR + sy + 6 + wheelie // 2))
        s.blit(img, rect)
        if not behind and self.ticks % 3 == 0:
            self.fight.effects.append(L.Effect("poeira", f.x - 80 * f.facing, FLOOR - 6, 18, color=(150, 150, 160),
                                               vx=-2 * f.facing, vy=-0.6, size=0.8))

    def _draw_held_ball(self, s, f, sx, sy):
        """Bola na mão do Cauanzera na ENTERRADA e no preparo do arremesso."""
        if f.key != "cauanzera" or f.pose not in ("basquete1", "enterrada1", "enterrada2"):
            return
        P = f.view_frame()[2]
        a = f.to_world(P["near_hand"])
        b = f.to_world(P["far_hand"])
        x, y = (a[0] + b[0]) / 2 + 6 * f.facing + sx, min(a[1], b[1]) - 8 + sy
        self._ball(s, x, y, 15, "basquete", self.ticks * 0.1)

    def _ball(self, s, x, y, r, kind, spin):
        x, y = int(x), int(y)
        if kind == "basquete":
            pygame.draw.circle(s, (60, 24, 8), (x, y), r + 1)
            pygame.draw.circle(s, (226, 112, 36), (x, y), r)
            pygame.draw.circle(s, (250, 160, 80), (x - r // 3, y - r // 3), r // 3)
            c, sn = math.cos(spin) * r, math.sin(spin) * r
            pygame.draw.line(s, (60, 24, 8), (x - c, y - sn), (x + c, y + sn), 2)
            pygame.draw.line(s, (60, 24, 8), (x + sn, y - c), (x - sn, y + c), 2)
        elif kind == "volei":
            pygame.draw.circle(s, (30, 34, 50), (x, y), r + 1)
            pygame.draw.circle(s, (244, 240, 226), (x, y), r)
            for k, col in enumerate(((250, 210, 60), (60, 110, 220))):
                a = spin + k * 2.1
                pygame.draw.arc(s, col, (x - r, y - r, 2 * r, 2 * r), a, a + 1.6, 4)
        else:                                       # moeda girando
            w = max(3, int(abs(math.cos(spin)) * r * 2))
            rect = pygame.Rect(0, 0, w, r * 2)
            rect.center = (x, y)
            pygame.draw.ellipse(s, (120, 80, 10), rect.inflate(2, 2))
            pygame.draw.ellipse(s, (250, 210, 80), rect)
            if w > 8:
                pygame.draw.ellipse(s, (255, 240, 160), rect.inflate(-w // 2, -r))

    def _draw_projectile(self, s, p, sx, sy):
        if p.delay > 0:
            return
        for k in range(1, 4):                       # rastro
            tx, ty = p.x - p.vx * k * 1.5 + sx, p.y - p.vy * k * 1.5 + sy
            pygame.draw.circle(s, (255, 240, 200) if p.kind == "moeda" else (255, 200, 140),
                               (int(tx), int(ty)), max(1, p.radius // 2 - k * 2))
        self._ball(s, p.x + sx, p.y + sy, p.radius, p.kind, p.spin)

    def _draw_effects(self, s, sx, sy):
        for e in self.fight.effects:
            k = e.age / e.life
            x, y = int(e.x) + sx, int(e.y) + sy
            if e.kind == "faisca":
                size = e.size
                if e.age <= 2:                      # clarão do contato (dois quadros)
                    pygame.draw.circle(s, (255, 255, 255), (x, y), int(14 * size))
                    pygame.draw.circle(s, e.color, (x, y), int(14 * size), 2)
                if k < 0.7:                         # anel que abre
                    pygame.draw.circle(s, e.color, (x, y), int((12 + 46 * k) * size), max(1, int(3 * (1 - k))))
                n = 10
                for i in range(n):
                    a = i * math.tau / n + 0.3
                    ca = math.cos(a)
                    reach = 1.0 + 0.7 * max(0.0, ca * e.dirx)        # espirra para o lado do golpe
                    rr = (18 + 36 * k) * size * reach * (1 if i % 2 == 0 else 0.5) * (1 - 0.45 * k)
                    wd = 0.16 * (1 - k * 0.7)
                    p1 = (x + math.cos(a - wd) * 5, y + math.sin(a - wd) * 5)
                    p2 = (x + ca * rr, y + math.sin(a) * rr)
                    p3 = (x + math.cos(a + wd) * 5, y + math.sin(a + wd) * 5)
                    pygame.draw.polygon(s, (255, 252, 226) if k < 0.35 else e.color, [p1, p2, p3])
            elif e.kind == "lasca":
                tail = (x - e.vx * 2.2, y - e.vy * 2.2)
                col = (255, 255, 240) if k < 0.3 else e.color
                pygame.draw.line(s, col, (x, y), tail, 3 if k < 0.4 else 2 if k < 0.75 else 1)
            elif e.kind == "defesa":
                r = int(22 + 24 * k)
                face = -e.dirx                   # o escudo abre virado para quem bateu
                rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
                mid = 0 if face > 0 else math.pi
                for off, wd in ((-0.95, 4), (0.0, 5), (0.95, 4)):
                    a0 = mid + off - 0.38
                    pygame.draw.arc(s, e.color, rect, -(a0 + 0.76), -a0, max(1, int(wd * (1 - k))))
                if k < 0.3:
                    pygame.draw.circle(s, (236, 246, 255), (x, y), int(9 * (1 - k)))
            elif e.kind == "poeira":
                r = int((6 + 10 * k) * e.size)
                dust = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(dust, (*e.color, int(150 * (1 - k))), (r, r), r)
                s.blit(dust, (x - r, y - r))
            elif e.kind == "explosao":
                r = int(20 + 70 * k)
                for rr, col in ((r, (255, 120, 50)), (int(r * 0.7), (255, 200, 80)), (int(r * 0.35), (255, 250, 220))):
                    pygame.draw.circle(s, col, (x, y), max(1, rr))
            elif e.kind == "moeda":
                self._ball(s, x, y, 8, "moeda", e.age * 0.4)
            elif e.kind == "texto":
                self.ui.text(s, e.text, theme.S, e.color, (x, y))

    def _draw_boxes(self, s):
        for f in self.fight.fighters:
            for r in f.hurtboxes():
                pygame.draw.rect(s, (80, 150, 255), r, 1)
            pygame.draw.rect(s, (250, 220, 70), f.pushbox(), 1)
            for box in f.hitboxes():
                pygame.draw.circle(s, (255, 60, 60), (int(box[0]), int(box[1])), int(box[2]), 2)

    def _draw_super_cutin(self, s):
        f = self.fight.super_user
        if f is None:
            return
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((6, 8, 30, 110))
        s.blit(veil, (0, 0))
        t = L.SUPER_FREEZE - self.fight.super_freeze
        band = pygame.Rect(0, 150, W, 70)
        slide = min(1.0, t / 8)
        stripe = pygame.Surface(band.size, pygame.SRCALPHA)
        stripe.fill((*ENERGY, 170))
        s.blit(stripe, (int(-W * (1 - slide)) if f.side == 0 else int(W * (1 - slide)), band.y))
        face = portrait(f.key, 64)
        if f.facing < 0:
            face = pygame.transform.flip(face, True, False)
        fx = 60 if f.side == 0 else W - 124
        s.blit(face, (fx, band.y + 3))
        self.ui.text(s, f.spec.super, theme.M, (255, 255, 255), (W // 2, band.centery))

    # ── HUD ───────────────────────────────
    def _frame(self, s, rect, fill=(18, 12, 24)):
        pygame.draw.rect(s, (8, 4, 12), rect.inflate(6, 6))
        pygame.draw.rect(s, (150, 118, 70), rect.inflate(4, 4))
        pygame.draw.rect(s, fill, rect)

    def _draw_hud(self, s):
        fight = self.fight
        for i, f in enumerate(fight.fighters):
            flip = i == 1
            px = 16 if not flip else W - 80
            box = pygame.Rect(px, 12, 64, 64)
            self._frame(s, box, (54, 40, 66))
            face = portrait(f.key, 64)
            s.blit(pygame.transform.flip(face, True, False) if flip else face, box)
            # vida
            bw = 318
            bx = 96 if not flip else W - 96 - bw
            bar = pygame.Rect(bx, 20, bw, 20)
            self._frame(s, bar, (70, 18, 26))
            frac = max(0.0, f.hp / f.max_hp)
            ghost = max(0.0, self._lost[i] / f.max_hp)
            gw, fw = int(bw * ghost), int(bw * frac)
            if flip:
                s.fill((255, 214, 120), (bx + bw - gw, 20, gw, 20))
                fr = pygame.Rect(bx + bw - fw, 20, fw, 20)
            else:
                s.fill((255, 214, 120), (bx, 20, gw, 20))
                fr = pygame.Rect(bx, 20, fw, 20)
            low = frac < 0.25 and (self.ticks // 8) % 2
            col = (240, 90, 70) if low else f.spec.color
            s.fill(col, fr)
            s.fill(tuple(min(255, c + 70) for c in col), (fr.x, fr.y + 2, fr.w, 4))
            s.fill(tuple(max(0, c - 50) for c in col), (fr.x, fr.y + 15, fr.w, 5))
            for k in range(1, 10):
                pygame.draw.line(s, (20, 12, 24), (bx + bw * k // 10, 36), (bx + bw * k // 10, 39))
            name = f.spec.name.upper()
            label = f"P{f.slot} {name}" if f.slot is not None else name
            self.ui.text(s, label, theme.XS, (255, 238, 200), (bx if not flip else bx + bw, 54),
                         anchor="midleft" if not flip else "midright")
            # rounds ganhos
            for k in range(L.ROUNDS_TO_WIN):
                gx = (bx + bw - 12 - k * 18) if not flip else (bx + 12 + k * 18)
                self._gem(s, gx, 54, k < f.wins, GOLD)
            # SUPER: 3 cargas de energia azul
            self._draw_energy(s, f, flip)
            if f.combo >= 2:                         # sequência que este lutador está levando
                tx = W - 40 if not flip else 40
                self.ui.text(s, f"{f.combo} GOLPES!", theme.S, (170, 225, 255), (tx, 150),
                             anchor="midright" if not flip else "midleft")
        clock = pygame.Rect(W // 2 - 40, 8, 80, 66)
        self._frame(s, clock, (26, 16, 30))
        sec = fight.seconds()
        self.ui.text(s, f"{sec:02d}", theme.M, (255, 120, 90) if sec <= 10 and fight.state == "luta" else (255, 228, 140),
                     (W // 2, 34))
        self.ui.text(s, f"ROUND {fight.round}", theme.XS, (200, 180, 160), (W // 2, 62))

    def _gem(self, s, x, y, on, c):
        pts = [(x, y - 7), (x + 6, y), (x, y + 7), (x - 6, y)]
        pygame.draw.polygon(s, (14, 8, 20), [(px + 1, py + 1) for px, py in pts])
        pygame.draw.polygon(s, c if on else (50, 40, 60), pts)
        if on:
            pygame.draw.polygon(s, (255, 255, 255), [(x, y - 5), (x + 2, y - 1), (x, y)])

    def _draw_energy(self, s, f, flip):
        n = int(f.energy + 1e-6)
        part = f.energy - n
        x0 = 20 if not flip else W - 20 - 3 * 66 + 8
        for k in range(3):
            bx = x0 + (k if not flip else 2 - k) * 66
            rr = pygame.Rect(bx, H - 34, 58, 14)
            self._frame(s, rr, (24, 30, 56))
            fill = 1 if k < n else (part if k == n else 0)
            fw = int(58 * fill)
            fr = pygame.Rect(bx + (58 - fw if flip else 0), H - 34, fw, 14)
            s.fill(ENERGY, fr)
            if fill >= 1:
                s.fill((200, 232, 255), (fr.x, fr.y + 2, fr.w, 3))
        if n >= 3:
            label, color = "SUPER PRONTO!", (255, 255, 255) if (self.ticks // 10) % 2 else (200, 232, 255)
        elif n >= 1:
            label, color = f"ESPECIAL x{n}", (200, 232, 255)
        else:
            label, color = "ENERGIA", (140, 160, 200)
        self.ui.text(s, label, theme.XS, color, (x0 if not flip else x0 + 3 * 66 - 8, H - 50),
                     anchor="midleft" if not flip else "midright")

    def _draw_banner(self, s):
        fight = self.fight
        if fight.state == "intro":
            if fight.t < 60:
                k = min(1.0, fight.t / 10)
                size = theme.XL if k >= 1 else theme.L
                self.ui.text(s, f"ROUND {fight.round}", size, (255, 228, 140), (W // 2, 220))
                if fight.round > 1 and fight.fighters[0].wins == fight.fighters[1].wins == L.ROUNDS_TO_WIN - 1:
                    self.ui.text(s, "ROUND FINAL", theme.S, (240, 110, 90), (W // 2, 262))
            else:
                self.ui.text(s, "LUTEM!", theme.XL, (255, 255, 255) if (fight.t // 4) % 2 else (255, 210, 120),
                             (W // 2, 220))
        elif fight.state == "ko":
            title = getattr(fight, "ko_title", "NOCAUTE!")
            self.ui.text(s, title, theme.XL, (255, 90, 70) if title == "NOCAUTE!" else (255, 228, 140), (W // 2, 200))
            if fight.t > 50:
                self.ui.text(s, fight.round_title(), theme.M, (255, 238, 200), (W // 2, 256))
        elif fight.state == "fim":
            if fight.winner is None:
                self.ui.text(s, "EMPATE", theme.XL, (255, 228, 140), (W // 2, 210))
            else:
                w = fight.fighters[fight.winner]
                self.ui.text(s, f"{w.spec.name.upper()} VENCEU!", theme.L, w.spec.color, (W // 2, 210))

    def _draw_pause(self, s):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        s.blit(veil, (0, 0))
        self.ui.text(s, "PAUSA", theme.L, theme.BRASS, (W // 2, 200))
        self.ui.hints(s, [("ATACAR / ENTER", "CONTINUAR"), ("ESC", "SAIR DA LUTA")], (W // 2, 260))
        self.ui.text(s, "F4 MOSTRA AS CAIXAS DE GOLPE", theme.XS, theme.MUTED, (W // 2, 300))


def start_luta(game):
    """Luta direto do menu (os dois lutadores escolhidos na seleção)."""
    session = game.session
    slots = tuple(s.slot for s in session.slots[:2])
    return LutaScene(game, slots=slots)
