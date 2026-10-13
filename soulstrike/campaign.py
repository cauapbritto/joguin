"""Modo campanha: 3 fases cooperativas (1 a 4 jogadores) contra criaturas e almas corrompidas.

CampaignRun guarda o que passa de uma fase para a outra (melhorias, vida, continues, tempo).
CampaignMatch é uma fase: ondas de inimigos que saem de portais, até a fase acabar.
"""
import copy
import math
import random
from dataclasses import dataclass

import pygame

from . import config, hud, theme
from .ai import FighterAI
from .entities import Pickup
from .enemies import CREATURES, SHADOW_AURA, Portal, spawn_enemy
from .matches import Match, Result, _separate
from .upgrades import apply_all

PLAYERS, ENEMIES = 0, 1
CONTINUES = 3
PHASE_HEAL = 0.35             # entre uma fase e outra, recupera esse tanto da vida
REVIVE_FRAMES = 120           # tempo perto de um companheiro caído para levantá-lo
REVIVE_RADIUS = 56
REVIVE_HP = 0.4
CONTINUE_HP = 0.5
LEASH_X, LEASH_Y = 1150, 500  # quão longe os jogadores podem ficar uns dos outros (cabe na câmera)
INTRO_FRAMES = 150
BETWEEN_FRAMES = 110
CLEAR_FRAMES = 200
DOWN_FRAMES = 150
GAMEOVER_FRAMES = 220
CORPSE_FRAMES = 70
SOLO_DAMAGE = 0.85

# dificuldade da campanha: (vida dos inimigos, dano dos inimigos)
DIFFICULTY = {"facil": (0.75, 0.7), "normal": (1.0, 1.0), "dificil": (1.3, 1.25)}


@dataclass(frozen=True)
class Phase:
    key: str
    map_key: str
    name: str
    starts: tuple             # onde cada jogador começa
    facing: tuple
    waves: tuple              # cada onda: ((tipo, quantidade), ...)
    boss_spot: tuple = None


PHASES = (
    Phase("floresta", "floresta", "FLORESTA SOMBRIA",
          ((200, 640), (200, 760), (290, 640), (290, 760)), (1.0, 0.0),
          ((("diabrete", 5),),
           (("diabrete", 4), ("esqueleto", 2)),
           (("sombra:velocista", 1), ("diabrete", 3)))),
    Phase("calabouco", "calabouco", "CALABOUÇO DAS ALMAS",
          ((110, 540), (110, 660), (170, 540), (170, 660)), (1.0, 0.0),
          ((("esqueleto", 3), ("diabrete", 3)),
           (("golem", 1), ("esqueleto", 2), ("diabrete", 2)),
           (("sombra:tanque", 1), ("sombra:ninja", 1), ("diabrete", 2)))),
    Phase("templo", "templo_gelado", "TEMPLO GELADO",
          ((740, 1090), (860, 1090), (680, 1100), (920, 1100)), (0.0, -1.0),
          ((("diabrete", 4), ("esqueleto", 2), ("golem", 1)),
           (("chefe", 1),)),
          boss_spot=(800, 330)),
)


def is_elite(kind):
    return kind == "chefe" or kind.startswith("sombra:") or CREATURES[kind].elite


def scaled_count(kind, base, players):
    """Mais jogadores, mais inimigos: +50% dos comuns por jogador a mais (os fortes ganham vida)."""
    if is_elite(kind):
        return base
    return max(1, round(base * (1 + 0.5 * (players - 1))))


def elite_hp_scale(kind, players):
    if kind == "chefe":
        return 1 + 0.6 * (players - 1)
    return 1 + 0.35 * (players - 1) if is_elite(kind) else 1.0


class CampaignRun:
    """O que vale para a campanha inteira, de uma fase para a outra."""

    def __init__(self, session):
        self.session = session
        self.slots = [s.slot for s in session.slots]
        self.phase_index = 0
        self.continues = CONTINUES
        self.upgrades = {s: [] for s in self.slots}
        self.hp_ratio = {s: 1.0 for s in self.slots}
        self.kills = {s: 0 for s in self.slots}
        self.damage = {s: 0 for s in self.slots}
        self.frames = 0
        self._snapshot = None

    @property
    def phase(self):
        return PHASES[self.phase_index]

    @property
    def players(self):
        return len(self.slots)

    @property
    def last_phase(self):
        return self.phase_index == len(PHASES) - 1

    def _state(self):
        return {k: copy.deepcopy(getattr(self, k))
                for k in ("phase_index", "continues", "upgrades", "hp_ratio", "kills", "damage", "frames")}

    def begin_phase(self):
        """Guarda como tudo estava no começo da fase (para TENTAR DE NOVO)."""
        self._snapshot = self._state()

    def retry_phase(self):
        if self._snapshot is not None:
            for k, v in copy.deepcopy(self._snapshot).items():
                setattr(self, k, v)
        self.continues = max(self.continues, 1)
        self.hp_ratio = {s: max(r, 0.6) for s, r in self.hp_ratio.items()}

    def prepare(self, fighter):
        """Aplica as melhorias e a vida que sobrou da fase anterior."""
        apply_all(fighter, self.upgrades.get(fighter.slot, ()))
        fighter.hp = max(1, round(fighter.max_hp * self.hp_ratio.get(fighter.slot, 1.0)))

    def finish_phase(self, match):
        for f in match.players:
            ratio = f.hp / f.max_hp if f.hp > 0 else 0.0
            self.hp_ratio[f.slot] = min(1.0, ratio + PHASE_HEAL)
            self.kills[f.slot] += f.kills
            self.damage[f.slot] += f.damage_dealt
        self.frames += match.frame

    def add_upgrade(self, slot, key):
        self.upgrades[slot].append(key)

    def advance(self):
        self.phase_index += 1


class _Point:
    """Alvo imaginário à frente do jogador (atirar sem inimigo por perto)."""

    def __init__(self, x, y):
        self.x, self.y = x, y


class CampaignMatch(Match):
    min_zoom = 0.6

    def __init__(self, game, run):
        self.run = run
        self.phase = run.phase
        super().__init__(game, run.session, self.phase.map_key)
        self.enemy_hp, self.enemy_dmg = DIFFICULTY.get(run.session.difficulty, (1.0, 1.0))
        if run.players == 1:
            self.enemy_dmg *= SOLO_DAMAGE         # sozinho não tem quem levante: inimigos batem menos
        for setup, pos in zip(run.session.slots, self.phase.starts):
            f = self._add_fighter(setup, pos, team=PLAYERS)
            f.full_name = setup.name
            f.facing = self.phase.facing
            run.prepare(f)
            game.inputs[setup.slot].set_layout("battle")
            self.controllers[f] = game.inputs[setup.slot]
        self.players = list(self.fighters)
        self.enemies = []
        self.portals = []
        self.pickups = []
        self.corpses = {}
        self.revive_progress = {f: 0.0 for f in self.players}
        self.was_down = set()
        self.wave = -1
        self.state = "intro"
        self.state_timer = INTRO_FRAMES
        self.banner = None              # (título, subtítulo, cor, idade)
        self.wave_banner = 0
        self.boss = None
        self.slain_boss = False
        self.won = False
        self._last_pause = -99

    def hit_feedback(self, target, amount):
        """Com muita gente batendo ao mesmo tempo, pausar a cada tiro travaria o jogo:
        a pausa fica para quando um jogador apanha ou um inimigo cai (e não mais que uma por vez)."""
        if target.team == PLAYERS:
            self.camera.shake(4 if amount < 20 else 7)
            pause = 2 if amount < 20 else 4
        else:
            if amount >= 20:
                self.camera.shake(2)
            pause = 3 if target.hp <= 0 else 0
        if pause and self.frame - self._last_pause > 12:
            self._last_pause = self.frame
            self.hit_pause(pause)

    # ── consultas ────────────────────────────
    @property
    def alive_players(self):
        return [p for p in self.players if p.alive_in_match]

    @property
    def alive_enemies(self):
        return [e for e in self.enemies if e.alive_in_match]

    @property
    def elapsed(self):
        return self.run.frames + self.frame

    def nearest_player(self, me):
        alive = self.alive_players
        return min(alive, key=me.distance_to) if alive else None

    def aim_target(self, f):
        """Inimigo que o jogador quer acertar: o mais perto na direção em que ele aponta."""
        reach = 220 if f.weapon.is_melee else 600
        fx, fy = f.input if math.hypot(*f.input) > 0.3 else f.facing
        mag = math.hypot(fx, fy) or 1
        fx, fy = fx / mag, fy / mag
        best, best_score = None, 1e9
        for e in self.alive_enemies:
            dx, dy = e.x - f.x, e.y - f.y
            d = math.hypot(dx, dy)
            if d > reach + e.radius:
                continue
            dot = (dx * fx + dy * fy) / (d or 1)
            score = d * (1.6 - dot)
            if score < best_score:
                best, best_score = e, score
        return best

    def focus_points(self):
        return [(p.x, p.y - 20) for p in self.players]

    def world_entities(self):
        return self.fighters + self.pickups

    # ── ciclo ────────────────────────────────
    def step(self):
        if self.state_timer > 0:
            self.state_timer -= 1
        locked = self.state in ("clear", "gameover") or (self.state == "intro" and self.state_timer > INTRO_FRAMES - 40)
        for f, ctrl in list(self.controllers.items()):
            if not f.alive_in_match or locked or f.stunned:
                f.steer(0, 0)
            elif f.team == PLAYERS:
                self._human(f, ctrl)
            elif isinstance(ctrl, FighterAI):
                target = self.nearest_player(f)
                if target is None:
                    f.steer(0, 0)
                else:
                    ctrl.update(f, target, self)
            else:
                ctrl.update(f, self)
            f.update(self)
        self._separate_bodies()
        self._leash()
        self._update_bullets()
        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]
        self._update_portals()
        self._update_pickups()
        self._update_corpses()
        self._update_downed()
        self._update_state()
        if self.wave_banner > 0:
            self.wave_banner -= 1
        if self.banner:
            t, s, c, age = self.banner
            self.banner = (t, s, c, age + 1)

    def _human(self, f, inp):
        f.steer(*inp.axis())
        target = self.aim_target(f)
        if target is None:
            fx, fy = f.facing
            target = _Point(f.x + fx * 260, f.y + fy * 260)
        if inp.held("attack"):
            f.attack(self, target)
        if inp.pressed("special"):
            f.use_ability(self, target)
        if inp.pressed("switch") and f.switch_weapon():
            self.assets.play("click", 0.4)
        direction = None
        if inp.pressed("dodge"):
            direction = f.input if any(f.input) else f.facing
        elif inp.double_tap:
            direction = inp.double_tap
        if direction and f.dash(direction):
            self.assets.play("dash", 0.3)

    def _separate_bodies(self):
        bodies = [f for f in self.fighters if f.alive_in_match and f.lift <= 0]
        for i, a in enumerate(bodies):
            for b in bodies[i + 1:]:
                _separate(a, b)
        for f in bodies:
            self.arena.resolve(f)

    def _leash(self):
        """Ninguém se afasta demais do grupo: todos cabem na câmera."""
        if len(self.players) < 2:
            return
        for p in self.alive_players:
            others = [q for q in self.players if q is not p]
            min_x, max_x = min(q.x for q in others), max(q.x for q in others)
            min_y, max_y = min(q.y for q in others), max(q.y for q in others)
            x = min(max(p.x, max_x - LEASH_X), min_x + LEASH_X)
            y = min(max(p.y, max_y - LEASH_Y), min_y + LEASH_Y)
            if (x, y) != (p.x, p.y):
                p.x, p.y = x, y
                self.arena.resolve(p)

    # ── ondas e inimigos ─────────────────────
    def _start_wave(self, index):
        self.wave = index
        self.wave_banner = 100
        delay = 0
        for kind, count in self.phase.waves[index]:
            for _ in range(scaled_count(kind, count, len(self.players))):
                x, y = self._spawn_spot(kind)
                self.portals.append(Portal(x, y, kind, delay))
                delay += 14
        self.assets.play("ability", 0.4)

    def _spawn_spot(self, kind):
        if kind == "chefe" and self.phase.boss_spot:
            return self.phase.boss_spot
        radius = 30 if kind in ("golem", "chefe") else config.PLAYER_RADIUS + 6
        players = self.alive_players or self.players
        best, best_score = None, -1
        for attempt in range(90):
            x, y = self.arena.random_free_spot(radius)
            near = min(math.hypot(p.x - x, p.y - y) for p in players)
            crowd = min([math.hypot(q.x - x, q.y - y) for q in self.portals] or [999])
            if 380 <= near <= 950 and crowd > 70:
                return x, y
            score = min(near, 600) + min(crowd, 70)
            if score > best_score:
                best, best_score = (x, y), score
        return best

    def summon(self, kinds, near):
        """Chamado pelo chefão: portais abrem em volta dele."""
        players = len(self.players)
        expanded = []
        for kind in kinds:
            expanded += [kind] * (scaled_count(kind, 1, players) if kind == "diabrete" else 1)
        for i, kind in enumerate(expanded):
            a = i * math.tau / len(expanded) + random.uniform(-0.3, 0.3)
            r = random.uniform(150, 240)
            x, y = self.arena.free_spot(near.x + math.cos(a) * r, near.y + math.sin(a) * r, config.PLAYER_RADIUS + 6)
            self.portals.append(Portal(x, y, kind, i * 10))

    def _update_portals(self):
        still = []
        for portal in self.portals:
            portal.update(self)
            if portal.ready:
                self._spawn(portal.kind, portal.x, portal.y)
            else:
                still.append(portal)
        self.portals = still

    def _spawn(self, kind, x, y):
        if kind == "chefe":
            from .boss import spawn_boss
            enemy, brain = spawn_boss(self, x, y)
            self.boss = enemy
        else:
            enemy, brain = spawn_enemy(self, kind, x, y)
        scale = elite_hp_scale(kind, len(self.players))
        enemy.max_hp = enemy.hp = max(1, round(enemy.max_hp * self.enemy_hp * scale))
        enemy.damage_bonus *= self.enemy_dmg
        target = self.nearest_player(enemy)
        if target is not None:
            enemy.face(target)
        self.fighters.append(enemy)
        self.enemies.append(enemy)
        self.controllers[enemy] = brain
        self.burst(x, y - 10, SHADOW_AURA, 18, speed=4)
        if kind.startswith("sombra:") or kind == "chefe":
            self.popup(x, y - 80, enemy.stats.name.upper(), SHADOW_AURA)
            self.camera.shake(5)

    def _update_corpses(self):
        for e in self.enemies:
            if not e.alive_in_match and e not in self.corpses:
                self.corpses[e] = 0
                self._on_enemy_death(e)
        gone = []
        for e in list(self.corpses):
            self.corpses[e] += 1
            if self.corpses[e] >= CORPSE_FRAMES:
                gone.append(e)
        for e in gone:
            del self.corpses[e]
            self.enemies.remove(e)
            self.fighters.remove(e)
            self.controllers.pop(e, None)
            self.burst(e.x, e.y + 10, (70, 60, 80), 8, speed=2)

    def _on_enemy_death(self, e):
        # a alma presa sobe e se liberta
        for _ in range(10):
            self.particles.append(_soul_particle(e.x, e.y - 20))
        self.assets.play("hit", 0.5)
        if e is self.boss:
            self.slain_boss = True
            self.slowmo = 80
            self.camera.shake(14)
            self.burst(e.x, e.y - 30, SHADOW_AURA, 60, speed=8)
            self.bullets.clear()
            return
        if random.random() < e.stats.drop_chance:
            kind = random.choices(("vida", "furia", "energia"), weights=(55, 25, 20))[0]
            x, y = self.arena.free_spot(e.x, e.y, 14)
            self.pickups.append(Pickup(kind, x, y))

    def _update_pickups(self):
        for item in self.pickups:
            item.update(self)
            if not item.alive:
                continue
            for f in self.alive_players:
                if math.hypot(f.x - item.x, f.y - item.y) < f.radius + item.radius + 6:
                    item.apply(f, self)
                    break
        self.pickups = [p for p in self.pickups if p.alive]

    # ── caídos e continues ───────────────────
    def _update_downed(self):
        for p in self.players:
            if p.alive_in_match:
                self.was_down.discard(p)
                continue
            if p not in self.was_down:
                self.was_down.add(p)
                self.revive_progress[p] = 0.0
                self.popup(p.x, p.y - 60, f"{p.label} CAIU", p.color)
                self.assets.play("gameover", 0.25)
            if self.state not in ("fight", "between", "intro"):
                continue
            helpers = [q for q in self.alive_players if q.distance_to(p) < REVIVE_RADIUS]
            prog = self.revive_progress[p]
            if helpers:
                prog += (1 + 0.5 * (len(helpers) - 1)) / REVIVE_FRAMES
                if self.frame % 6 == 0:
                    self.burst(p.x, p.y, p.color, 1, speed=2)
            else:
                prog = max(0.0, prog - 1 / 240)
            self.revive_progress[p] = prog
            if prog >= 1:
                self._revive(p, REVIVE_HP)
                self.popup(p.x, p.y - 70, "DE PÉ!", theme.MOSS)

    def _revive(self, p, ratio):
        p.hp = max(1, round(p.max_hp * ratio))
        p.invulnerable_timer = 100
        p.stun_timer = 0
        p.vx = p.vy = 0.0
        self.revive_progress[p] = 0.0
        self.was_down.discard(p)
        self.burst(p.x, p.y - 16, p.color, 22, speed=5)
        self.assets.play("select", 0.5)

    def _use_continue(self):
        self.run.continues -= 1
        for p in self.players:
            self._revive(p, CONTINUE_HP)
            p.invulnerable_timer = 150
        # os inimigos perto são empurrados para longe
        for e in self.alive_enemies:
            p = min(self.players, key=e.distance_to)
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy) or 1
            if d < 260:
                e.knock = [dx / d * 12 * (1 - e.knock_resist), dy / d * 12 * (1 - e.knock_resist)]
                e.stun(40)
        self.camera.shake(8)

    # ── estados da fase ──────────────────────
    def _set_banner(self, title, sub=None, color=theme.BRASS):
        self.banner = (title, sub, color, 0)

    def _update_state(self):
        state, timer = self.state, self.state_timer
        if state == "intro":
            if timer == INTRO_FRAMES - 1:
                self._set_banner(f"FASE {self.run.phase_index + 1}", self.phase.name, theme.BRASS)
            if timer == 30:
                self.banner = None
            if timer == 0:
                self._start_wave(0)
                self.state = "fight"
            return
        if state in ("fight", "between") and not self.alive_players:
            self.state, self.state_timer = "down", DOWN_FRAMES
            self._set_banner("TODOS CAÍRAM", None, theme.BLOOD)
            return
        if state == "fight":
            if self.portals or self.alive_enemies:
                return
            if self.wave + 1 < len(self.phase.waves):
                self.state, self.state_timer = "between", BETWEEN_FRAMES
            else:
                self.state, self.state_timer = "clear", CLEAR_FRAMES
                self.bullets.clear()
                self._set_banner("FASE CONCLUÍDA!", self.phase.name, theme.MOSS)
                self.assets.stop_music(1500)
                self.assets.play("victory", 0.5)
        elif state == "between":
            if timer == 0:
                self._start_wave(self.wave + 1)
                self.state = "fight"
        elif state == "down":
            if timer == DOWN_FRAMES // 2 and self.run.continues > 0:
                self._set_banner("CONTINUE", f"RESTAM {self.run.continues - 1}", theme.BRASS)
            if timer == 0:
                if self.run.continues > 0:
                    self._use_continue()
                    self.banner = None
                    self.state = "fight"
                else:
                    self.state, self.state_timer = "gameover", GAMEOVER_FRAMES
                    self._set_banner("FIM DE JOGO", "SEM CONTINUES", theme.BLOOD)
                    self.assets.stop_music(1500)
                    self.assets.play("gameover", 0.5)
        elif state == "clear" and timer == 0:
            self._finish(won=True)
        elif state == "gameover" and timer == 0:
            self._finish(won=False)

    def _finish(self, won):
        self.won = won
        if won:
            self.run.finish_phase(self)
        title = "FASE CONCLUÍDA" if won else "FIM DE JOGO"
        self.result = Result(title, theme.MOSS if won else theme.BLOOD, self.players if won else [])
        self.finished = True

    def next_scene(self):
        from .scenes.campaign import after_phase, game_over
        return after_phase(self.game, self.run) if self.won else game_over(self.game, self.run)

    def restart_scene(self):
        from .scenes.campaign import start_phase
        self.run.retry_phase()
        return start_phase(self.game, self.run, story=False)

    # ── desenho ──────────────────────────────
    def draw_under(self, view, cam):
        for portal in self.portals:
            portal.draw(view, cam)
        for p in self.players:
            if p.alive_in_match or self.state not in ("fight", "between", "intro"):
                continue
            # anel de "levante seu companheiro"
            sx, sy = round(p.x - cam.x), round(p.y + 14 - cam.y)
            r = REVIVE_RADIUS
            ring = pygame.Rect(0, 0, r * 2, r)
            ring.center = (sx, sy)
            pulse = 120 + round(60 * math.sin(self.frame * 0.15))
            layer = pygame.Surface(ring.inflate(8, 8).size, pygame.SRCALPHA)
            inner = pygame.Rect(4, 4, ring.w, ring.h)
            pygame.draw.ellipse(layer, (*p.color, pulse // 3), inner)
            pygame.draw.ellipse(layer, (*p.color, pulse), inner, 2)
            prog = self.revive_progress.get(p, 0.0)
            if prog > 0:
                pygame.draw.arc(layer, (*theme.BONE, 255), inner, math.pi / 2, math.pi / 2 + math.tau * prog, 4)
            view.blit(layer, ring.inflate(8, 8).topleft)

    def draw(self, screen, ui):
        super().draw(screen, ui)
        cam = self.camera
        for p in self.players:
            if not p.alive_in_match and self.state in ("fight", "between", "intro"):
                sx, sy = cam.to_screen(p.x, p.y - 34)
                if (self.frame // 20) % 2:
                    ui.text(screen, "LEVANTE!" if len(self.players) > 1 else "", theme.XS, p.color, (round(sx), round(sy)))
        self._draw_offscreen(screen, cam)
        hud.draw_campaign_banners(screen, ui, self)

    def _draw_offscreen(self, screen, cam):
        """Setinha na borda da tela apontando para os inimigos fora da câmera."""
        W, H = config.SCREEN_W, config.SCREEN_H
        cx = W / 2
        for e in self.alive_enemies + [_Point(p.x, p.y) for p in self.portals]:
            sx, sy = cam.to_screen(e.x, e.y - 20)
            if 0 <= sx <= W and 0 <= sy <= H:
                continue
            # a área das setas fica entre o HUD de cima e o de baixo
            top, bottom = 64, H - 72
            cy = (top + bottom) / 2
            dx, dy = sx - cx, sy - cy
            k = min((W / 2 - 22) / abs(dx) if dx else 1e9, (bottom - top) / 2 / abs(dy) if dy else 1e9)
            ax, ay = cx + dx * k, cy + dy * k
            d = math.hypot(dx, dy) or 1
            ux, uy = dx / d, dy / d
            big = e is self.boss
            size = 11 if big else 7
            color = SHADOW_AURA if big or getattr(e, "aura", None) else theme.BLOOD
            tip = (ax + ux * size, ay + uy * size)
            left = (ax - uy * size * 0.7, ay + ux * size * 0.7)
            right = (ax + uy * size * 0.7, ay - ux * size * 0.7)
            pygame.draw.polygon(screen, theme.SHADOW, [(x + 1, y + 1) for x, y in (tip, left, right)])
            pygame.draw.polygon(screen, color, (tip, left, right))

    def draw_hud(self, screen, ui):
        hud.draw_campaign(screen, ui, self)

    def hud_regions(self):
        W = config.SCREEN_W
        n = len(self.players)
        regions = [pygame.Rect(W // 2 - 230, 0, 460, 74), pygame.Rect(W - 190, 0, 190, 60)]
        for i in range(n):
            regions.append(pygame.Rect(*hud.campaign_block_rect(i, n)).inflate(8, 8))
        return regions


class _SoulParticle:
    """Luz que sobe do inimigo derrotado (a alma presa se libertando)."""

    def __init__(self, x, y):
        self.x = x + random.uniform(-10, 10)
        self.y = y + random.uniform(-8, 8)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-1.6, -0.6)
        self.life = self.max_life = random.randint(40, 70)
        self.color = random.choice(((200, 170, 255), (240, 230, 255), SHADOW_AURA))

    def update(self):
        self.x += self.vx + math.sin(self.life * 0.2) * 0.3
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surf, camera):
        s = 2 if self.life > self.max_life // 3 else 1
        surf.fill(self.color, (round(self.x - camera.x), round(self.y - camera.y), s, s + 1))


def _soul_particle(x, y):
    return _SoulParticle(x, y)


# ─────────────────────────────────────────────
#  História (cada página: retrato, quem fala, texto)
# ─────────────────────────────────────────────
CRYSTAL, BROKEN = "cristal", "cristal_quebrado"

STORY = {
    "prologo": ("PRÓLOGO", "templo_gelado", (
        (CRYSTAL, None, "No alto do Templo Gelado fica o Cristal das Almas. Ele guarda a força de todos "
                        "os lutadores da arena."),
        ("aryel", "ARYEL", "Com esse poder, ninguém mais me vence..."),
        ("sombra:aryel", None, "Aryel tocou no cristal e foi consumido por ele. Agora é ARYEL CORROMPIDO, "
                               "e quer a alma de todos."),
        (CRYSTAL, None, "Quem ele derrota vira sombra. Cheguem ao topo do templo e quebrem o cristal."),
    )),
    "floresta": ("FASE 1 · FLORESTA SOMBRIA", "floresta", (
        ("diabrete", None, "A corrupção começou na floresta. Diabretes saem de portais entre as árvores."),
        ("sombra:velocista", "VELOCISTA SOMBRIO", "Eu fui o primeiro a cair. Agora corro para o mestre... "
                                                  "e vocês não vão me alcançar."),
    )),
    "calabouco": ("FASE 2 · CALABOUÇO DAS ALMAS", "calabouco", (
        ("esqueleto", None, "Nos calabouços, as almas capturadas ficam presas. Só os ossos montam guarda."),
        ("sombra:tanque", "TANQUE SOMBRIO", "O mestre mandou ninguém passar. Ninguém passa."),
        ("sombra:ninja", None, "O Tanque e o Ninja já nem lembram quem são. Derrotem as sombras para "
                               "libertar os dois."),
    )),
    "templo": ("FASE 3 · TEMPLO GELADO", "templo_gelado", (
        (CRYSTAL, None, "No topo do Templo Gelado, o Cristal das Almas pulsa cada vez mais forte."),
        ("sombra:aryel", "ARYEL CORROMPIDO", "Vieram me entregar as suas almas? Que gentileza."),
    )),
    "final": ("FIM", "templo_gelado", (
        (BROKEN, None, "O cristal se parte em mil pedaços. As almas presas voltam para os seus donos."),
        ("aryel", "ARYEL", "O que... aconteceu? Eu lembro de tudo. Obrigado por me trazerem de volta."),
        ("sombra:aryel", None, "Mas a sombra de Aryel não sumiu. Agora ela luta do seu lado: "
                               "ARYEL CORROMPIDO está liberado no duelo."),
    )),
}
