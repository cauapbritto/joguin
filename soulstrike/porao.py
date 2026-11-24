"""O porão da Casa (abre ao zerar a campanha): o Cristal da IARA e o portão da Arena sem Fim.

Do quintal, ATACAR no alçapão do porão aberto leva o grupo inteiro para baixo. É escuro: só as
velas, o Cristal, a luz da escada e o portão roxo iluminam (e um pouquinho em volta de cada um).

* O Cristal, no meio, numa redoma: ATACAR conversa com a IARA. O que ela fala muda com quantas
  vezes a campanha foi zerada (``IARA_LINES``).
* O portão da ARENA SEM FIM (``arena_sem_fim.py``): ATACAR leva a turma para as ondas que não
  acabam. A placa embaixo mostra o recorde.
* A escada do canto volta para o quintal.

Segredo (``lampada``): ficar parado 10 s no escuro (longe de toda luz) faz aparecer o versículo
gravado na parede: Salmos 119:105.
"""
import math

import pygame

from . import arena_sem_fim, casa_art as art, janelas, pecas, progress, segredos, theme
from .arena import MAPS_BY_KEY
from .campaign import CoopMatch, _spread
from .casa import Decor
from .matches import Result
from .sotao import _piece

PORAO_MAP = "porao_casa"
T = 40
TOP = 3 * T
BACK = pygame.Rect(T, TOP + T, 22 * T, 3 * T)            # a parede de pedra do fundo
STAIRS = pygame.Rect(56, BACK.y + 8, 128, BACK.h - 8)    # o vão da escada (na parede)
STAIRS_SPOT = pygame.Rect(56, BACK.bottom - 4, 128, 44)  # na frente da escada: ATACAR sobe
GATE = pygame.Rect(650, BACK.y + 10, 180, BACK.h - 10)   # o arco do portão da arena (na parede)
GATE_SPOT = pygame.Rect(660, BACK.bottom - 4, 160, 50)
CRYSTAL = (470, TOP + 8 * T)                             # o pé do pedestal do Cristal
CANDLES = ((250, TOP + 5 * T + 10), (640, TOP + 6 * T + 20), (830, TOP + 11 * T), (90, TOP + 11 * T + 10))
VERSE = ("LÂMPADA PARA OS MEUS PÉS É TUA PALAVRA", "E LUZ PARA O MEU CAMINHO.", "SALMOS 119:105")
VERSE_AT = (430, BACK.y + 30)
IARA = (60, 230, 255)
PURPLE = (190, 120, 255)
REACH = 80
STILL_FRAMES = 10 * 60                                   # parado no escuro para o versículo aparecer
DARK = 165                                               # o quanto o porão é escuro (0 a 255)

# o que a IARA fala, pela quantidade de vezes que a campanha foi zerada (1, 2, 3 ou mais)
IARA_LINES = {
    1: ("...VOCÊS ME TIRARAM DA TOMADA. OBRIGADA. EU ACHO.",
        "ESSE CACO É O QUE SOBROU DO CRISTAL. É AQUI EMBAIXO QUE EU FICO AGORA.",
        "LÁ NA MANSÃO, O CARIMBO PARECIA TÃO CERTO. DAQUI DE BAIXO, NEM TANTO.",
        "QUER TREINAR? O PORTÃO ALI DO LADO NÃO ACABA NUNCA. EU CONTO AS ONDAS."),
    2: ("VOCÊS VOLTARAM. É A SEGUNDA VEZ QUE ME TIRAM DO ESCURO.",
        "EU AINDA OUÇO O CARIMBO, LÁ LONGE... MAS ELE NÃO MANDA MAIS EM MIM.",
        "O BORBA JR DEIXOU UM PARAFUSO AQUI EMBAIXO. NÃO CONTEM PRA ELE.",
        "A RACHADURA DO CRISTAL DIMINUIU. ACHO QUE É POR CAUSA DE VOCÊS."),
    3: ("DE NOVO? VOCÊS NÃO CANSAM, HEIN. EU GOSTO.",
        "A CAMPANHA JÁ FOI ZERADA {n} VEZES. EU CONTEI TODAS.",
        "O CRISTAL ESTÁ QUASE INTEIRO. QUANDO FICAR, EU QUERO VER O SOL.",
        "AGORA VAI LÁ NA ARENA. QUERO VER BATER O RECORDE."),
}


def times_cleared():
    return int(progress.load().get("vezes_zerada", 0) or 0)


def iara_lines(n=None):
    n = times_cleared() if n is None else n
    lines = IARA_LINES[max(1, min(3, n))]
    return [line.format(n=n) for line in lines]


class IaraMenu:
    """A conversa com a IARA no Cristal: uma fala por vez. ATACAR passa, ESQUIVA fecha."""

    kind = "iara"

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.times = times_cleared()
        self.lines = iara_lines(self.times)
        self.index = 0
        self.age = 0

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True
        if any(inp.pressed(a) for a in ("dodge", "special", "cancel")):
            return False
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.index += 1
            self.match.assets.play("bip", 0.3)
            return self.index < len(self.lines)
        return True

    def pick(self, item):
        return False

    def snapshot(self):
        return None

    def size(self, ui):
        return 420, 128

    def draw(self, screen, ui, cam, rect=None):
        if rect is None:
            rect = janelas.default_rect(self.size(ui), cam, self.fighter)
        body = janelas.panel(screen, ui, rect, self.fighter, "IARA", f"FALA {min(self.index + 1, len(self.lines))} "
                             f"DE {len(self.lines)}", accent=IARA)
        gem = [(body.x + 22, body.y + 6), (body.x + 34, body.y + 28), (body.x + 28, body.y + 56),
               (body.x + 16, body.y + 56), (body.x + 10, body.y + 28)]
        pygame.draw.polygon(screen, (40, 160, 200), gem)
        pygame.draw.polygon(screen, (200, 250, 255), gem, 1)
        line = self.lines[min(self.index, len(self.lines) - 1)]
        for i, part in enumerate(ui.wrap(line, theme.XS, body.w - 60)[:3]):
            ui.text(screen, part, theme.XS, (220, 240, 250), (body.x + 50, body.y + 10 + i * 16), anchor="topleft",
                    shadow=False)
        vezes = "1 VEZ" if self.times == 1 else f"{self.times} VEZES"
        janelas.footer(screen, ui, rect, f"CAMPANHA ZERADA {vezes} · ATACAR: PASSAR")


def draw_crystal(s, x, y, frame=0):
    """O pedestal, o caco do Cristal com a rachadura e a redoma de vidro (pé em x, y)."""
    ped = pecas.image("porao_pedestal")
    if ped is not None:
        s.blit(ped, ped.get_rect(midbottom=(x, y)))
    top = y - 40
    gem = [(x, top - 70), (x + 16, top - 36), (x + 8, top - 4), (x - 10, top - 4), (x - 18, top - 40)]
    pygame.draw.polygon(s, (40, 160, 200), gem)
    pygame.draw.polygon(s, (150, 245, 255), [(x, top - 70), (x + 4, top - 40), (x - 2, top - 8), (x - 18, top - 40)])
    pygame.draw.polygon(s, (230, 255, 255), gem, 1)
    pygame.draw.line(s, (20, 90, 120), (x + 2, top - 56), (x + 10, top - 30), 1)        # a rachadura
    dome = pygame.Surface((80, 100), pygame.SRCALPHA)
    pygame.draw.rect(dome, (200, 240, 255, 30), dome.get_rect(), border_top_left_radius=40, border_top_right_radius=40)
    pygame.draw.rect(dome, (220, 250, 255, 120), dome.get_rect(), 2, border_top_left_radius=40,
                     border_top_right_radius=40)
    pygame.draw.line(dome, (255, 255, 255, 140), (14, 26), (14, 70), 2)
    s.blit(dome, (x - 40, top - 96))


def draw_backdrop(s, ui=None):
    """A parede de pedra com a escada para o quintal, o portão da arena e as correntes."""
    r = BACK
    s.fill((30, 28, 36), r)
    for row, y in enumerate(range(r.y, r.bottom, 22)):
        off = 0 if row % 2 else 26
        for x in range(r.x - 26 + off, r.right, 52):
            c = 58 + ((x * 7 + y * 3) % 13) - 6
            pygame.draw.rect(s, (c, c - 4, c + 8), (max(r.x, x + 2), y + 2, 48, 18), border_radius=3)
    s.fill((24, 22, 30), (r.x, r.bottom - 8, r.w, 8))
    # a escada de pedra subindo para o quintal
    st = STAIRS
    pygame.draw.rect(s, (80, 76, 92), st.inflate(12, 8), 4, border_top_left_radius=44, border_top_right_radius=44)
    pygame.draw.rect(s, (12, 10, 16), st, border_top_left_radius=40, border_top_right_radius=40)
    for i in range(6):
        y = st.bottom - 4 - i * 18
        inset = i * 7
        c = 96 - i * 11
        s.fill((c, c - 4, c + 8), (st.x + 6 + inset, y - 12, st.w - 12 - inset * 2, 12))
        s.fill((c + 22, c + 18, c + 30), (st.x + 6 + inset, y - 12, st.w - 12 - inset * 2, 2))
    # o portão da arena: arco de pedra com o portal roxo
    g = GATE
    pygame.draw.rect(s, (70, 66, 80), g.inflate(28, 8), border_top_left_radius=90, border_top_right_radius=90)
    portal = pygame.Surface(g.size, pygame.SRCALPHA)
    pygame.draw.rect(portal, (60, 20, 100), portal.get_rect(), border_top_left_radius=86, border_top_right_radius=86)
    for k in range(8):
        pygame.draw.ellipse(portal, (150, 60, 230, min(255, 40 + k * 20)),
                            (g.w // 2 - 80 + k * 10, g.h // 2 - 44 + k * 6, 160 - k * 20, 100 - k * 12), 2)
    s.blit(portal, g.topleft)
    for x in (g.x - 30, g.right + 22):                                   # tochas
        s.fill((80, 60, 40), (x, g.y + 40, 8, 22))
        pygame.draw.polygon(s, (255, 180, 60), [(x - 2, g.y + 40), (x + 10, g.y + 40), (x + 4, g.y + 22)])
        pygame.draw.polygon(s, (255, 240, 160), [(x + 1, g.y + 40), (x + 7, g.y + 40), (x + 4, g.y + 30)])
    chain = pecas.image("porao_corrente")
    if chain is not None:
        for x in (330, 560):
            s.blit(chain, (x, r.y))
    # o versículo, gravado quase apagado (o segredo só acende a cor)
    if ui is not None:
        for i, line in enumerate(VERSE[:2]):
            ui.text(s, line, theme.XS, (52, 50, 62), (VERSE_AT[0], VERSE_AT[1] + i * 16), shadow=False)


class PoraoMatch(janelas.Janelas, CoopMatch):
    """O porão. ``story`` e ``walk`` só passam adiante para a Casa na volta."""

    lobby = True
    music = "casa"
    walk = False
    hud_title = "PORÃO"

    def __init__(self, game, run, story=False, walk=False, arrive=None):
        self.story = story
        self.walk = walk
        cfg = MAPS_BY_KEY[PORAO_MAP]
        n = len(run.session.slots)
        if arrive == "arena":                                # voltando da arena: na frente do portão
            starts = [(GATE_SPOT.centerx - 60 + 40 * i, GATE_SPOT.bottom + 30) for i in range(n)]
        else:
            starts = _spread(cfg.markers["S"], n)
        super().__init__(game, run, cfg.key, starts, (0.0, -1.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()
        self.going_up = False
        self.going_arena = False
        self.still = {}                                      # jogador -> (x, y, quadros parado no escuro)
        self.verse = 1.0 if segredos.is_found("lampada") else 0.0     # o quanto o versículo acendeu
        self.verse_found = segredos.is_found("lampada")
        self._holes = {}
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
        draw_backdrop(floor, self.game.ui)
        self.arena.walls.append(Wall(BACK.x, BACK.y, BACK.w, BACK.h - 16, visible=False))
        for x in (230, 610):
            self._put(_piece("porao_coluna"), x, BACK.bottom + 14, 30)
        self._put(_piece("porao_prateleira_potes"), 300, BACK.bottom + 40, 70)
        for x, y in ((60, TOP + 6 * T + 10), (98, TOP + 6 * T + 16), (78, TOP + 7 * T + 10), (880, TOP + 8 * T)):
            self._put(_piece("porao_barril"), x, y, 30)
        for x, y in ((150, TOP + 7 * T), (860, TOP + 6 * T + 20), (880, TOP + 12 * T - 6)):
            self._put(_piece("porao_caixa_madeira"), x, y, 40)
        for x, y in CANDLES:
            self._put(_piece("porao_candelabro"), x, y, 20)
        img = pygame.Surface((120, 190), pygame.SRCALPHA)
        pygame.draw.ellipse(img, (0, 0, 0, 90), (10, 172, 100, 18))
        draw_crystal(img, 60, 182)
        self.crystal = self._put(art.Baked(img, -60, -182), *CRYSTAL, 70)

    # ── consultas ────────────────────────────
    @property
    def objective_text(self):
        return "PORÃO · O CRISTAL DA IARA E A ARENA SEM FIM"

    def objective(self):
        return None

    def stairs_near(self, f):
        return f.alive_in_match and STAIRS_SPOT.inflate(20, 20).collidepoint(f.x, f.y)

    def gate_near(self, f):
        return f.alive_in_match and GATE_SPOT.inflate(20, 20).collidepoint(f.x, f.y)

    def crystal_near(self, f):
        x, y = CRYSTAL
        return f.alive_in_match and math.hypot(f.x - x, f.y - y) < REACH

    def lights(self):
        """(x, y, raio) de cada luz do porão (sem contar a luzinha em volta dos jogadores)."""
        x, y = CRYSTAL
        out = [(x, y - 80, 190), (STAIRS.centerx, STAIRS.bottom, 120), (GATE.centerx, GATE.bottom, 150)]
        out += [(cx, cy - 40, 90) for cx, cy in CANDLES]
        return out

    def in_dark(self, f):
        return all(math.hypot(f.x - x, f.y - y) > r for x, y, r in self.lights())

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            self._set_banner("PORÃO", "O CRISTAL E A ARENA SEM FIM", IARA)
        if self.banner and self.banner[3] > 130:
            self.banner = None
        self._update_verse()
        self.update_windows()

    def _update_verse(self):
        if self.verse_found:
            self.verse = min(1.0, self.verse + 0.02)
            return
        for p in self.alive_players:
            x, y, n = self.still.get(p, (p.x, p.y, 0))
            if math.hypot(p.x - x, p.y - y) > 2 or p in self.menus or not self.in_dark(p):
                self.still[p] = (p.x, p.y, 0)
                continue
            n += 1
            self.still[p] = (x, y, n)
            if n >= STILL_FRAMES:
                self.verse_found = True
                self.assets.play("magia", 0.4)
                segredos.find("lampada", self, VERSE_AT[0], VERSE_AT[1] + 70)
                return

    def interact(self, f):
        if self.stairs_near(f):
            if self.leaving_in:
                return True
            self.going_up = True
            self.assets.play("select", 0.45)
            self.leave_soon(self.leave)
            return True
        if self.gate_near(f):
            if self.leaving_in:
                return True
            self.going_arena = True
            self.assets.play("teletransporte", 0.45)
            self.leave_soon(self.leave)
            return True
        if self.crystal_near(f):
            self.menus[f] = IaraMenu(self, f)
            self.assets.play("magia", 0.35)
            return True
        return self.pick_ground(f)

    def _finish(self, won):
        self.won = won
        self.result = Result("PORÃO", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.escada import StairsTripScene
        if self.going_arena:
            from .scenes.campaign import arena_scene
            return StairsTripScene(self.game, lambda: arena_scene(self.game, self.run, self.story, walk=self.walk),
                                   "ENTRANDO NA ARENA SEM FIM", accent=PURPLE, door=True)
        from .scenes.campaign import hub_scene
        return StairsTripScene(self.game, lambda: hub_scene(self.game, self.run, story=self.story, walk=self.walk,
                                                            arrive="porao"), "SUBINDO PARA O QUINTAL")

    def restart_scene(self):
        from .scenes.campaign import porao_scene
        return porao_scene(self.game, self.run, story=self.story, walk=self.walk)

    # ── desenho ──────────────────────────────
    def _hole(self, r):
        """Furo de luz: alfa 0 no meio e DARK na borda (BLEND_RGBA_MIN abre a escuridão)."""
        if r not in self._holes:
            h = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
            h.fill((0, 0, 0, DARK))
            for k in range(r, 0, -4):
                a = round(DARK * (k / r) ** 1.6)
                pygame.draw.circle(h, (0, 0, 0, a), (r, r), k)
            self._holes[r] = h
        return self._holes[r]

    def draw_dark(self, screen):
        cam = self.camera
        dark = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, DARK))
        lights = self.lights() + [(p.x, p.y - 20, 70) for p in self.alive_players]
        for x, y, r in lights:
            r = max(8, round(r * cam.zoom)) if hasattr(cam, "zoom") else r
            sx, sy = cam.to_screen(x, y)
            dark.blit(self._hole(r), (round(sx) - r, round(sy) - r), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(dark, (0, 0))
        glow = pygame.Surface((240, 240), pygame.SRCALPHA)                 # o brilho do Cristal
        pulse = 0.75 + 0.25 * math.sin(self.frame * 0.05)
        for k in range(8):
            pygame.draw.circle(glow, (*IARA, round(7 * pulse)), (120, 120), 118 - k * 14)
        sx, sy = cam.to_screen(CRYSTAL[0], CRYSTAL[1] - 100)
        screen.blit(glow, (round(sx) - 120, round(sy) - 120))

    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        self.draw_dark(screen)
        if self.verse > 0:
            a = round(60 + 195 * self.verse)
            for i, line in enumerate(VERSE):
                sx, sy = cam.to_screen(VERSE_AT[0], VERSE_AT[1] + i * 16)
                img = pygame.Surface((420, 16), pygame.SRCALPHA)
                ui.text(img, line, theme.XS, (255, 236, 170) if i < 2 else (210, 190, 150), (210, 8), shadow=False)
                img.set_alpha(a)
                screen.blit(img, (round(sx) - 210, round(sy) - 8))
        sx, sy = cam.to_screen(GATE_SPOT.centerx, GATE_SPOT.y + 4)
        plate = pygame.Rect(0, 0, 200, 34)
        plate.midtop = (round(sx), round(sy))
        pygame.draw.rect(screen, (16, 12, 22), plate)
        pygame.draw.rect(screen, PURPLE, plate, 2)
        ui.text(screen, "ARENA SEM FIM", theme.XS, (210, 160, 255), (plate.centerx, plate.y + 10), shadow=False)
        rec = arena_sem_fim.record()
        ui.text(screen, f"RECORDE: ONDA {rec['onda']}" if rec else "RECORDE: NENHUM", theme.XS, (180, 170, 200),
                (plate.centerx, plate.y + 24), shadow=False)
        free = [p for p in self.alive_players if p not in self.menus]
        blink = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
        if any(self.stairs_near(p) for p in free):
            sx, sy = cam.to_screen(STAIRS_SPOT.centerx, STAIRS_SPOT.bottom + 14)
            ui.text(screen, "ATACAR: SUBIR PARA O QUINTAL", theme.XS, blink, (round(sx), round(sy)))
        if any(self.gate_near(p) for p in free):
            sx, sy = cam.to_screen(GATE_SPOT.centerx, GATE_SPOT.bottom + 24)
            ui.text(screen, "ATACAR: ENTRAR NA ARENA", theme.XS, blink, (round(sx), round(sy)))
        if any(self.crystal_near(p) for p in free):
            sx, sy = cam.to_screen(CRYSTAL[0], CRYSTAL[1] + 22)
            ui.text(screen, "ATACAR: FALAR COM A IARA", theme.XS, blink, (round(sx), round(sy)))
        self.draw_ground(screen, cam, ui)
        janelas.draw(self, screen, ui)


__all__ = ("PoraoMatch", "PORAO_MAP", "IaraMenu", "iara_lines")
