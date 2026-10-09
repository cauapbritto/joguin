"""Partidas: a classe base Match e os dois modos de jogo (duelo e futebol)."""
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pygame

from . import config, hud, theme
from .ai import FighterAI, SoccerAI
from .arena import MAPS_BY_KEY, SOCCER_MAP, Arena
from .camera import Camera
from .data import CHARACTERS
from .entities import Barrier, Bullet, Entity, Explosion, FloatingText, Particle, Pickup
from .fighter import Fighter
from .net.remote import hub
from .soccer_powers import create_power


@dataclass
class Result:
    title: str
    color: tuple
    winners: list
    lines: list = field(default_factory=list)     # [(rótulo, valor)]
    score: tuple = None


class Match(ABC):
    min_zoom = 0.6

    def __init__(self, game, session, map_key):
        self.game = game
        self.assets = game.assets
        self.session = session
        self.arena = Arena(MAPS_BY_KEY[map_key], game.assets)
        self.camera = Camera(self.arena.size, self.min_zoom)
        self.fighters = []
        self.controllers = {}
        self.bullets = []
        self.effects = []
        self.particles = []
        self.popups = []
        self.frame = 0
        self.ending = 0           # quadros restantes da animação final
        self.hitstop = 0          # pausa curta quando um golpe acerta
        self.slowmo = 0           # câmera lenta (K.O.)
        self.finished = False
        self.result = None

    # ── criação ──────────────────────────────
    def _add_fighter(self, setup, pos, team=None, color=None):
        stats = CHARACTERS[setup.char]
        x, y = self.arena.free_spot(*pos, config.PLAYER_RADIUS + 2)
        fighter = Fighter(stats, setup.slot, x, y, self.assets.sprites[stats.key],
                          setup.label, color or setup.color, team=team,
                          weapon_index=setup.weapon, is_cpu=setup.cpu)
        fighter.facing = (1.0, 0.0) if x < self.arena.width / 2 else (-1.0, 0.0)
        self.fighters.append(fighter)
        return fighter

    # ── serviços usados por entidades e habilidades ──
    def spawn_bullet(self, owner, dx, dy, speed, damage, explosive=False):
        color = owner.stats.color
        self.bullets.append(Bullet(owner, owner.x + dx * 18, owner.y + dy * 18 - 4, dx, dy, speed, damage, color, explosive))

    def add_effect(self, effect):
        self.effects.append(effect)

    def burst(self, x, y, color, count, speed=4, gravity=0.0, size=4):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            s = random.uniform(speed * 0.3, speed)
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s, color,
                                           random.randint(14, 34), size, gravity))

    def popup(self, x, y, text, color):
        self.popups.append(FloatingText(x, y, text, color))

    def dust(self, x, y, count):
        for _ in range(count):
            self.particles.append(Particle(x + random.uniform(-8, 8), y - 2, random.uniform(-0.8, 0.8),
                                           random.uniform(-0.9, -0.2), (120, 112, 120),
                                           random.randint(12, 22), 4, gravity=0.02))

    def hit_pause(self, frames):
        self.hitstop = max(self.hitstop, frames)

    def opponents_of(self, fighter):
        return [f for f in self.fighters if f is not fighter and (f.team is None or f.team != fighter.team)]

    # ── ciclo ────────────────────────────────
    def update(self):
        if self.finished:
            return
        if self.hitstop > 0:
            self.hitstop -= 1
            self.camera.focus(self.focus_points())
            return
        if self.slowmo > 0:
            self.slowmo -= 1
            if self.slowmo % 2:
                self.camera.focus(self.focus_points())
                return
        self.frame += 1
        self.step()
        self.particles = [p for p in self.particles if p.update()]
        self.popups = [p for p in self.popups if p.update()]
        self.camera.focus(self.focus_points(), instant=self.frame == 1)

    def focus_points(self):
        return [(f.x, f.y - 20) for f in self.fighters]

    @abstractmethod
    def step(self):
        """Avança a lógica específica do modo."""

    @abstractmethod
    def draw_hud(self, screen, ui):
        """Placar, barras de vida etc."""

    def world_entities(self):
        return list(self.fighters)

    def draw(self, screen, ui):
        cam = self.camera
        view = cam.begin()
        self.arena.draw_floor(view, cam, view.get_size())
        self.draw_under(view, cam)
        self.arena.draw_walls(view, cam)
        for effect in self.effects:
            effect.draw(view, cam)
        for entity in sorted(self.world_entities(), key=lambda e: getattr(e, "sort_y", e.y)):
            entity.draw(view, cam)
        for b in self.bullets:
            b.draw(view, cam)
        for p in self.particles:
            p.draw(view, cam)
        cam.end(view, screen)
        for f in self.fighters:
            f.draw_overlay(screen, cam, ui, show_hp=not self.session.soccer)
        for p in self.popups:
            sx, sy = cam.to_screen(p.x, p.y)
            color = p.color if p.life > 8 or p.life % 2 else theme.FAINT
            ui.text(screen, p.text, theme.S if len(p.text) < 4 else theme.XS, color, (round(sx), round(sy)))
        self._draw_hud_layer(screen, ui)

    def draw_under(self, view, cam):
        pass

    # ── HUD ──────────────────────────────────
    def hud_regions(self):
        """Áreas da tela ocupadas pelo HUD (cada uma fica translúcida quando cobre o jogo)."""
        return [pygame.Rect(0, 0, config.SCREEN_W, config.SCREEN_H)]

    def _occluders(self):
        cam = self.camera
        scale = config.SCREEN_W / cam.view_size[0]
        rects = []
        for f in self.fighters:
            sx, sy = cam.to_screen(f.x, f.y - 20)
            r = pygame.Rect(0, 0, 44 * scale, 86 * scale)
            r.center = (sx, sy)
            rects.append(r)
        return rects

    def _draw_hud_layer(self, screen, ui):
        if not hasattr(self, "_hud_surface"):
            self._hud_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            self._hud_alpha = {}
        layer = self._hud_surface
        layer.fill((0, 0, 0, 0))
        self.draw_hud(layer, ui)
        occluders = self._occluders()
        for i, region in enumerate(self.hud_regions()):
            target = 85 if region.collidelist(occluders) >= 0 else 255
            alpha = self._hud_alpha.get(i, 255)
            alpha += (target - alpha) * 0.2
            self._hud_alpha[i] = alpha
            layer.set_alpha(round(alpha))
            screen.blit(layer, region.topleft, region)
        layer.set_alpha(255)        # set_alpha(None) quebraria o desenho do texto no quadro seguinte


# ─────────────────────────────────────────────
#  DUELO
# ─────────────────────────────────────────────
class BattleMatch(Match):
    """Duelo em melhor de 3 rounds, com relógio e itens aparecendo na arena."""

    def __init__(self, game, session):
        super().__init__(game, session, session.map_key)
        spawns = self.arena.cfg.spawns
        for setup, pos in zip(session.slots, spawns):
            fighter = self._add_fighter(setup, pos)
            fighter.full_name = setup.name
            if setup.cpu:
                self.controllers[fighter] = FighterAI(session.difficulty)
            else:
                self.controllers[fighter] = game.inputs[setup.slot]
        self.starts = {f: (f.x, f.y, f.facing) for f in self.fighters}
        self.wins = {f: 0 for f in self.fighters}
        self.round_no = 1
        self.rounds_played = 0
        self.pickups = []
        self.loser = None
        self._start_round()

    def _start_round(self):
        self.intro = config.ROUND_INTRO_FRAMES
        self.time_left = config.ROUND_SECONDS * config.FPS
        self.round_end = 0
        self.round_banner = None
        self.loser = None
        self.pickups.clear()
        self.pickup_timer = config.PICKUP_FIRST

    @property
    def active(self):
        """Os lutadores podem agir (fora da apresentação e do fim de round)."""
        return self.intro <= 30 and not self.round_end

    @property
    def match_point(self):
        return all(w == config.ROUNDS_TO_WIN - 1 for w in self.wins.values())

    def target_of(self, fighter):
        others = [f for f in self.fighters if f is not fighter and f.alive_in_match]
        return min(others, key=fighter.distance_to) if others else None

    def world_entities(self):
        return self.fighters + self.pickups

    def step(self):
        if self.intro > 0:
            self.intro -= 1
        if self.round_end:
            self.round_end -= 1
            if self.frame % 3 == 0 and self.loser:
                self.burst(self.loser.x, self.loser.y - 16, self.loser.stats.color, 2, speed=5)
            if self.round_end == 0:
                self._next_round()
                return
        active = self.active
        for fighter, ctrl in self.controllers.items():
            target = self.target_of(fighter)
            if not active or not fighter.alive_in_match or fighter.stunned:
                fighter.steer(0, 0)
            elif isinstance(ctrl, FighterAI):
                ctrl.update(fighter, target, self)
            else:
                self._human(fighter, ctrl, target)
            fighter.update(self)
        self._update_bullets()
        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]
        self._update_pickups(active)
        if not active:
            return
        dead = [f for f in self.fighters if not f.alive_in_match]
        if dead:
            self.loser = dead[0]
            winner = self.target_of(self.loser)
            self._end_round(winner, "ko")
            return
        self.time_left -= 1
        if self.time_left <= 0:
            a, b = self.fighters
            ra, rb = a.hp / a.stats.max_hp, b.hp / b.stats.max_hp
            winner = a if ra > rb else b if rb > ra else None
            self._end_round(winner, "time")

    def _end_round(self, winner, reason):
        self.round_end = config.ROUND_END_FRAMES
        self.rounds_played += 1
        self.bullets.clear()
        if winner is not None:
            self.wins[winner] += 1
        if reason == "ko":
            self.slowmo = 50
            self.burst(self.loser.x, self.loser.y - 16, self.loser.stats.color, 30, speed=7)
            self.camera.shake(10)
            title = "K.O.!"
        else:
            title = "TEMPO!"
        sub = f"{winner.full_name} VENCE O ROUND" if winner else "EMPATE"
        self.round_banner = (title, sub, winner.color if winner else theme.BONE)
        if self._decided():
            self.assets.stop_music(1500)
            champion = max(self.fighters, key=lambda f: self.wins[f])
            human_won = not champion.is_cpu
            self.assets.play("victory" if human_won else "gameover", 0.5)
        else:
            self.assets.play("hit", 0.6)

    def _decided(self):
        return (any(w >= config.ROUNDS_TO_WIN for w in self.wins.values())
                or self.rounds_played >= config.MAX_ROUNDS)

    def _next_round(self):
        if self._decided():
            self._finish()
            return
        self.round_no += 1
        for f, (x, y, facing) in self.starts.items():
            f.reset_round(x, y, facing)
        self.bullets.clear()
        self.effects.clear()
        self._start_round()

    def _human(self, fighter, inp, target):
        fighter.steer(*inp.axis())
        if inp.held("attack"):
            fighter.attack(self, target)
        if inp.pressed("special"):
            fighter.use_ability(self, target)
        if inp.pressed("switch") and fighter.switch_weapon():
            self.assets.play("click", 0.4)
        direction = None
        if inp.pressed("dodge"):
            direction = fighter.input if any(fighter.input) else fighter.facing
        elif inp.double_tap:
            direction = inp.double_tap
        if direction and fighter.dash(direction):
            self.assets.play("dash", 0.3)

    def _update_pickups(self, active):
        for item in self.pickups:
            item.update(self)
            if not item.alive:
                continue
            for f in self.fighters:
                if f.alive_in_match and math.hypot(f.x - item.x, f.y - item.y) < f.radius + item.radius + 6:
                    item.apply(f, self)
                    break
        self.pickups = [p for p in self.pickups if p.alive]
        if not active:
            return
        self.pickup_timer -= 1
        if self.pickup_timer <= 0:
            self.pickup_timer = random.randint(*config.PICKUP_EVERY)
            if len(self.pickups) < config.PICKUP_MAX:
                self._spawn_pickup()

    def _spawn_pickup(self):
        for _ in range(20):
            x, y = self.arena.random_free_spot(16)
            if all(math.hypot(f.x - x, f.y - y) > 160 for f in self.fighters):
                break
        kind = random.choices(("vida", "furia", "energia"), weights=(45, 30, 25))[0]
        self.pickups.append(Pickup(kind, x, y))
        self.burst(x, y - 10, Pickup.KINDS[kind][1], 10, speed=2)

    def _update_bullets(self):
        alive = []
        for b in self.bullets:
            if b.alive:
                b.update(self)
            if b.alive and any(w.rect.colliderect(b.rect) for w in self.arena.walls):
                b.alive = False
            if b.alive:
                for e in self.effects:
                    if isinstance(e, Barrier) and e.owner is not b.owner and e.rect.colliderect(b.rect):
                        b.alive = False
                        self.burst(b.x, b.y, (150, 226, 240), 4, speed=2)
                        break
            if b.alive:
                for f in self.fighters:
                    if f is b.owner or not f.alive_in_match or f.dash_timer > 0:
                        continue
                    if math.hypot(f.x - b.x, f.y - 6 - b.y) < f.radius + b.radius + 4:
                        b.alive = False
                        if not b.explosive:
                            if f.invulnerable_timer > 0:
                                self.popup(f.x, f.y - 46, "IMUNE", theme.BRASS)
                            f.take_damage(b.damage, b.x, b.y, attacker=b.owner, match=self)
                        break
            if not b.alive and b.explosive:
                self.effects.append(Explosion(b.owner, b.x, b.y, b.damage))
                self.assets.play("explosion", 0.45)
                self.camera.shake(5)
            if b.alive:
                alive.append(b)
        self.bullets = alive

    def _finish(self):
        a, b = self.fighters
        if self.wins[a] == self.wins[b]:
            winners, title, color = [], "EMPATE", theme.BONE
        else:
            winner = a if self.wins[a] > self.wins[b] else b
            winners = [winner]
            if winner.is_cpu:
                title, color = "A CPU VENCEU", theme.CPU_COLOR
            else:
                title, color = f"JOGADOR {winner.slot} VENCEU", winner.color
        seconds = self.frame // config.FPS
        lines = [("ROUNDS", f"{self.wins[a]} x {self.wins[b]}"),
                 ("TEMPO TOTAL", f"{seconds // 60}:{seconds % 60:02d}")]
        for f in self.fighters:
            lines.append((f"{f.label} DANO CAUSADO", str(f.damage_dealt)))
        self.result = Result(title, color, winners, lines, score=(self.wins[a], self.wins[b]))
        self.finished = True

    def draw(self, screen, ui):
        super().draw(screen, ui)
        hud.draw_round_banner(screen, ui, self)

    def draw_hud(self, screen, ui):
        hud.draw_battle(screen, ui, self)

    def hud_regions(self):
        W, half = config.SCREEN_W, 52
        return [pygame.Rect(0, 0, W // 2 - half, 104), pygame.Rect(W // 2 - half, 0, half * 2, 104),
                pygame.Rect(W // 2 + half, 0, W // 2 - half, 104)]


# ─────────────────────────────────────────────
#  FUTEBOL
# ─────────────────────────────────────────────
class Ball(Entity):
    radius = config.BALL_RADIUS

    def __init__(self, x, y):
        super().__init__(x, y)
        self.reset(x, y)

    def reset(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.homing_timer = 0
        self.homing_target = None
        self.homing_player = None
        self.homing_force = 0.0
        self.spin = 0.0
        self.ghost_timer = 0
        self.ghost_team = None
        self.z = 0.0                # altura
        self.vz = 0.0
        self.squash = 0

    @property
    def airborne(self):
        return self.z > 0.5 or self.vz > 0

    @property
    def sort_y(self):
        return self.y + (5000 if self.z > config.BODY_HEIGHT else 0)

    def lift(self, vz):
        self.vz = vz
        self.z = max(self.z, 0.1)

    def landing(self):
        """Onde e daqui a quantos quadros a bola toca o chão."""
        if not self.airborne:
            return self.x, self.y, 0
        g = config.GRAVITY
        t = (self.vz + math.sqrt(self.vz * self.vz + 2 * g * self.z)) / g
        return self.x + self.vx * t, self.y + self.vy * t, t

    def update(self, match):
        if self.z > 0 or self.vz > 0:
            self.vz -= config.GRAVITY
            self.z += self.vz
            if self.z <= 0:
                self.z = 0.0
                if self.vz < -1.4:
                    # quique: perde força a cada toque no chão
                    self.vz = -self.vz * config.BOUNCE
                    self.vx *= 0.82
                    self.vy *= 0.82
                    self.squash = 4
                    match.ball_bounced(self)
                else:
                    self.vz = 0.0
        friction = 0.996 if self.airborne else config.BALL_FRICTION
        if self.squash:
            self.squash -= 1
        self.vx *= friction
        self.vy *= friction
        if abs(self.vx) < 0.05:
            self.vx = 0.0
        if abs(self.vy) < 0.05:
            self.vy = 0.0
        speed = math.hypot(self.vx, self.vy)
        if speed > config.BALL_MAX_SPEED:
            self.vx *= config.BALL_MAX_SPEED / speed
            self.vy *= config.BALL_MAX_SPEED / speed
        if self.homing_timer > 0:
            if self.homing_player is not None:
                self.homing_target = (self.homing_player.x, self.homing_player.y)
            hx, hy = self.homing_target[0] - self.x, self.homing_target[1] - self.y
            hm = math.hypot(hx, hy)
            if hm > 0:
                self.vx += hx / hm * self.homing_force
                self.vy += hy / hm * self.homing_force
            self.homing_timer -= 1
        if self.ghost_timer > 0:
            self.ghost_timer -= 1
        self.x += self.vx
        self.y += self.vy
        self.spin += math.hypot(self.vx, self.vy) * 0.15

    def draw(self, surf, camera):
        gx, gy = round(self.x - camera.x), round(self.y - camera.y)
        # sombra fica no chão e encolhe com a altura
        shrink = max(0.5, 1 - self.z / 160)
        sw, sh = round(24 * shrink), max(4, round(9 * shrink))
        pygame.draw.ellipse(surf, (12, 30, 16), (gx - sw // 2, gy + 10 - sh // 2, sw, sh))
        sx, sy = gx, gy - round(self.z)
        r = round(self.radius * (1 + self.z / 220))
        if self.squash:
            rect = pygame.Rect(0, 0, r * 2 + 4, r * 2 - 4)
            rect.center = (sx, sy + 2)
            pygame.draw.ellipse(surf, (24, 20, 28), rect.inflate(2, 2))
            pygame.draw.ellipse(surf, (238, 236, 228), rect)
            return
        if self.ghost_timer > 0:
            pygame.draw.circle(surf, (150, 104, 214), (sx, sy), r + 3, 2)
            pygame.draw.circle(surf, (196, 170, 236), (sx, sy), r)
            return
        pygame.draw.circle(surf, (24, 20, 28), (sx, sy), r + 1)
        pygame.draw.circle(surf, (238, 236, 228), (sx, sy), r)
        for k in range(3):
            a = self.spin + k * math.tau / 3
            px, py = sx + math.cos(a) * r * 0.55, sy + math.sin(a) * r * 0.55 * 0.8
            pygame.draw.circle(surf, (40, 38, 48), (round(px), round(py)), 3)
        pygame.draw.circle(surf, (255, 255, 255), (sx - 4, sy - 4), 2)
        if self.homing_timer > 0:
            pygame.draw.circle(surf, theme.BRASS, (sx, sy), r + 4, 2)


class Goal(Entity):
    def __init__(self, x, y, w, h, team):
        super().__init__(x, y)
        self.rect = pygame.Rect(x, y, w, h)
        self.team = team

    def update(self, match):
        pass

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        color = theme.TEAM_COLORS[self.team]
        surf.fill(tuple(c // 4 for c in color), r)
        for x in range(r.x, r.right, 6):
            surf.fill(tuple(c // 2 for c in color), (x, r.y, 1, r.h))
        for y in range(r.y, r.bottom, 6):
            surf.fill(tuple(c // 2 for c in color), (r.x, y, r.w, 1))
        for py in (r.y - 6, r.bottom):
            surf.fill((230, 230, 222), (r.x - 2, py, r.w + 22, 6))


class SoccerMatch(Match):
    min_zoom = 0.55
    GOAL_TOP, GOAL_BOTTOM = 370, 530

    def __init__(self, game, session):
        super().__init__(game, session, SOCCER_MAP)
        spawns = self.arena.cfg.spawns
        self.spawn_of = {}
        for setup in session.slots:
            team = session.team_of(setup.slot)
            pos = spawns[setup.slot - 1]
            fighter = self._add_fighter(setup, pos, team=team, color=theme.TEAM_COLORS[team] if setup.cpu else None)
            fighter.ring_color = theme.TEAM_COLORS[team]
            fighter.armed = False
            fighter.power = create_power(fighter.stats)
            self.spawn_of[fighter] = pos
            self.controllers[fighter] = SoccerAI() if setup.cpu else game.inputs[setup.slot]
        self.ball = Ball(self.arena.width / 2, self.arena.height / 2)
        self.goals = [Goal(2, self.GOAL_TOP, 18, self.GOAL_BOTTOM - self.GOAL_TOP, 0),
                      Goal(1580, self.GOAL_TOP, 18, self.GOAL_BOTTOM - self.GOAL_TOP, 1)]
        self.score = [0, 0]
        self.freeze = 0
        self.last_touch = None
        self.goal_banner = None
        self.banner_age = 0
        self._ball_trail = []
        self.ball_walls = []
        self.possessor = None       # quem está com a bola no pé
        self.no_trap = {}
        self.contest = {}

    @staticmethod
    def goal_x(team):
        """Linha do gol que o time defende."""
        return 20 if team == 0 else 1580

    def focus_points(self):
        pts = [(f.x, f.y - 20) for f in self.fighters]
        pts.append((self.ball.x, self.ball.y - self.ball.z))
        return pts

    def world_entities(self):
        return self.fighters + [self.ball]

    def draw_under(self, view, cam):
        for g in self.goals:
            g.draw(view, cam)
        for w in self.ball_walls:
            w.draw(view, cam)
        p = self.possessor
        if p is not None:
            # marca discreta no chão de quem está com a bola
            rect = pygame.Rect(0, 0, 54, 18)
            rect.center = (round(p.x - cam.x), round(p.y - cam.y) + 22)
            pygame.draw.ellipse(view, (232, 232, 220), rect, 1)

    def foes_of(self, f):
        return [o for o in self.fighters if o.team != f.team]

    def ball_bounced(self, ball):
        if ball.vz > 2:
            self.assets.play("click", min(0.35, ball.vz * 0.06))
            self.dust(ball.x, ball.y + 8, 3)

    def mates_of(self, f):
        return [o for o in self.fighters if o.team == f.team and o is not f]

    def add_ball_wall(self, wall):
        self.ball_walls = [w for w in self.ball_walls if w.team != wall.team]
        self.ball_walls.append(wall)

    # ── ações ────────────────────────────────
    def touching(self, f, extra=15, max_z=config.BODY_HEIGHT):
        ball = self.ball
        if ball.ghost_timer > 0 and f.team != ball.ghost_team:
            return False
        if ball.z > max_z:
            return False
        if f is self.possessor:
            return True         # quem conduz sempre alcança a bola, mesmo correndo
        return math.hypot(ball.x - f.x, ball.y - f.y) < f.radius + ball.radius + extra

    def can_head(self, f):
        lo, hi = config.HEAD_RANGE
        return lo <= self.ball.z <= hi and self.touching(f, 10, max_z=hi)

    def header(self, f, direction=None):
        """Cabeçada: desvia a bola alta na direção em que o jogador olha."""
        if self.freeze or f.stunned or not self.can_head(f):
            return False
        self._release(f, 8)
        dx, dy = direction or f.facing
        ball = self.ball
        ball.vx, ball.vy = dx * 8, dy * 8
        ball.lift(2.5)
        ball.homing_timer = 0
        f.kick_cd = 14
        self.last_touch = f
        self.popup(f.x, f.y - 74, "CABEÇA", theme.BONE)
        self.assets.play("hit", 0.35)
        return True

    def _release(self, f, frames=config.NO_TRAP_FRAMES):
        """O jogador soltou a bola (chute, passe, poder): não a domina de novo na hora."""
        if self.possessor is f:
            self.possessor = None
        self.no_trap[f] = frames
        self.contest.clear()

    def kick(self, f, direction=None, loft=0.0):
        """Chute rasteiro (loft=0) ou pelo alto (loft de 0 a 1 = força e altura)."""
        if self.freeze or f.kick_cd > 0 or f.stunned:
            return False
        if self.can_head(f):
            return self.header(f, direction)
        if not self.touching(f):
            return False
        self._release(f)
        dx, dy = direction or f.facing
        ball = self.ball
        if loft > 0:
            power = 8 + 4 * loft
            ball.lift(5 + 3 * loft)
        else:
            power = config.KICK_POWER
        ball.vx, ball.vy = dx * power, dy * power
        ball.homing_timer = 0
        f.kick_cd = 14
        self.last_touch = f
        self.assets.play("shoot", 0.3)
        return True

    def pass_ball(self, f, high=False):
        if self.freeze or f.stunned or not self.touching(f):
            return False
        self._release(f)
        mates = [m for m in self.fighters if m.team == f.team and m is not f]
        ball = self.ball
        mate = min(mates, key=f.distance_to) if mates else None
        if high:
            # passe por cima: calcula o arco para cair no pé do companheiro (ou à frente)
            if mate is not None:
                tx = mate.x + (mate.x - mate.prev_pos[0]) * 24
                ty = mate.y + (mate.y - mate.prev_pos[1]) * 24
            else:
                tx, ty = f.x + f.facing[0] * 320, f.y + f.facing[1] * 320
            dx, dy = tx - ball.x, ty - ball.y
            dist = math.hypot(dx, dy) or 1
            t = max(22.0, min(48.0, dist / 8))
            speed = min(config.BALL_MAX_SPEED, dist / t)
            f.facing = (dx / dist, dy / dist)
            ball.vx, ball.vy = f.facing[0] * speed, f.facing[1] * speed
            ball.lift(config.GRAVITY * t / 2)
            ball.homing_timer = 0
        else:
            if mate is not None:
                f.face(mate)
                ball.homing_timer = config.PASS_HOMING_FRAMES
                ball.homing_player = mate
                ball.homing_target = (mate.x, mate.y)
                ball.homing_force = config.PASS_HOMING_FORCE
            ball.vx, ball.vy = f.facing[0] * config.PASS_POWER, f.facing[1] * config.PASS_POWER
        self.last_touch = f
        self.assets.play("shoot", 0.25)
        return True

    def use_power(self, f):
        if self.freeze or self.ending:
            return False
        used = f.power.use(f, self)
        if used and f.power.needs_ball:
            self._release(f, 20)
        return used

    def cut(self, f, direction=None):
        """Corte: drible lateral rápido."""
        lx, ly = direction or f.facing
        if direction is None:
            lx, ly = -ly, lx
        if not f.dash((lx, ly), frames=6, cooldown=30):
            return
        self.assets.play("dash", 0.3)
        owner = self.possessor
        if not self.freeze and owner is not None and owner.team != f.team and self.touching(f, 12):
            # corte em cima de quem está com a bola: cutuca a bola para longe
            self._release(owner, 24)
            self.ball.vx, self.ball.vy = lx * 7, ly * 7
            self.last_touch = f
            self.burst(self.ball.x, self.ball.y, (236, 230, 220), 6, speed=3)
        elif owner is f:
            f.carry_dir = (lx, ly)     # o corte leva a bola junto

    # ── ciclo ────────────────────────────────
    def step(self):
        if self.goal_banner:
            self.banner_age += 1
        if self.ending:
            self.ending -= 1
            if self.frame % 4 == 0:
                team = self.result_team
                self.burst(random.uniform(200, 1400), random.uniform(100, 400), theme.TEAM_COLORS[team], 6,
                           speed=3, gravity=0.15, size=5)
            if self.ending == 0:
                self._finish()
                return

        for f in self.fighters:
            f.prev_pos = (f.x, f.y)
        for f, ctrl in self.controllers.items():
            if self.freeze or self.ending or f.stunned:
                f.steer(0, 0)
            elif isinstance(ctrl, SoccerAI):
                ctrl.update(f, self)
            else:
                self._human(f, ctrl)
            f.update(self)
            if f.tackle_timer > 0:
                self._tackle(f)
        for w in self.ball_walls:
            w.update(self)
        self.ball_walls = [w for w in self.ball_walls if w.alive]

        for i, a in enumerate(self.fighters):
            for b in self.fighters[i + 1:]:
                _separate(a, b)
                self.arena.resolve(a)
                self.arena.resolve(b)

        if not self.freeze and not self.ending:
            self._update_ball()
        elif self.freeze:
            self.freeze -= 1
            if self.freeze == 0:
                self._kickoff()

        for f in self.fighters:
            if not f.is_cpu:
                hub.publish_slot(f.slot, cooldown=f.super_cd / f.power.cooldown)

    def _tackle(self, f):
        """Carrinho do Guerreiro: derruba adversários e leva a bola."""
        f.tackle_timer -= 1
        for foe in self.foes_of(f):
            if f.distance_to(foe) < f.radius + foe.radius + 8 and not foe.stunned and foe.stun(60):
                self.burst(foe.x, foe.y, (236, 230, 220), 8, speed=3)
                self.camera.shake(5)
                self.assets.play("hit", 0.5)
        if not self.freeze and self.touching(f, 4) and self.possessor is not f:
            if self.possessor is not None:
                self._release(self.possessor, 30)
            self._take(f)

    def _human(self, f, inp):
        f.steer(*inp.axis())
        # CHUTE: toque = rasteiro; segurar e soltar = pelo alto. Bola na altura da cabeça = cabeçada.
        if inp.held("attack"):
            f.kick_charge = min(f.kick_charge + 1, config.MAX_CHARGE)
            if self.can_head(f) and f.kick_cd <= 0:
                self.header(f)
                f.kick_charge = 0
        elif f.kick_charge:
            if not any(f.input):
                f.face(self.ball)
            self.kick(f, loft=_loft(f.kick_charge))
            f.kick_charge = 0
        # PASSE: mesma ideia
        if inp.held("special"):
            f.pass_charge = min(f.pass_charge + 1, config.MAX_CHARGE)
        elif f.pass_charge:
            self.pass_ball(f, high=f.pass_charge >= config.LOFT_FRAMES)
            f.pass_charge = 0
        if inp.pressed("super"):
            if not self.use_power(f):
                self.assets.play("cancel", 0.2)
        if inp.pressed("dodge"):
            self.cut(f)
        elif inp.double_tap:
            self.cut(f, inp.double_tap)
        f.dribbling = inp.held("dribble") or f.sprint_timer > 0

    # ── posse e condução ─────────────────────
    def _can_touch(self, f):
        ball = self.ball
        return not f.stunned and f not in self.no_trap and not (ball.ghost_timer > 0 and f.team != ball.ghost_team)

    def _trappable_height(self):
        ball = self.ball
        return ball.z < 16 or (ball.vz < 0 and ball.z < 34)     # bola descendo: domínio no peito

    def _update_possession(self):
        ball = self.ball
        for f in list(self.no_trap):
            self.no_trap[f] -= 1
            if self.no_trap[f] <= 0:
                del self.no_trap[f]
        owner = self.possessor
        if owner is not None:
            d = owner.distance_to(ball)
            if not self._can_touch(owner) or d > owner.radius + ball.radius + config.LOSE_DISTANCE:
                self.possessor = None
                self.contest.clear()
                return
            # disputa: o adversário que fica mais perto da bola por um tempo toma a posse
            for foe in self.foes_of(owner):
                fd = foe.distance_to(ball)
                if self._can_touch(foe) and fd < foe.radius + ball.radius + 6 and fd < d:
                    self.contest[foe] = self.contest.get(foe, 0) + 1
                    if self.contest[foe] >= config.STEAL_FRAMES:
                        self._take(foe)
                        self.burst(ball.x, ball.y, (236, 230, 220), 6, speed=3)
                        self.assets.play("dash", 0.25)
                        return
                else:
                    self.contest.pop(foe, None)
            return
        # bola sem dono: quem encostar e conseguir dominar fica com ela
        if not self._trappable_height():
            return
        best, best_d = None, 1e9
        for f in self.fighters:
            if not self._can_touch(f):
                continue
            d = f.distance_to(ball)
            if d < f.radius + ball.radius + 8:
                rel = math.hypot(ball.vx - (f.x - f.prev_pos[0]), ball.vy - (f.y - f.prev_pos[1]))
                limit = config.TRAP_SPEED + (3 if ball.airborne else 0)
                if (rel < limit or f.dribbling) and d < best_d:
                    best, best_d = f, d
        if best is not None:
            self._take(best)

    def _take(self, f):
        ball = self.ball
        if ball.airborne:
            self.popup(f.x, f.y - 74, "DOMINOU", theme.BONE)
        ball.z = ball.vz = 0.0
        self.possessor = f
        self.contest.clear()
        dx, dy = ball.x - f.x, ball.y - f.y
        d = math.hypot(dx, dy) or 1
        f.carry_dir = (dx / d, dy / d)
        ball.homing_timer = 0
        self.last_touch = f

    def _carry(self, f):
        """A bola acompanha o pé: amortecida, sem quicar, e vira junto aos poucos."""
        ball = self.ball
        close = f.dribbling
        f.carrying_close = close
        turn = config.CLOSE_TURN if close else config.CARRY_TURN
        fx, fy = f.facing
        cx, cy = f.carry_dir
        cx += (fx - cx) * turn
        cy += (fy - cy) * turn
        m = math.hypot(cx, cy) or 1
        f.carry_dir = (cx / m, cy / m)
        vx, vy = f.x - f.prev_pos[0], f.y - f.prev_pos[1]      # deslocamento real (inclui corte)
        speed = math.hypot(vx, vy)
        ahead = f.radius + ball.radius + (2 if close else 4 + speed * 1.6)
        tx, ty = f.x + f.carry_dir[0] * ahead, f.y + f.carry_dir[1] * ahead
        gain = config.CLOSE_GAIN if close else config.CARRY_GAIN
        ball.vx = vx + (tx - ball.x) * gain
        ball.vy = vy + (ty - ball.y) * gain
        self.last_touch = f

    def _update_ball(self):
        ball = self.ball
        self._update_possession()
        for f in self.fighters:
            if f is not self.possessor:
                f.carrying_close = False
        if self.possessor is not None:
            self._carry(self.possessor)
        ball.update(self)
        _bounce_off_walls(ball, self.arena.walls + self.ball_walls)
        for f in self.fighters:
            if f is self.possessor or (ball.ghost_timer > 0 and f.team != ball.ghost_team):
                continue
            if ball.z > config.BODY_HEIGHT:
                continue        # bola alta passa por cima
            # corpo de quem não está com a bola funciona como obstáculo
            dx, dy = ball.x - f.x, ball.y - f.y
            dist = math.hypot(dx, dy)
            mind = ball.radius + f.radius
            if 0 < dist < mind:
                nx, ny = dx / dist, dy / dist
                ball.x += nx * (mind - dist)
                ball.y += ny * (mind - dist)
                dot = ball.vx * nx + ball.vy * ny
                if dot < 0:
                    ball.vx -= 1.6 * dot * nx
                    ball.vy -= 1.6 * dot * ny
                ball.vx += nx * 0.8
                ball.vy += ny * 0.8
                self.last_touch = f
        # bola presa entre jogadores (só quando ninguém domina)
        self._ball_trail.append((ball.x, ball.y))
        if self.possessor is not None:
            self._ball_trail.clear()
        elif len(self._ball_trail) > 24:
            self._ball_trail.pop(0)
            (x0, y0) = self._ball_trail[0]
            close = [f for f in self.fighters if math.hypot(f.x - ball.x, f.y - ball.y) < ball.radius + f.radius + 6]
            if len(close) >= 2 and math.hypot(ball.x - x0, ball.y - y0) < 8:
                cx = sum(f.x for f in close) / len(close)
                cy = sum(f.y for f in close) / len(close)
                ax, ay = ball.x - cx, ball.y - cy
                d = math.hypot(ax, ay)
                # sai pela lateral da disputa
                px, py = (-ay / d, ax / d) if d else (0.0, 1.0)
                side = random.choice((-1, 1))
                ball.vx, ball.vy = px * side * 6, py * side * 6
                self._ball_trail.clear()
        if self.GOAL_TOP < ball.y < self.GOAL_BOTTOM and (ball.x < 20 or ball.x > 1580):
            defending = 0 if ball.x < 20 else 1
            if ball.z > config.CROSSBAR:
                self._over_bar(defending)
            else:
                self._goal(scoring_team=1 - defending)
        if not (-100 < ball.x < self.arena.width + 100 and -100 < ball.y < self.arena.height + 100):
            ball.reset(self.arena.width / 2, self.arena.height / 2)

    def _over_bar(self, defending):
        """Passou por cima do gol: tiro de meta para quem defende."""
        x = 110 if defending == 0 else self.arena.width - 110
        self.popup(self.goal_x(defending), self.arena.height / 2 - 60, "POR CIMA", theme.BONE)
        self.ball.reset(x, self.arena.height / 2)
        self.possessor = None
        self.last_touch = None
        self.assets.play("cancel", 0.3)

    def _goal(self, scoring_team):
        self.score[scoring_team] += 1
        self.freeze = config.GOAL_FREEZE
        scorer = self.last_touch
        own_goal = scorer is not None and scorer.team != scoring_team
        if scorer is not None and not own_goal:
            scorer.goals += 1
        self.goal_banner = (scoring_team, scorer.label if scorer else "", own_goal)
        self.banner_age = 0
        color = theme.TEAM_COLORS[scoring_team]
        self.burst(self.ball.x, self.ball.y, color, 40, speed=8, gravity=0.1, size=5)
        self.burst(self.ball.x, self.ball.y, theme.BONE, 20, speed=6, gravity=0.1, size=3)
        self.camera.shake(8)
        self.assets.play("victory", 0.5)
        if self.score[scoring_team] >= config.WIN_SCORE:
            self.result_team = scoring_team
            self.ending = config.DEATH_ANIM_FRAMES + 30
            self.freeze = 0
            self.assets.stop_music(1800)

    def _kickoff(self):
        self.goal_banner = None
        self.ball.reset(self.arena.width / 2, self.arena.height / 2)
        self.last_touch = None
        self.ball_walls.clear()
        self.possessor = None
        self.no_trap.clear()
        self.contest.clear()
        for f, pos in self.spawn_of.items():
            f.x, f.y = pos
            f.vx = f.vy = 0
            f.knock = [0.0, 0.0]
            f.stun_timer = f.tackle_timer = f.sprint_timer = f.dash_timer = 0
            f.facing = (1.0, 0.0) if f.team == 0 else (-1.0, 0.0)

    def _finish(self):
        team = self.result_team
        winners = [f for f in self.fighters if f.team == team]
        lines = [("PLACAR", f"{self.score[0]} x {self.score[1]}")]
        for f in self.fighters:
            lines.append((f"{f.label} GOLS", str(f.goals)))
        self.result = Result(f"TIME {theme.TEAM_NAMES[team]} VENCEU", theme.TEAM_COLORS[team], winners,
                             lines, score=tuple(self.score))
        self.finished = True

    def draw(self, screen, ui):
        super().draw(screen, ui)
        # barra de força enquanto segura CHUTE/PASSE
        for f in self.fighters:
            charge = max(f.kick_charge, f.pass_charge)
            if charge < 4:
                continue
            sx, sy = self.camera.to_screen(f.x, f.y + 32)
            high = charge >= config.LOFT_FRAMES
            ui.bar(screen, (round(sx) - 16, round(sy), 32, 5), charge / config.MAX_CHARGE,
                   theme.BRASS if high else theme.SKY)
            if high:
                ui.text(screen, "ALTO", theme.XS, theme.BRASS, (round(sx), round(sy) + 12))
        if self.goal_banner:
            hud.draw_goal_banner(screen, ui, *self.goal_banner, self.banner_age)

    def draw_hud(self, screen, ui):
        hud.draw_soccer(screen, ui, self)

    def hud_regions(self):
        W, H = config.SCREEN_W, config.SCREEN_H
        return [pygame.Rect(W // 2 - 166, 0, 332, 86), pygame.Rect(0, H - 52, W, 52)]

    def _occluders(self):
        rects = super()._occluders()
        sx, sy = self.camera.to_screen(self.ball.x, self.ball.y - self.ball.z)
        r = pygame.Rect(0, 0, 30, 30)
        r.center = (sx, sy)
        rects.append(r)
        return rects


def _loft(charge):
    """Quadros segurando o botão → 0 (rasteiro) ou 0..1 (altura/força do chute alto)."""
    if charge < config.LOFT_FRAMES:
        return 0.0
    return 0.15 + 0.85 * (charge - config.LOFT_FRAMES) / (config.MAX_CHARGE - config.LOFT_FRAMES)


def _separate(a, b):
    """Afasta dois jogadores que se sobrepõem; o maior (Gigante) quase não se mexe."""
    dx, dy = b.x - a.x, b.y - a.y
    dist = math.hypot(dx, dy)
    mind = a.radius + b.radius
    if 0 < dist < mind:
        overlap = mind - dist
        ma, mb = a.radius ** 3, b.radius ** 3
        nx, ny = dx / dist, dy / dist
        a.x -= nx * overlap * mb / (ma + mb)
        a.y -= ny * overlap * mb / (ma + mb)
        b.x += nx * overlap * ma / (ma + mb)
        b.y += ny * overlap * ma / (ma + mb)


def _bounce_off_walls(ball, walls):
    for _ in range(3):
        hit = False
        for wall in walls:
            r = wall.rect
            cx = min(max(ball.x, r.left), r.right)
            cy = min(max(ball.y, r.top), r.bottom)
            dx, dy = ball.x - cx, ball.y - cy
            d2 = dx * dx + dy * dy
            if d2 >= ball.radius * ball.radius:
                continue
            hit = True
            if d2 < 1e-4:
                gaps = {"l": ball.x - r.left, "r": r.right - ball.x, "t": ball.y - r.top, "b": r.bottom - ball.y}
                side = min(gaps, key=gaps.get)
                if side == "l":
                    ball.x, ball.vx = r.left - ball.radius, -abs(ball.vx) * 0.75
                elif side == "r":
                    ball.x, ball.vx = r.right + ball.radius, abs(ball.vx) * 0.75
                elif side == "t":
                    ball.y, ball.vy = r.top - ball.radius, -abs(ball.vy) * 0.75
                else:
                    ball.y, ball.vy = r.bottom + ball.radius, abs(ball.vy) * 0.75
                continue
            d = math.sqrt(d2)
            nx, ny = dx / d, dy / d
            ball.x += nx * (ball.radius - d + 0.1)
            ball.y += ny * (ball.radius - d + 0.1)
            dot = ball.vx * nx + ball.vy * ny
            if dot < 0:
                ball.vx = (ball.vx - 2 * dot * nx) * 0.75
                ball.vy = (ball.vy - 2 * dot * ny) * 0.75
        if not hit:
            break


def create_match(game, session):
    return SoccerMatch(game, session) if session.soccer else BattleMatch(game, session)
