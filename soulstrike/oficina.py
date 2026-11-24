"""A oficina do Borba Jr (abre ao zerar o capítulo 2): a bancada e o estande de tiro.

Da Casa, ATACAR na porta da oficina aberta leva o grupo inteiro para dentro. Do lado esquerdo,
a bancada, o cavalete com o exoesqueleto pela metade, o painel de ferramentas e o suporte de armas:
ATACAR nele troca a arma do estande de quem apertou (só as que a turma já liberou; as outras ficam
com cadeado). Do lado direito, as 4 raias do estande.

DESAFIO DE 30 S: ATACAR numa baia começa a contagem para quem estiver nas baias. Os alvos levantam
sozinhos nas raias e ficam de pé por pouco tempo; ATACAR na baia atira na raia dela. Acertar rápido
dá mais ponto (NA MOSCA!), alvo longe dá mais, atirar com o alvo deitado perde ponto. Cada arma tem
o seu tempo entre tiros. O melhor resultado fica no placar de LED como RECORDE DA TURMA. Só placar:
não dá CACOS.

Segredo (``parafuso``): 5 ATACAR seguidos no exoesqueleto e ele dá dois passos sozinho... e desmonta.
"""
import math
import random

import pygame

from . import casa_art as art, janelas, progress, segredos, theme, weapon_art
from .arena import MAPS_BY_KEY
from .campaign import CoopMatch, _spread
from .casa import Decor
from .data import FREE_GUNS, RARE_WEAPONS
from .matches import Result
from .sotao import _piece

OFICINA_MAP = "oficina_casa"
RECORD_KEY = "estande_recorde"
T = 40
TOP = 3 * T
BACK = pygame.Rect(T, TOP + T, 22 * T, 3 * T)        # a parede de tijolo do fundo
RANGE_X = 14 * T                                     # onde começa o estande (ninguém passa daqui)
RANGE_END = 23 * T
LANE_TOP = TOP + 5 * T
LANE_H = 2 * T
LANES = 4
BAY_W = 90                                           # na frente da raia: quem está aqui atira nela
DOOR = pygame.Rect(240, TOP + 12 * T - 16, 100, 56)  # a porta de volta para a Casa (parede de baixo)
RACK = pygame.Rect(300, TOP + T + 10, 208, 100)      # o suporte de armas na parede
EXO_AT = (370, TOP + 6 * T + 20)                     # o cavalete do exoesqueleto (pé no chão)
REACH = 60

COUNT = 3 * 60                                       # 3, 2, 1
RUN = 30 * 60                                        # o desafio
SHOW = 4 * 60                                        # o resultado na tela antes de liberar
MISS = 50
FLY = 22                                             # quadros: reação até aqui é NA MOSCA!
EXO_POKES = 5
EXO_WALK = 50

# o suporte de armas: (chave, capítulo que libera). 0 = sempre liberada.
RACK_GUNS = (("revolver", 0), ("colmeia", 1), ("lanterna", 1), ("rifle_plasma", 2), ("canhao", 2),
             ("pistola_agua", 3), ("besta", 3), ("cajado_raio", 4))


def gun_stats(key):
    if key == "revolver":
        return next(g for g in FREE_GUNS if g.name == "Revólver do Xerife")
    return RARE_WEAPONS[key]


def gun_ready(key, chapter):
    from . import computador
    return chapter == 0 or computador.freed() or progress.chapter_cleared(chapter)


def gun_cooldown(key):
    """Quadros entre um tiro e outro no estande (a arma rápida atira mais, mas erra mais)."""
    return max(10, min(40, gun_stats(key).cooldown))


def record():
    """O recorde salvo: {"pontos", "quem", "slot", "arma"} ou None."""
    data = progress.load().get(RECORD_KEY)
    if isinstance(data, dict) and isinstance(data.get("pontos"), int):
        return data
    return None


def save_record(points, who, slot, gun):
    old = record()
    if old is not None and old["pontos"] >= points:
        return False
    data = progress.load()
    data[RECORD_KEY] = {"pontos": int(points), "quem": who, "slot": int(slot), "arma": gun}
    progress.save(data)
    return True


def lane_rect(k):
    return pygame.Rect(RANGE_X, LANE_TOP + k * LANE_H, RANGE_END - RANGE_X, LANE_H)


def lane_of(f):
    """A raia em que ``f`` está de frente (na baia), ou None."""
    if not f.alive_in_match or not (RANGE_X - BAY_W <= f.x < RANGE_X):
        return None
    k = int((f.y - LANE_TOP) // LANE_H)
    return k if 0 <= k < LANES else None


class Target:
    """Um alvo na raia: deitado (esperando) ou de pé (vale ponto) por pouco tempo."""

    def __init__(self, lane, rng):
        self.lane = lane
        self.rng = rng
        self.up = False
        self.age = 0
        self.life = 0
        self.timer = rng.randint(20, 90)
        self.x = RANGE_X + 200
        self.flash = 0

    def update(self, progress_):
        if self.flash > 0:
            self.flash -= 1
        self.timer -= 1
        if self.up:
            self.age += 1
            if self.timer <= 0:
                self.drop()
        elif self.timer <= 0:
            self.up = True
            self.age = 0
            self.x = self.rng.randint(RANGE_X + 90, RANGE_END - 40)
            self.life = max(36, round(100 - 50 * progress_))          # fica de pé menos no fim
            self.timer = self.life

    def drop(self):
        self.up = False
        self.timer = self.rng.randint(25, 80)

    def points(self):
        """Quanto vale acertar agora (e se foi NA MOSCA!)."""
        quick = max(0.0, 1 - self.age / self.life)
        far = (self.x - RANGE_X) / (RANGE_END - RANGE_X)
        pts = 100 + round(200 * quick) + round(100 * far)
        fly = self.age <= FLY
        return (pts + 100 if fly else pts), fly


class Challenge:
    """O DESAFIO DE 30 S: contagem, os 30 segundos e o resultado."""

    def __init__(self, players, seed=None):
        self.players = list(players)
        self.score = {p: 0 for p in self.players}
        self.hits = {p: 0 for p in self.players}
        self.state = "count"
        self.timer = COUNT
        self.rng = random.Random(seed)
        self.targets = [Target(k, self.rng) for k in range(LANES)]
        self.cool = {}
        self.tracers = []                                # [x0, y, x1, quadros, cor]
        self.new_record = False

    @property
    def running(self):
        return self.state == "run"

    @property
    def left(self):
        return self.timer if self.state == "run" else 0

    def update(self, match):
        self.timer -= 1
        for t in self.tracers:
            t[3] -= 1
        self.tracers = [t for t in self.tracers if t[3] > 0]
        for p in list(self.cool):
            self.cool[p] -= 1
            if self.cool[p] <= 0:
                del self.cool[p]
        if self.state == "count":
            if self.timer % 60 == 0 and self.timer > 0:
                match.assets.play("bip", 0.4)
            if self.timer <= 0:
                self.state, self.timer = "run", RUN
                match.assets.play("apito", 0.5)
        elif self.state == "run":
            done = 1 - self.timer / RUN
            for t in self.targets:
                t.update(done)
            if self.timer <= 0:
                self.finish(match)
        elif self.state == "end" and self.timer <= 0:
            return False
        return True

    def finish(self, match):
        self.state, self.timer = "end", SHOW
        for t in self.targets:
            t.up = False
        best = max(self.players, key=lambda p: self.score[p], default=None)
        if best is not None and self.score[best] > 0:
            gun = gun_stats(match.gun_of(best)).name.upper()
            self.new_record = save_record(self.score[best], best.stats.name.upper(), best.slot, gun)
        if self.new_record:
            match._set_banner("RECORDE NOVO!", f"P{best.slot} · {self.score[best]} PONTOS", theme.BRASS)
            match.assets.play("torcida", 0.5)
        else:
            match.assets.play("apito_longo", 0.5)

    def shoot(self, match, f):
        """ATACAR na baia durante o desafio."""
        lane = lane_of(f)
        if not self.running or lane is None or f not in self.score or f in self.cool:
            return False
        self.cool[f] = gun_cooldown(match.gun_of(f))
        t = self.targets[lane]
        y = lane_rect(lane).centery
        color = f.color
        match.assets.play("shoot", 0.35)
        if t.up:
            pts, fly = t.points()
            self.score[f] += pts
            self.hits[f] += 1
            self.tracers.append([RANGE_X, y - 10, t.x, 8, color])
            t.flash = 14
            t.drop()
            match.popup(t.x, y - 60, f"+{pts}" + ("  NA MOSCA!" if fly else ""), theme.BRASS if fly else color)
            match.assets.play("hit", 0.4)
        else:
            self.score[f] = max(0, self.score[f] - MISS)
            self.tracers.append([RANGE_X, y - 10, RANGE_END, 6, (150, 150, 160)])
            match.popup(RANGE_X + 80, y - 50, f"-{MISS}", (200, 120, 120))
        return True


class OficinaMatch(janelas.Janelas, CoopMatch):
    """A oficina. ``story`` e ``walk`` só passam adiante para a Casa na volta."""

    lobby = True
    music = "garagem"
    walk = False
    hud_title = "OFICINA DO BORBA JR"

    def __init__(self, game, run, story=False, walk=False):
        self.story = story
        self.walk = walk
        cfg = MAPS_BY_KEY[OFICINA_MAP]
        starts = _spread(cfg.markers["S"], len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (1.0, 0.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()
        self.going_back = False
        self.challenge = None
        self.guns = {}                                   # jogador -> chave da arma do estande
        self.exo_pokes = 0
        self.exo_last = -999
        self.exo_walk = 0                                # quadros andando (o segredo)
        self.exo_broken = False
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
        draw_range(floor)
        draw_door(floor, DOOR)
        self.arena.walls.append(Wall(BACK.x, BACK.y, BACK.w, BACK.h - 16, visible=False))
        self.arena.walls.append(Wall(RANGE_X, TOP + 4 * T, RANGE_END - RANGE_X, 9 * T, visible=False))
        for k in range(LANES):                          # o balcão de cada baia
            self._put(_piece("oficina_baia", shadow=False), RANGE_X + 4, lane_rect(k).bottom - 4)
        self._put(_piece("oficina_bancada"), 166, TOP + 6 * T, 180)
        self._put(_piece("oficina_extintor"), 58, TOP + 6 * T, 16)
        self._put(_piece("oficina_pneus"), 74, TOP + 12 * T - 6, 44)
        self._put(_piece("oficina_tambor"), 130, TOP + 12 * T - 6, 28)
        self._put(_piece("oficina_compressor"), 410, TOP + 12 * T - 6, 48)
        self._put(_piece("oficina_suporte_exo"), *EXO_AT, 52)
        sheet = self.assets.sprites.get("borba_exo")
        self.exo_frames = []
        if sheet is not None:
            for i in range(4):
                img = sheet.pose("frente", "andar", i * 2).copy()
                img.fill((0, 0, 0, 0), (0, 0, img.get_width(), 26))     # sem ninguém dentro: só a armadura
                self.exo_frames.append(art.Baked(img, -img.get_width() // 2, -img.get_height()))
        self.exo = None
        if self.exo_frames:
            self.exo = Decor(EXO_AT[0], EXO_AT[1] - 6, self.exo_frames[0], foot_y=EXO_AT[1] + 1)
            self.props.append(self.exo)

    # ── consultas ────────────────────────────
    @property
    def objective_text(self):
        return "OFICINA · ATACAR NUMA BAIA: DESAFIO DE 30 S"

    def objective(self):
        return None

    def gun_of(self, f):
        return self.guns.get(f, RACK_GUNS[0][0])

    def door_near(self, f):
        return f.alive_in_match and DOOR.inflate(30, 40).collidepoint(f.x, f.y)

    def rack_near(self, f):
        return f.alive_in_match and RACK.left - 10 <= f.x <= RACK.right + 10 and f.y < BACK.bottom + 70

    def exo_near(self, f):
        x, y = EXO_AT
        return f.alive_in_match and self.exo is not None and math.hypot(f.x - x, f.y - y) < REACH

    def bay_players(self):
        return [p for p in self.alive_players if lane_of(p) is not None]

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            self._set_banner("OFICINA DO BORBA JR", "ESTANDE DE TIRO", (240, 170, 60))
        if self.banner and self.banner[3] > 130:
            self.banner = None
        if self.challenge is not None and not self.challenge.update(self):
            self.challenge = None
        self._update_exo()
        self.update_windows()

    def interact(self, f):
        if self.door_near(f):
            if self.leaving_in:
                return True
            self.going_back = True
            self.assets.play("select", 0.45)
            self.leave_soon(self.leave)
            return True
        if lane_of(f) is not None:
            if self.challenge is None:
                self.start_challenge()
            elif self.challenge.running:
                self.challenge.shoot(self, f)
            return True
        if self.rack_near(f):
            self.next_gun(f)
            return True
        if self.exo_near(f):
            self.poke_exo(f)
            return True
        return self.pick_ground(f)

    def start_challenge(self, seed=None):
        who = self.bay_players()
        if not who:
            return None
        self.challenge = Challenge(who, seed)
        self.assets.play("confirm", 0.45)
        return self.challenge

    def next_gun(self, f):
        """Troca a arma do estande de ``f`` pela próxima liberada do suporte."""
        keys = [k for k, ch in RACK_GUNS if gun_ready(k, ch)]
        now = self.gun_of(f)
        i = keys.index(now) if now in keys else -1
        key = keys[(i + 1) % len(keys)]
        self.guns[f] = key
        self.popup(f.x, f.y - 70, gun_stats(key).name.upper(), f.color)
        self.assets.play("click", 0.4)

    def poke_exo(self, f):
        if self.exo_broken or self.exo_walk:
            return
        self.exo_pokes = self.exo_pokes + 1 if self.frame - self.exo_last < 60 else 1
        self.exo_last = self.frame
        self.exo.wobble = 14
        self.assets.play("soco_metal", 0.3)
        if self.exo_pokes >= EXO_POKES:
            self.exo_walk = EXO_WALK
            self.exo_pokes = 0

    def _update_exo(self):
        if not self.exo_walk:
            return
        self.exo_walk -= 1
        step = EXO_WALK - self.exo_walk
        self.exo.y = EXO_AT[1] - 6 + step * 0.9                       # desce do cavalete andando
        self.exo.foot_y = self.exo.y + 7
        self.exo.baked = self.exo_frames[(step // 6) % len(self.exo_frames)]
        if step % 12 == 0:
            self.assets.play("passo_pesado", 0.3)
        if self.exo_walk == 0:
            self.break_exo()

    def break_exo(self):
        """Dois passos e... desmonta no chão."""
        self.exo_broken = True
        img = pygame.transform.rotate(self.exo_frames[0].image, 90)
        self.exo.baked = art.Baked(img, -img.get_width() // 2, -img.get_height())
        x, y = self.exo.x, self.exo.y
        self.burst(x, y - 20, (170, 174, 186), 26, speed=4)
        self.camera.shake(5)
        self.assets.play("explosion", 0.35)
        self.popup(x, y - 90, "FALTOU PARAFUSO...", (255, 230, 160))
        segredos.find("parafuso", self, x, y - 120)

    def _finish(self, won):
        self.won = won
        self.result = Result("OFICINA", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.campaign import hub_scene
        from .scenes.escada import StairsTripScene
        return StairsTripScene(self.game, lambda: hub_scene(self.game, self.run, story=self.story, walk=self.walk,
                                                            arrive="oficina"), "VOLTANDO PARA A CASA", door=True)

    def restart_scene(self):
        from .scenes.campaign import oficina_scene
        return oficina_scene(self.game, self.run, story=self.story, walk=self.walk)

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        self._draw_rack(screen, ui, cam)
        self._draw_board(screen, ui, cam)
        self._draw_targets(screen, cam)
        free = [p for p in self.alive_players if p not in self.menus]
        blink = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
        if any(self.door_near(p) for p in free):
            sx, sy = cam.to_screen(DOOR.centerx, DOOR.y - 40)
            ui.text(screen, "ATACAR: VOLTAR PARA A CASA", theme.XS, blink, (round(sx), round(sy)))
        if any(self.rack_near(p) for p in free):
            sx, sy = cam.to_screen(RACK.centerx, RACK.bottom + 12)
            ui.text(screen, "ATACAR: TROCAR A ARMA DO ESTANDE", theme.XS, blink, (round(sx), round(sy)))
        if self.challenge is None and any(lane_of(p) is not None for p in free):
            sx, sy = cam.to_screen(RANGE_X - 46, LANE_TOP - 16)
            ui.text(screen, "ATACAR: COMEÇAR O DESAFIO", theme.XS, blink, (round(sx), round(sy)))
        for p in self.alive_players:                     # a arma de cada um, quando está na baia
            if lane_of(p) is not None:
                icon = weapon_art.icon(gun_stats(self.gun_of(p)).name)
                if icon is not None:
                    sx, sy = cam.to_screen(p.x + 22, p.y - 24)
                    screen.blit(icon, icon.get_rect(center=(round(sx), round(sy))))
        self._draw_challenge(screen, ui)
        self.draw_ground(screen, cam, ui)
        janelas.draw(self, screen, ui)

    def _draw_rack(self, screen, ui, cam):
        for i, (key, chapter) in enumerate(RACK_GUNS):
            sx, sy = cam.to_screen(RACK.x + 26 + (i % 4) * 52, RACK.y + 26 + (i // 4) * 48)
            c = (round(sx), round(sy))
            if gun_ready(key, chapter):
                icon = weapon_art.icon2x(gun_stats(key).name) or weapon_art.icon(gun_stats(key).name)
                if icon is not None:
                    screen.blit(icon, icon.get_rect(center=c))
            else:
                pygame.draw.rect(screen, (60, 44, 30), (c[0] - 16, c[1] - 14, 32, 28))
                screen.fill((210, 170, 60), (c[0] - 6, c[1] - 2, 12, 10))
                screen.fill((150, 110, 30), (c[0] - 1, c[1] + 2, 2, 3))
                pygame.draw.arc(screen, (190, 190, 200), (c[0] - 6, c[1] - 10, 12, 14), 0, math.pi, 2)

    def _draw_board(self, screen, ui, cam):
        """O placar de LED do recorde, em cima das raias."""
        sx, sy = cam.to_screen(RANGE_X + 30, BACK.y + 30)
        box = pygame.Rect(round(sx), round(sy), 280, 50)
        pygame.draw.rect(screen, (12, 10, 14), box.inflate(6, 6))
        pygame.draw.rect(screen, (16, 14, 20), box)
        pygame.draw.rect(screen, (255, 90, 90), box, 2)
        rec = record()
        if rec is None:
            ui.text(screen, "RECORDE DA TURMA  ---", theme.XS, (255, 120, 120), (box.centerx, box.y + 16), shadow=False)
            ui.text(screen, "NINGUÉM ATIROU AINDA", theme.XS, (200, 180, 190), (box.centerx, box.y + 34), shadow=False)
        else:
            ui.text(screen, f"RECORDE DA TURMA  {rec['pontos']}", theme.XS, (255, 120, 120),
                    (box.centerx, box.y + 16), shadow=False)
            ui.text(screen, f"P{rec['slot']} · {rec['quem']} · {rec['arma']}"[:34], theme.XS, (200, 180, 190),
                    (box.centerx, box.y + 34), shadow=False)

    def _draw_targets(self, screen, cam):
        up_img = _piece("oficina_alvo", shadow=False).image
        hit_img = _piece("oficina_alvo_acertado", shadow=False).image
        targets = self.challenge.targets if self.challenge is not None else []
        for k in range(LANES):
            r = lane_rect(k)
            t = targets[k] if targets else None
            if t is not None and (t.up or t.flash):
                img = hit_img if t.flash else up_img
                sx, sy = cam.to_screen(t.x, r.bottom - 10)
                screen.blit(img, img.get_rect(midbottom=(round(sx), round(sy))))
        if self.challenge is not None:
            for x0, y, x1, _, color in self.challenge.tracers:
                a = cam.to_screen(x0, y)
                b = cam.to_screen(x1, y - 6)
                pygame.draw.line(screen, color, (round(a[0]), round(a[1])), (round(b[0]), round(b[1])), 2)

    def _draw_challenge(self, screen, ui):
        ch = self.challenge
        if ch is None:
            return
        from . import config
        rect = pygame.Rect(12, 60, 250, 40 + 18 * len(ch.players) + 26)
        pygame.draw.rect(screen, theme.SHADOW, rect.move(3, 3))
        ui.panel(screen, rect, fill=theme.INK_2, accent=(255, 120, 120))
        ui.text(screen, "DESAFIO DE 30 S", theme.XS, (255, 120, 120), (rect.centerx, rect.y + 14))
        for i, p in enumerate(sorted(ch.players, key=lambda q: q.slot)):
            y = rect.y + 34 + i * 18
            screen.fill(p.color, (rect.x + 12, y - 4, 8, 8))
            ui.text(screen, f"P{p.slot} {p.stats.name.upper()}"[:16], theme.XS, theme.BONE, (rect.x + 26, y),
                    anchor="midleft", shadow=False)
            ui.text(screen, str(ch.score[p]), theme.XS, theme.BRASS, (rect.right - 12, y), anchor="midright",
                    shadow=False)
        bottom = rect.bottom - 14
        if ch.state == "count":
            ui.text(screen, f"PREPARA... {-(-ch.timer // 60)}", theme.XS, (255, 200, 200), (rect.centerx, bottom))
        elif ch.state == "run":
            bar = pygame.Rect(rect.x + 12, bottom - 4, rect.w - 24, 8)
            screen.fill((60, 50, 60), bar)
            screen.fill((255, 120, 120), (bar.x, bar.y, round(bar.w * ch.timer / RUN), bar.h))
        else:
            ui.text(screen, "RECORDE NOVO!" if ch.new_record else "FIM!", theme.XS, theme.BRASS, (rect.centerx, bottom))


def draw_backdrop(s, ui=None):
    """A parede de tijolo com o letreiro, o painel de ferramentas, o suporte de armas e as latas."""
    from . import pecas
    r = BACK
    s.fill((150, 80, 60), r)
    for y in range(r.y, r.bottom, 12):
        s.fill((120, 62, 48), (r.x, y, r.w, 1))
        off = 0 if ((y - r.y) // 12) % 2 else 14
        for x in range(r.x + off, r.right, 28):
            s.fill((120, 62, 48), (x, y, 1, 12))
    s.fill((150, 150, 160), (r.x, r.y + 6, RANGE_X - r.x - 10, 4))               # o cano
    s.fill((70, 70, 78), (r.x, r.bottom - 10, r.w, 10))
    s.fill((110, 110, 120), (r.x, r.bottom - 10, r.w, 2))
    # o letreiro de neon
    sign = pygame.Rect(r.x + 16, r.y + 14, 236, 28)
    glow = pygame.Surface((sign.w + 80, sign.h + 60), pygame.SRCALPHA)
    for k in range(6):
        pygame.draw.ellipse(glow, (240, 170, 60, 10), glow.get_rect().inflate(-k * 12, -k * 8))
    s.blit(glow, (sign.x - 40, sign.y - 30))
    pygame.draw.rect(s, (30, 26, 30), sign)
    pygame.draw.rect(s, (240, 170, 60), sign, 2)
    if ui is not None:
        ui.text(s, "OFICINA DO BORBA JR", theme.XS, (240, 170, 60), sign.center, shadow=False)
    # o painel de ferramentas (pegboard)
    board = pygame.Rect(r.x + 16, r.y + 50, 236, 56)
    s.fill((160, 120, 80), board)
    for yy in range(board.y + 5, board.bottom - 2, 8):
        for xx in range(board.x + 5, board.right - 2, 8):
            s.fill((120, 86, 56), (xx, yy, 2, 2))
    tools = ((200, 40, 40), (120, 80, 50), (240, 200, 40), (60, 140, 220), (180, 184, 196), (200, 60, 60))
    for i, c in enumerate(tools):
        x = board.x + 16 + i * 38
        s.fill(c, (x, board.y + 8, 5, 30))
        s.fill((180, 184, 196), (x - 3, board.y + 6, 11, 5))
    pygame.draw.circle(s, (60, 60, 66), (board.right - 18, board.y + 28), 14)
    pygame.draw.circle(s, (160, 120, 80), (board.right - 18, board.y + 28), 6)
    rack = pecas.image("oficina_suporte_armas")
    if rack is not None:
        s.blit(rack, RACK.topleft)


def draw_range(s):
    """O estande: parede escura com espuma, o chão das raias, os trilhos e as faixas de aviso."""
    top = BACK.y
    s.fill((40, 40, 46), (RANGE_X - 6, top, RANGE_END - RANGE_X + 6, TOP + 13 * T - top))
    s.fill((52, 54, 60), (RANGE_X, top + 4, RANGE_END - RANGE_X, BACK.h - 8))
    for y in range(top + 70, top + BACK.h - 8, 14):                              # espuma acústica
        for x in range(RANGE_X + 4, RANGE_END - 4, 14):
            pygame.draw.polygon(s, (60, 62, 70), [(x, y + 12), (x + 6, y), (x + 12, y + 12)])
    s.fill((46, 46, 52), (RANGE_X, TOP + 4 * T, RANGE_END - RANGE_X, T))
    for k in range(LANES):
        lr = lane_rect(k)
        s.fill((58, 58, 64) if k % 2 else (52, 52, 58), lr)
        s.fill((150, 150, 160), (lr.x + 10, lr.bottom - 12, lr.w - 20, 2))       # trilho
        s.fill((110, 110, 120), (lr.x + 10, lr.bottom - 10, lr.w - 20, 1))
        s.fill((30, 30, 34), (lr.x, lr.y, lr.w, 2))
        pygame.draw.circle(s, (255, 240, 200), (RANGE_END - 16, lr.y + 14), 3)   # a luzinha da raia
    for y in range(LANE_TOP, LANE_TOP + LANES * LANE_H, 20):                     # faixa de aviso no chão
        pygame.draw.polygon(s, (236, 196, 60), [(RANGE_X - 14, y), (RANGE_X - 4, y), (RANGE_X - 4, y + 10), (RANGE_X - 14, y + 10)])
        pygame.draw.polygon(s, (30, 30, 34), [(RANGE_X - 14, y + 10), (RANGE_X - 4, y + 10), (RANGE_X - 4, y + 20), (RANGE_X - 14, y + 20)])
    for k in range(LANES):                                                       # o número de cada baia
        lr = lane_rect(k)
        pygame.draw.rect(s, (236, 196, 60), (RANGE_X - BAY_W, lr.y + 4, BAY_W - 18, lr.h - 8), 1)


def draw_door(s, rect):
    """A porta de volta para a Casa na parede de baixo: o batente, a folha aberta, a luz do
    corredor entrando e o capacho."""
    s.fill((60, 40, 24), rect.inflate(12, 4))
    s.fill((36, 26, 20), rect)
    for k in range(6):                                                   # a luz do corredor no chão
        c = (120 + k * 18, 96 + k * 14, 60 + k * 8)
        s.fill(c, (rect.x + 10 + k * 3, rect.y + 6 + k * 6, rect.w - 20 - k * 6, 6))
    s.fill((150, 104, 64), (rect.x - 6, rect.y, 6, rect.h))              # batente
    s.fill((150, 104, 64), (rect.right, rect.y, 6, rect.h))
    s.fill((122, 82, 50), (rect.right - 2, rect.y + 2, 18, rect.h - 4))  # a folha aberta encostada
    s.fill((96, 64, 40), (rect.right + 4, rect.y + 8, 8, rect.h - 16))
    mat = pygame.Rect(rect.x + 12, rect.y - 16, rect.w - 24, 14)         # o capacho
    s.fill((120, 60, 40), mat)
    for x in range(mat.x + 2, mat.right - 2, 4):
        s.fill((96, 46, 30), (x, mat.y + 2, 2, mat.h - 4))


__all__ = ("OficinaMatch", "OFICINA_MAP", "Challenge", "lane_of", "record")
