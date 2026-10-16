"""Partidas: a classe base Match e os dois modos de jogo (duelo e futebol)."""
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pygame

from . import config, hud, theme
from .ai import FighterAI, SoccerAI
from .arena import MAPS_BY_KEY, SOCCER_MAP, Arena, Pitch
from .camera import Camera
from .data import CHARACTERS, SHADOW_CHARACTERS
from .entities import Barrier, Bullet, Entity, Explosion, FloatingText, Particle, Pickup, hostile
from .fighter import Fighter
from .net.remote import hub
from .projectiles import projectile_class
from .soccer_assist import (ASSIST_LEVELS, closest_approach, pick_receiver, segment_contact, shot_assist,
                            unit)
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
        if stats.key in SHADOW_CHARACTERS:
            from .enemies import SHADOW_RIM
            fighter.aura = SHADOW_RIM          # Aryel Corrompido jogável também solta a sombra
        self.fighters.append(fighter)
        return fighter

    # ── serviços usados por entidades e habilidades ──
    def spawn_bullet(self, owner, dx, dy, speed, damage, explosive=False):
        color = owner.stats.color
        self.bullets.append(Bullet(owner, owner.x + dx * 18, owner.y + dy * 18 - 4, dx, dy, speed, damage, color, explosive))

    def spawn_projectile(self, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
        """Tiro de uma arma: cada estilo de arma tem sua classe de projétil (flecha, granada...)."""
        proj = projectile_class(weapon.style).launch(self, owner, weapon, direction, damage, target, power,
                                                     explosive)
        self.bullets.append(proj)
        return proj

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

    def hit_feedback(self, target, amount):
        """Tremida e pausa curta quando alguém leva um golpe (o "peso" do impacto)."""
        self.camera.shake(3 if amount < 20 else 6)
        self.hit_pause(min(8, 2 + amount // 6))

    def opponents_of(self, fighter):
        return [f for f in self.fighters if hostile(fighter, f)]

    @staticmethod
    def hostile(a, b):
        return hostile(a, b)

    def _update_bullets(self):
        """Move os tiros e aplica acertos (barreiras, paredes, quem é inimigo de quem)."""
        alive = []
        for b in self.bullets:
            if b.alive:
                b.update(self)
            if b.alive and not (b.ghost or b.lobbed):
                wall = next((w for w in self.arena.walls if w.rect.colliderect(b.rect)), None)
                if wall is not None:
                    b.alive = b.on_wall(wall, self)
            if b.alive and not b.lobbed:
                for e in self.effects:
                    if isinstance(e, Barrier) and hostile(e.owner, b.owner) and e.rect.colliderect(b.rect):
                        b.alive = False
                        self.burst(b.x, b.y, (150, 226, 240), 4, speed=2)
                        break
            if b.alive:
                for f in self.fighters:
                    if f in b.hit or not hostile(b.owner, f) or not f.alive_in_match or f.dash_timer > 0:
                        continue
                    if not b.can_hit(f):
                        continue
                    if math.hypot(f.x - b.x, f.y - 6 - b.y) < f.radius + b.radius + 4:
                        b.hit.add(f)
                        b.alive = b.survives_hit()      # atravessa (lança, flecha tensa, melhoria)?
                        if not b.explosive:
                            if f.invulnerable_timer > 0:
                                self.popup(f.x, f.y - 46, "IMUNE", theme.BRASS)
                            if f.take_damage(b.damage, b.x, b.y, attacker=b.owner, match=self):
                                b.on_hit(f, self)
                        break
            if not b.alive and b.explosive:
                self.effects.append(Explosion(b.owner, b.x, b.y, b.damage,
                                              getattr(b, "blast", config.EXPLOSION_RADIUS)))
                self.assets.play("explosion", 0.45)
                self.camera.shake(5)
            if b.alive:
                alive.append(b)
        self.bullets = alive

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
        self._emit_smoke()
        self.particles = [p for p in self.particles if p.update()]
        self.popups = [p for p in self.popups if p.update()]
        self.camera.focus(self.focus_points(), instant=self.frame == 1)

    def focus_points(self):
        return [(f.x, f.y - 20) for f in self.fighters]

    def _emit_smoke(self):
        """Fumaça escura subindo de quem tem aura sombria (almas corrompidas, Aryel Corrompido)."""
        if self.frame % 3:
            return
        from .enemies import SMOKE
        for f in self.fighters:
            if f.aura is None or not f.alive_in_match:
                continue
            s = f.draw_scale
            x = f.x + random.uniform(-12, 12) * s
            y = f.y + 18 - random.uniform(0, 46) * s - f.lift
            self.particles.append(Particle(x, y, random.uniform(-0.3, 0.3), random.uniform(-1.1, -0.4),
                                           random.choice(SMOKE), random.randint(24, 44), round(4 * s), -0.01))

    def publish_ammo(self):
        """Manda a munição de cada jogador humano para o celular dele (de tempos em tempos)."""
        if self.frame % 6:
            return
        for f in self.fighters:
            if f.is_cpu or not f.slot:
                continue
            mag = f.mag if not f.weapon.is_melee else 0
            hub.publish_slot(f.slot, ammo=f.ammo, mag=mag, reload=f.reload_ratio if f.reloading else 0.0)

    def next_scene(self):
        """Tela depois do fim da partida (None = tela de resultado padrão)."""
        return None

    def restart_scene(self):
        """Tela ao escolher REINICIAR na pausa (None = começar a mesma partida de novo)."""
        return None

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
        self.draw_over_walls(view, cam)
        self.arena.draw_ambience(view, cam, self.frame, "ground")
        for effect in self.effects:
            effect.draw(view, cam)
        for entity in sorted(self.world_entities(), key=lambda e: getattr(e, "sort_y", e.y)):
            entity.draw(view, cam)
        for b in self.bullets:
            b.draw(view, cam)
        for effect in self.effects:
            if hasattr(effect, "draw_over"):
                effect.draw_over(view, cam)         # por cima de todo mundo (bilhete da aposta)
        for p in self.particles:
            p.draw(view, cam)
        self.arena.draw_ambience(view, cam, self.frame, "air")
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

    def draw_over_walls(self, view, cam):
        """Coisas no chão que ficam por cima das paredes e por baixo dos lutadores (entradas, portal)."""

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
    """Duelo em melhor de 3 rounds, com relógio e itens aparecendo na arena.

    Cada "lado" disputa os rounds: no 1 x 1 o lado é o próprio lutador; no 2 x 2
    (TeamBattleMatch) é o time."""

    def __init__(self, game, session):
        super().__init__(game, session, session.map_key)
        self._create_fighters(session)
        self.starts = {f: (f.x, f.y, f.facing) for f in self.fighters}
        self.wins = {side: 0 for side in self.sides()}
        self.round_no = 1
        self.rounds_played = 0
        self.pickups = []
        self.loser = None
        self._start_round()

    def _create_fighters(self, session):
        spawns = self.arena.cfg.spawns
        for setup, pos in zip(session.slots, spawns):
            self._add_player(setup, pos)

    def _add_player(self, setup, pos, team=None, color=None):
        fighter = self._add_fighter(setup, pos, team=team, color=color)
        fighter.full_name = setup.name
        if setup.cpu:
            self.controllers[fighter] = FighterAI(self.session.difficulty)
        else:
            self.game.inputs[setup.slot].set_layout("battle")
            self.controllers[fighter] = self.game.inputs[setup.slot]
        return fighter

    # ── lados (quem disputa os rounds) ───────
    def sides(self):
        return list(self.fighters)

    def members(self, side):
        return [side]

    def side_of(self, fighter):
        return fighter

    def side_name(self, side):
        return side.full_name

    def side_color(self, side):
        return side.color

    def _side_health(self, side):
        team = self.members(side)
        return sum(max(0, f.hp) for f in team) / max(1, sum(f.max_hp for f in team))

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
        """Adversário em pé mais "à mão": o mais perto, com preferência para quem está na direção em que
        o jogador está indo (no 2 x 2 dá para escolher em quem atirar só apontando)."""
        foes = [f for f in self.fighters if f.alive_in_match and hostile(fighter, f)]
        if len(foes) <= 1:
            return foes[0] if foes else None
        ax, ay = fighter.input if math.hypot(*fighter.input) > 0.3 else fighter.facing

        def score(f):
            d = fighter.distance_to(f) or 1.0
            along = ((f.x - fighter.x) * ax + (f.y - fighter.y) * ay) / d
            return d * (1.6 - 0.6 * along)
        return min(foes, key=score)

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
        self._update_downed(active)
        self.publish_ammo()
        if not active:
            return
        down = [s for s in self.sides() if not any(f.alive_in_match for f in self.members(s))]
        if down:
            standing = [s for s in self.sides() if s not in down]
            fallen = [f for s in down for f in self.members(s)]
            self.loser = min(fallen, key=lambda f: f.down_age)       # quem caiu por último
            self._end_round(standing[0] if len(standing) == 1 else None, "ko")
            return
        self.time_left -= 1
        if self.time_left <= 0:
            health = {s: self._side_health(s) for s in self.sides()}
            best = max(health.values())
            leaders = [s for s, h in health.items() if h == best]
            self._end_round(leaders[0] if len(leaders) == 1 else None, "time")

    def _update_downed(self, active):
        """Só o 2 x 2 tem companheiro para levantar quem caiu."""

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
        sub = f"{self.side_name(winner)} VENCE O ROUND" if winner is not None else "EMPATE"
        self.round_banner = (title, sub, self.side_color(winner) if winner is not None else theme.BONE)
        if self._decided():
            self.assets.stop_music(1500)
            champion = max(self.sides(), key=lambda s: self.wins[s])
            human_won = any(not f.is_cpu for f in self.members(champion))
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
            if len(self.pickups) < self.pickup_max:
                self._spawn_pickup()

    @property
    def pickup_max(self):
        return config.PICKUP_MAX

    def _spawn_pickup(self):
        for _ in range(20):
            x, y = self.arena.random_free_spot(16)
            if all(math.hypot(f.x - x, f.y - y) > 160 for f in self.fighters):
                break
        kind = random.choices(("vida", "furia", "energia", "municao"), weights=(36, 22, 18, 24))[0]
        self.pickups.append(Pickup(kind, x, y))
        self.burst(x, y - 10, Pickup.KINDS[kind][1], 10, speed=2)

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


REVIVE_FRAMES = 150         # 2 x 2: tempo perto de um companheiro caído para levantá-lo
REVIVE_RADIUS = 52
REVIVE_HP = 0.35            # volta com essa parte da vida
REVIVES_PER_ROUND = 1       # cada lutador pode ser levantado uma vez por round
TEAM_SPREAD = 110           # distância entre os dois do mesmo time na largada


class TeamBattleMatch(BattleMatch):
    """Duelo 2 x 2: dois times, sem fogo amigo. O round acaba quando o time inteiro cai,
    e dá para levantar o companheiro caído ficando perto dele."""

    min_zoom = 0.6

    def _create_fighters(self, session):
        spawns = self.arena.cfg.spawns
        for setup in session.slots:
            team = session.team_of(setup.slot)
            k = session.teammates(team).index(setup.slot)
            bx, by = spawns[team]
            pos = (bx, by + (k * 2 - 1) * TEAM_SPREAD)
            color = theme.TEAM_COLORS[team] if setup.cpu else None
            fighter = self._add_player(setup, pos, team=team, color=color)
            fighter.ring_color = theme.TEAM_COLORS[team]
            fighter.facing = (1.0, 0.0) if team == 0 else (-1.0, 0.0)
        self.revive_progress = {f: 0.0 for f in self.fighters}
        self.revives = {f: 0 for f in self.fighters}

    def sides(self):
        return [0, 1]

    def members(self, side):
        return [f for f in self.fighters if f.team == side]

    def side_of(self, fighter):
        return fighter.team

    def side_name(self, side):
        return f"TIME {theme.TEAM_NAMES[side]}"

    def side_color(self, side):
        return theme.TEAM_COLORS[side]

    @property
    def pickup_max(self):
        return config.PICKUP_MAX + 1          # mais gente na arena, um item a mais

    def _start_round(self):
        super()._start_round()
        for f in self.fighters:
            self.revive_progress[f] = 0.0
            self.revives[f] = 0

    def focus_points(self):
        # quem caiu há um tempo sai do enquadramento (a câmera fica em quem ainda luta)
        pts = [(f.x, f.y - 20) for f in self.fighters if f.alive_in_match or f.down_age < 90]
        return pts or super().focus_points()

    # ── levantar o companheiro ───────────────
    def can_revive(self, f):
        return (not f.alive_in_match and self.revives[f] < REVIVES_PER_ROUND
                and any(m.alive_in_match for m in self.members(f.team)))

    def _update_downed(self, active):
        for f in self.fighters:
            if not active or not self.can_revive(f):
                self.revive_progress[f] = 0.0
                continue
            helpers = [m for m in self.members(f.team)
                       if m is not f and m.alive_in_match and m.distance_to(f) < REVIVE_RADIUS]
            prog = self.revive_progress[f]
            if helpers:
                prog += 1 / REVIVE_FRAMES
                if self.frame % 6 == 0:
                    self.burst(f.x, f.y, theme.TEAM_COLORS[f.team], 1, speed=2)
            else:
                prog = max(0.0, prog - 1 / 200)
            self.revive_progress[f] = prog
            if prog >= 1:
                self._revive(f)

    def _revive(self, f):
        f.hp = max(1, round(f.max_hp * REVIVE_HP))
        f.invulnerable_timer = 90
        f.stun_timer = 0
        f.vx = f.vy = 0.0
        f.down_age = 0
        self.revives[f] += 1
        self.revive_progress[f] = 0.0
        self.burst(f.x, f.y - 16, theme.TEAM_COLORS[f.team], 22, speed=5)
        self.popup(f.x, f.y - 70, "DE PÉ!", theme.MOSS)
        self.assets.play("select", 0.5)

    def _finish(self):
        w0, w1 = self.wins[0], self.wins[1]
        if w0 == w1:
            winners, title, color = [], "EMPATE", theme.BONE
        else:
            team = 0 if w0 > w1 else 1
            winners = self.members(team)
            title, color = f"TIME {theme.TEAM_NAMES[team]} VENCEU", theme.TEAM_COLORS[team]
        seconds = self.frame // config.FPS
        lines = [("ROUNDS", f"{w0} x {w1}"), ("TEMPO TOTAL", f"{seconds // 60}:{seconds % 60:02d}")]
        for f in sorted(self.fighters, key=lambda f: (f.team, f.slot)):
            lines.append((f"{f.label} DANO · ABATES", f"{f.damage_dealt} · {f.kills}"))
        self.result = Result(title, color, winners, lines, score=(w0, w1))
        self.finished = True

    # ── desenho ──────────────────────────────
    def draw_under(self, view, cam):
        for f in self.fighters:
            if not self.can_revive(f) or not self.active:
                continue
            # anel de "levante seu companheiro" na cor do time
            color = theme.TEAM_COLORS[f.team]
            sx, sy = round(f.x - cam.x), round(f.y + 14 - cam.y)
            ring = pygame.Rect(0, 0, REVIVE_RADIUS * 2, REVIVE_RADIUS)
            ring.center = (sx, sy)
            pulse = 120 + round(60 * math.sin(self.frame * 0.15))
            layer = pygame.Surface(ring.inflate(8, 8).size, pygame.SRCALPHA)
            inner = pygame.Rect(4, 4, ring.w, ring.h)
            pygame.draw.ellipse(layer, (*color, pulse // 3), inner)
            pygame.draw.ellipse(layer, (*color, pulse), inner, 2)
            prog = self.revive_progress.get(f, 0.0)
            if prog > 0:
                pygame.draw.arc(layer, (*theme.BONE, 255), inner, math.pi / 2, math.pi / 2 + math.tau * prog, 4)
            view.blit(layer, ring.inflate(8, 8).topleft)

    def draw(self, screen, ui):
        Match.draw(self, screen, ui)
        cam = self.camera
        if (self.frame // 20) % 2:
            for f in self.fighters:
                if self.can_revive(f) and self.active:
                    sx, sy = cam.to_screen(f.x, f.y - 34)
                    ui.text(screen, "LEVANTE!", theme.XS, theme.TEAM_COLORS[f.team], (round(sx), round(sy)))
        hud.draw_round_banner(screen, ui, self)

    def draw_hud(self, screen, ui):
        hud.draw_team_battle(screen, ui, self)

    def hud_regions(self):
        W, half = config.SCREEN_W, 52
        return [pygame.Rect(0, 0, W // 2 - half, 96), pygame.Rect(W // 2 - half, 0, half * 2, 96),
                pygame.Rect(W // 2 + half, 0, W // 2 - half, 96)]


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
        self.hook_timer = 0         # puxada pelo gancho do Pirata: ele domina na chegada
        self.hook_owner = None
        self.receiver = None        # lançamento: o companheiro que vai receber domina mesmo a bola rápida
        self.receiver_timer = 0
        self.thunder_timer = 0      # chute trovão: quase não perde força e derruba quem entra na frente
        self.thunder_owner = None
        self.thunder_hit = set()    # quem o trovão já derrubou (um tombo por chute)
        self.z = 0.0                # altura
        self.vz = 0.0
        self.squash = 0
        self.held = False           # nas mãos (enterrada): desenha no tamanho normal

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

    def descending_point(self, h):
        """Onde a bola vai estar quando descer até a altura h (para cabecear), e em quantos quadros."""
        x, y, z, vx, vy, vz = self.x, self.y, self.z, self.vx, self.vy, self.vz
        for t in range(1, 150):
            vz -= config.GRAVITY
            z += vz
            vx *= 0.996
            vy *= 0.996
            x += vx
            y += vy
            if (vz < 0 and z <= h) or z <= 0:
                return x, y, t
        return x, y, 150

    def update(self, match):
        if self.z > 0 or self.vz > 0:
            self.vz -= config.GRAVITY
            self.z += self.vz
            if self.z <= 0:
                self.z = 0.0
                if self.vz < -1.4:
                    # quique: perde força a cada toque no chão
                    self.vz = -self.vz * config.BOUNCE
                    self.vx *= config.BOUNCE_ROLL
                    self.vy *= config.BOUNCE_ROLL
                    self.squash = 4
                    match.ball_bounced(self)
                else:
                    self.vz = 0.0
        friction = 0.996 if self.airborne else config.BALL_FRICTION
        if self.thunder_timer > 0:
            friction = 0.998
        if self.squash:
            self.squash -= 1
        self.vx *= friction
        self.vy *= friction
        if abs(self.vx) < 0.05:
            self.vx = 0.0
        if abs(self.vy) < 0.05:
            self.vy = 0.0
        speed = math.hypot(self.vx, self.vy)
        limit = config.BALL_AIR_MAX_SPEED if self.airborne else config.BALL_MAX_SPEED
        if self.thunder_timer > 0:
            limit = config.THUNDER_SPEED
        if speed > limit:
            self.vx *= limit / speed
            self.vy *= limit / speed
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
        if self.hook_timer > 0:
            self.hook_timer -= 1
            if self.hook_timer == 0:
                self.hook_owner = None
        if self.receiver_timer > 0:
            self.receiver_timer -= 1
            if self.receiver_timer == 0:
                self.receiver = None
        if self.thunder_timer > 0:
            self.thunder_timer -= 1
            if self.thunder_timer == 0:
                self.thunder_owner = None
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
        r = self.radius if self.held else round(self.radius * (1 + self.z / 220))
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
        if self.thunder_timer > 0:
            pygame.draw.circle(surf, (255, 236, 120), (sx, sy), r + 3, 2)


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
    min_zoom = 0.5            # bem de longe a arte fica no tamanho original (pixel por pixel)
    GOAL_TOP, GOAL_BOTTOM = Pitch.GOAL_TOP, Pitch.GOAL_BOTTOM
    # zonas do jogo, medidas a partir da linha do gol
    HEADER_RANGE = 460        # cabeçada mais perto do gol que isso vai para o gol (por baixo do travessão)
    CROSS_DEPTH = Pitch.AREA_DEPTH + 130          # zona de quem recebe o cruzamento
    CROSS_HALF = Pitch.AREA_HALF - 40

    def __init__(self, game, session):
        super().__init__(game, session, SOCCER_MAP)
        spawns = self.arena.cfg.spawns
        self.spawn_of = {}
        for setup in session.slots:
            team = session.team_of(setup.slot)
            k = session.teammates(team).index(setup.slot)
            pos = spawns[team + 2 * k]           # time 0 à esquerda (0 e 2), time 1 à direita (1 e 3)
            fighter = self._add_fighter(setup, pos, team=team, color=theme.TEAM_COLORS[team] if setup.cpu else None)
            fighter.ring_color = theme.TEAM_COLORS[team]
            fighter.sprites = self.assets.kit_sprites(fighter.stats.key, team)    # uniforme do time
            fighter.kit = team
            fighter.armed = False
            fighter.power = create_power(fighter.stats)
            self.spawn_of[fighter] = pos
            if setup.cpu:
                self.controllers[fighter] = SoccerAI()
            else:
                game.inputs[setup.slot].set_layout("soccer")      # CORRER e MARCAR no teclado
                self.controllers[fighter] = game.inputs[setup.slot]
        self.ball = Ball(self.arena.width / 2, self.arena.height / 2)
        depth = Pitch.EDGE - 2
        self.goals = [Goal(2, self.GOAL_TOP, depth, Pitch.GOAL, 0),
                      Goal(Pitch.W - Pitch.EDGE, self.GOAL_TOP, depth, Pitch.GOAL, 1)]
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
        self.dunk = None            # enterrada do Cauanzera em andamento (ela segura a bola)
        self.assist = ASSIST_LEVELS.get(getattr(session, "assist", "media"), ASSIST_LEVELS["media"])

    @staticmethod
    def goal_x(team):
        """Linha do gol que o time defende."""
        return Pitch.goal_x(team)

    def focus_points(self):
        """A bola fica sempre na tela; entra junto quem couber no zoom mais afastado
        (as pessoas antes da CPU, os mais perto da bola primeiro). Quem ficou de fora
        ganha uma setinha na borda da tela."""
        ball = self.ball
        bx, by = ball.x, ball.y - ball.z
        pts = [(bx, by)]
        cam = self.camera
        max_w = config.SCREEN_W / cam.min_zoom - cam.margin * 2
        max_h = config.SCREEN_H / cam.min_zoom - cam.margin * 2
        lo_x = hi_x = bx
        lo_y = hi_y = by
        for f in sorted(self.fighters, key=lambda f: (f.is_cpu, f.distance_to(ball))):
            x, y = f.x, f.y - 20
            nlx, nhx, nly, nhy = min(lo_x, x), max(hi_x, x), min(lo_y, y), max(hi_y, y)
            if nhx - nlx <= max_w and nhy - nly <= max_h:
                lo_x, hi_x, lo_y, hi_y = nlx, nhx, nly, nhy
                pts.append((x, y))
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
        if f.power is not None:
            hi += f.power.head_reach                # Trovão: alcança bola mais alta
        return lo <= self.ball.z <= hi and self.touching(f, 10, max_z=hi)

    def header(self, f, direction=None):
        """Cabeçada: desvia a bola alta na direção em que o jogador olha."""
        if self.freeze or f.busy or f.kick_cd > 0 or not self.can_head(f):
            return False
        self._release(f, 8)
        if direction is None and self.in_own_half(f):
            direction = self.clearance_dir(f)      # cabeçada no próprio campo: afasta
        elif direction is None and self.assist.shot_cone > 0 and abs(self.goal_x(1 - f.team) - f.x) < self.HEADER_RANGE:
            # cabeçada na área adversária (cruzamento): vai para o gol, no canto mais longe
            gx = self.goal_x(1 - f.team)
            far = self.GOAL_BOTTOM - 22 if f.y < self.arena.height / 2 else self.GOAL_TOP + 22
            direction = unit(gx - self.ball.x, far - self.ball.y)
        dx, dy = direction or f.facing
        ball = self.ball
        force = 8 * (f.power.head_power if f.power is not None else 1.0)
        ball.vx, ball.vy = dx * force, dy * force
        gx = self.goal_x(1 - f.team)
        if abs(gx - f.x) < self.HEADER_RANGE and (gx - f.x) * dx > 0:
            ball.vz = -0.5          # cabeçada para o gol: para baixo, por baixo do travessão
        else:
            ball.lift(2.5)
        ball.homing_timer = 0
        f.kick_cd = 14
        self.last_touch = f
        self.popup(f.x, f.y - 74, "CABEÇA", theme.BONE)
        self.assets.play("hit", 0.35)
        return True

    def _release(self, f, frames=config.NO_TRAP_FRAMES, keep_receiver=False):
        """O jogador soltou a bola (chute, passe, poder): não a domina de novo na hora."""
        if self.possessor is f:
            self.possessor = None
        if frames > 0:
            self.no_trap[f] = frames
        self.contest.clear()
        if not keep_receiver:
            self.ball.receiver, self.ball.receiver_timer = None, 0

    def kick(self, f, direction=None, loft=0.0, assist=False):
        """Chute rasteiro (loft=0) ou pelo alto (loft de 0 a 1 = força e altura).
        Com assist, um chute que sairia um pouco para fora é corrigido para o gol."""
        if self.freeze or f.kick_cd > 0 or f.busy:
            return False
        if self.can_head(f):
            return self.header(f, direction)
        if not self.touching(f):
            return False
        self._release(f)
        dx, dy = direction or f.facing
        ball = self.ball
        if assist:
            dx, dy = shot_assist(ball.x, ball.y, (dx, dy), self.goal_x(1 - f.team),
                                 self.GOAL_TOP, self.GOAL_BOTTOM, self.assist.shot_cone)
            f.facing = (dx, dy)
        if loft > 0:
            power = config.LOFT_KICK_POWER[0] + (config.LOFT_KICK_POWER[1] - config.LOFT_KICK_POWER[0]) * loft
            ball.lift(5 + 4 * loft)
        else:
            power = config.KICK_POWER
            if f.power is not None and f.power.finisher and self.in_cross_zone(f.team, f.x, f.y):
                # Matador na área: o chute vai no gol (com ou sem assistência) e sai mais forte
                dx, dy = shot_assist(ball.x, ball.y, (dx, dy), self.goal_x(1 - f.team),
                                     self.GOAL_TOP, self.GOAL_BOTTOM, config.FINISHER_CONE)
                f.facing = (dx, dy)
                power *= config.FINISHER_POWER
        ball.vx, ball.vy = dx * power, dy * power
        ball.homing_timer = 0
        f.kick_cd = 14
        self.last_touch = f
        self.assets.play("shoot", 0.3)
        return True

    # ── marcar ───────────────────────────────
    def goal_center(self, team):
        return self.goal_x(team), (self.GOAL_TOP + self.GOAL_BOTTOM) / 2

    def mark_target(self, f):
        """Para onde MARCAR leva o jogador (None = deixa o jogador se mexer sozinho).

        - bola perto do meu gol: posição de goleiro, na linha entre a bola e o centro do gol;
        - adversário com a bola: na frente dele, entre ele e o meu gol;
        - bola solta: vai até onde a bola vai estar;
        - no 2x2, se um companheiro já está mais perto da bola, eu cubro o espaço atrás dele.
        """
        ball = self.ball
        owner = self.possessor
        if owner is not None and owner.team == f.team:
            return None
        gx, gy = self.goal_center(f.team)
        bx, by = ball.x, ball.y
        if ball.airborne:
            bx, by, _ = ball.landing()
        to_goal = math.hypot(bx - gx, by - gy)
        if to_goal < config.GOALKEEPER_ZONE:
            ux, uy = unit(bx - gx, by - gy)
            depth = max(40.0, min(110.0, to_goal * 0.35))
            return gx + ux * depth, gy + uy * depth
        mates = [m for m in self.mates_of(f) if m.distance_to(ball) < f.distance_to(ball)]
        if mates:
            # cobertura: meio do caminho entre a bola e o meu gol
            return (bx + gx) / 2, (by + gy) / 2
        if owner is not None:
            # fecha o caminho do gol a um passo de distância (encostar e roubar é com o jogador)
            ux, uy = unit(gx - owner.x, gy - owner.y)
            return owner.x + ux * 66, owner.y + uy * 66
        # bola solta: antecipa a posição dela
        speed = max(1.0, f.max_speed)
        lead = min(30.0, f.distance_to(ball) / speed)
        return bx + ball.vx * lead * 0.8, by + ball.vy * lead * 0.8

    def mark_steer(self, f, stick):
        """Direção (com intensidade) do MARCAR, corrigida pelo analógico do jogador."""
        target = self.mark_target(f)
        if target is None:
            return None
        dx, dy = target[0] - f.x, target[1] - f.y
        dist = math.hypot(dx, dy)
        if dist < 6:
            ax, ay = 0.0, 0.0
        else:
            ux, uy = dx / dist, dy / dist
            power = min(1.0, dist / 40) * (1.0 if f.sprint_held else config.MARK_SPEED)
            ax, ay = ux * power, uy * power
        sx, sy = stick
        if math.hypot(sx, sy) > 0.2:
            ax, ay = ax * 0.5 + sx * 0.5, ay * 0.5 + sy * 0.5     # o jogador ainda corrige
        return ax, ay

    # ── defesa ───────────────────────────────
    def in_own_half(self, f):
        return abs(f.x - self.goal_x(f.team)) < self.arena.width / 2

    def clearance_dir(self, f, stick=None):
        """Para onde vai o chutão: para frente e para a lateral, nunca para o próprio gol."""
        fwd = 1.0 if f.team == 0 else -1.0
        if stick is not None and math.hypot(*stick) > 0.3:
            sx, sy = unit(*stick)
            if sx * fwd > 0.2:
                return sx, sy                       # o jogador escolheu uma direção para frente
        side = 1.0 if self.ball.y >= self.arena.height / 2 else -1.0
        return unit(fwd, side * 0.65)

    def can_clear(self, f):
        return self.possessor is None and self.in_own_half(f)

    def clear_ball(self, f, direction=None):
        """Chutão: tira a bola de perto do próprio gol, pelo alto, com alcance maior que o chute."""
        if self.freeze or f.kick_cd > 0 or f.busy or not self.can_clear(f):
            return False
        if not self.touching(f, config.CLEAR_REACH, max_z=config.HEAD_RANGE[1]):
            return False
        self._release(f, 16)
        dx, dy = direction or self.clearance_dir(f)
        ball = self.ball
        ball.vx, ball.vy = dx * config.CLEAR_POWER, dy * config.CLEAR_POWER
        ball.lift(config.CLEAR_LIFT)
        ball.homing_timer = 0
        f.facing = (dx, dy)
        f.kick_cd = 14
        self.last_touch = f
        self.popup(f.x, f.y - 74, "AFASTOU", theme.BONE)
        self.burst(ball.x, ball.y, (236, 230, 220), 6, speed=3)
        self.camera.shake(2)
        self.assets.play("shoot", 0.35)
        return True

    def incoming(self, f, horizon=24, reach=120):
        """A bola (solta e rápida) vem na direção deste jogador? Devolve (quadros, ponto) ou None."""
        ball = self.ball
        if self.possessor is not None or ball.z > config.BODY_HEIGHT + 10:
            return None
        if math.hypot(ball.vx, ball.vy) < 5:
            return None
        t, d = closest_approach(ball.x, ball.y, ball.vx, ball.vy, f.x, f.y, horizon)
        if t <= 0 or d > reach:
            return None
        return t, (ball.x + ball.vx * t, ball.y + ball.vy * t)

    def block_dive(self, f):
        """Carrinho de bloqueio: mergulha no caminho da bola e estica o alcance do corpo."""
        hit = self.incoming(f)
        if hit is None or f.block_timer > 0:
            return False
        arrival, (px, py) = hit
        dx, dy = unit(px - f.x, py - f.y)
        if (dx, dy) == (0.0, 0.0):
            dx, dy = unit(-self.ball.vy, self.ball.vx)
        if not f.dash((dx, dy), frames=7, cooldown=50):
            return False
        # dura até a bola chegar (com folga), mas nunca mais que o dobro do normal
        f.block_timer = int(min(config.BLOCK_FRAMES * 2, max(config.BLOCK_FRAMES, arrival + 6)))
        f.block_hit = False
        self.assets.play("dash", 0.35)
        self.dust(f.x, f.y + 20, 6)
        return True

    def _thunder_hit(self, f):
        """O chute trovão passou por alguém: derruba (uma vez por chute) e perde um pouco de força."""
        ball = self.ball
        if f in ball.thunder_hit:
            return
        ball.thunder_hit.add(f)
        ball.vx *= 0.85
        ball.vy *= 0.85
        ux, uy = unit(ball.vx, ball.vy)
        if f.stun(50):
            f.knock = [ux * 7, uy * 7]
            self.popup(f.x, f.y - 74, "DERRUBADO", theme.BONE)
        self.burst(f.x, f.y - 10, (255, 236, 120), 12, speed=5)
        self.camera.shake(4)
        self.assets.play("hit", 0.5)

    def _nose_pull(self):
        """Faro de gol (Matador): a bola solta perto dele faz a curva e vem para o pé."""
        ball = self.ball
        for f in self.fighters:
            if f.nose_timer <= 0 or not self._can_touch(f):
                continue
            d = f.distance_to(ball)
            if 20 < d < config.NOSE_RANGE:
                ux, uy = unit(f.x - ball.x, f.y - ball.y)
                ball.vx += ux * config.NOSE_PULL
                ball.vy += uy * config.NOSE_PULL
                return

    def _body_block(self, f, reach):
        """A bola bateu no corpo de quem não está com ela."""
        ball = self.ball
        ball.receiver, ball.receiver_timer = None, 0          # desviou: o lançamento não chega mais
        dx, dy = ball.x - f.x, ball.y - f.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            nx, ny = unit(-ball.vx, -ball.vy)
            if (nx, ny) == (0.0, 0.0):
                nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / dist, dy / dist
        if dist < reach:
            ball.x, ball.y = f.x + nx * reach, f.y + ny * reach
        speed = math.hypot(ball.vx, ball.vy)
        dot = ball.vx * nx + ball.vy * ny
        if dot < 0 and speed > config.BLOCK_SPEED:
            # bloqueio: a bola perde força e espirra para o lado, não de volta para quem chutou
            vin_x = ball.vx
            tx, ty = -ny, nx
            gx, gy = self.goal_x(f.team), self.arena.height / 2
            if tx * (ball.x - gx) + ty * (ball.y - gy) < 0:
                tx, ty = -tx, -ty
            ox, oy = unit(nx * 0.55 + tx * 0.85, ny * 0.55 + ty * 0.85)
            out = speed * config.BLOCK_DAMP
            ball.vx, ball.vy = ox * out, oy * out
            ball.homing_timer = 0
            f.block_hit = True
            # só avisa quando bloqueou um chute forte indo para o próprio gol, perto dele
            if speed > 8.5 and abs(ball.x - gx) < 650 and (gx - ball.x) * vin_x > 0:
                self.popup(f.x, f.y - 74, "BLOQUEIO", theme.BONE)
                self.camera.shake(3)
            self.burst(ball.x, ball.y, (236, 230, 220), 8, speed=3)
            self.assets.play("hit", 0.4)
        else:
            if dot < 0:
                ball.vx -= 1.6 * dot * nx
                ball.vy -= 1.6 * dot * ny
            ball.vx += nx * 0.8
            ball.vy += ny * 0.8
        self.last_touch = f

    def _exo_block(self, f):
        """O corpo blindado do exoesqueleto segura o chute: a bola morre na frente dele."""
        ball = self.ball
        speed = math.hypot(ball.vx, ball.vy)
        if speed > 3:
            ux, uy = unit(ball.vx, ball.vy)
            ball.vx, ball.vy = ux * 1.5, uy * 1.5
            ball.thunder_timer = 0
            if speed > 8:
                self.popup(f.x, f.y - 74, "BLINDADO", (120, 190, 255))
                self.burst(ball.x, ball.y, (120, 190, 255), 8, speed=3)

    # ── cruzamento ───────────────────────────
    def in_cross_position(self, f):
        """Na ponta, no último terço do campo de ataque."""
        gx = self.goal_x(1 - f.team)
        return (abs(gx - f.x) < (self.arena.width - 80) / 3
                and abs(f.y - self.arena.height / 2) >= config.WING_OFFSET)

    def in_cross_zone(self, team, x, y):
        """Na área adversária ou chegando nela (um pouco antes da linha da área)."""
        gx = self.goal_x(1 - team)
        return 40 < abs(gx - x) < self.CROSS_DEPTH and abs(y - self.arena.height / 2) < self.CROSS_HALF

    def cross_receiver(self, f, mates, aim=None):
        """Companheiro entrando na área para receber o cruzamento (None = não é caso de cruzar)."""
        if not mates or not self.in_cross_position(f):
            return None
        gx = self.goal_x(1 - f.team)
        fwd = 1.0 if gx > f.x else -1.0
        if aim is not None and aim[0] * fwd < -0.3:
            return None                          # apontou para trás: é recuo, não cruzamento
        spot = (gx - fwd * (Pitch.SPOT - 20), self.arena.height / 2)
        best, best_d = None, 1e9
        for m in mates:
            vx, vy = m.x - m.prev_pos[0], m.y - m.prev_pos[1]
            px, py = m.x + vx * 20, m.y + vy * 20
            if self.in_cross_zone(f.team, m.x, m.y) or self.in_cross_zone(f.team, px, py):
                d = math.hypot(px - spot[0], py - spot[1])
                if d < best_d:
                    best, best_d = m, d
        return best

    def _cross(self, f, mate, high):
        """Cruza da ponta para a frente da corrida do companheiro. Alto: chega na altura da
        cabeça. Rasteiro: forte, para finalizar de primeira."""
        ball = self.ball
        gx = self.goal_x(1 - f.team)
        fwd = 1.0 if gx > f.x else -1.0
        mid = self.arena.height / 2
        mvx, mvy = mate.x - mate.prev_pos[0], mate.y - mate.prev_pos[1]
        near_x, far_x = gx - fwd * 60, gx - fwd * 300
        t = 30.0
        for _ in range(3):                       # onde ele vai estar quando a bola chegar
            tx = min(max(mate.x + mvx * t, min(near_x, far_x)), max(near_x, far_x))
            ty = min(max(mate.y + mvy * t, mid - 230), mid + 230)
            dist = math.hypot(tx - ball.x, ty - ball.y)
            t = min(52.0, max(24.0, dist / 9)) if high else min(60.0, max(14.0, dist / config.CROSS_LOW_POWER))
        dx, dy = unit(tx - ball.x, ty - ball.y)
        if high:
            # velocidade para chegar em t quadros (a bola no ar perde 0,4% por quadro)
            frames = int(t)
            reach = sum(0.996 ** k for k in range(1, frames + 1))
            speed = min(config.BALL_MAX_SPEED, dist / reach)
            if speed >= config.BALL_MAX_SPEED:   # longe demais: demora mais para chegar
                covered, frames = 0.0, 0
                while covered < dist and frames < 120:
                    frames += 1
                    covered += speed * 0.996 ** frames
            g = config.GRAVITY
            ball.vx, ball.vy = dx * speed, dy * speed
            ball.vz = (config.CROSS_HEIGHT + g * frames * (frames + 1) / 2) / frames
            ball.z = max(ball.z, 0.1)
            ball.homing_timer = 0
        else:
            ball.vx, ball.vy = dx * config.CROSS_LOW_POWER, dy * config.CROSS_LOW_POWER
            ball.homing_timer = 40
            ball.homing_player = mate
            ball.homing_target = (tx, ty)
            ball.homing_force = 0.12
        f.facing = (dx, dy)
        self.last_touch = f
        self.popup(f.x, f.y - 74, "CRUZAMENTO", theme.BONE)
        self.assets.play("shoot", 0.3)
        return True

    def pass_ball(self, f, high=False, direction=None, power=1.0):
        """Passe. Sem direção: para o companheiro mais perto. Com direção (analógico/setas): para o
        companheiro que estiver para aquele lado, na frente dele se estiver correndo; se ninguém
        estiver para lá, a bola vai para o espaço. Com a assistência desligada, vai reto.
        Passe alto (``high``): lançamento por cima, que alcança o companheiro mesmo do outro lado
        do campo; para o espaço, vai mais longe quanto mais tempo segurou (``power`` de 0 a 1)."""
        if self.freeze or f.busy or not self.touching(f):
            return False
        self._release(f)
        mates = [m for m in self.fighters if m.team == f.team and m is not f]
        ball = self.ball
        cone = self.assist.pass_cone if not f.is_cpu else 180
        aim = unit(*direction) if direction is not None and math.hypot(*direction) > 0.3 else None
        # na ponta, no último terço, com companheiro entrando na área: vira cruzamento
        receiver = self.cross_receiver(f, mates, aim)
        if receiver is not None:
            return self._cross(f, receiver, high)
        if f.is_cpu or (aim is None and cone > 0):
            mate = min(mates, key=f.distance_to) if mates else None
        elif cone > 0:
            mate = pick_receiver(f.x, f.y, aim, mates, cone)
        else:
            mate = None                              # assistência desligada: vai reto
        if mate is None and aim is not None:
            f.facing = aim
        if high:
            # lançamento: calcula o arco para cair no pé do companheiro (na frente da corrida dele)
            if mate is not None:
                mvx, mvy = mate.x - mate.prev_pos[0], mate.y - mate.prev_pos[1]
                tx, ty, frames = mate.x, mate.y, 24
                for _ in range(2):                   # onde ele vai estar quando a bola cair
                    tx, ty = mate.x + mvx * frames, mate.y + mvy * frames
                    _, frames = lob(math.hypot(tx - ball.x, ty - ball.y), t_max=config.LOB_MATE_MAX_FRAMES)
            else:
                lo, hi = config.LOB_SPACE
                reach = lo + (hi - lo) * max(0.0, min(1.0, power))
                tx, ty = f.x + f.facing[0] * reach, f.y + f.facing[1] * reach
            dx, dy = tx - ball.x, ty - ball.y
            dist = math.hypot(dx, dy) or 1
            speed, frames = lob(dist, t_max=config.LOB_MATE_MAX_FRAMES if mate is not None else None)
            f.facing = (dx / dist, dy / dist)
            ball.vx, ball.vy = f.facing[0] * speed, f.facing[1] * speed
            ball.lift(config.GRAVITY * (frames + 1) / 2)    # volta ao chão em `frames` quadros
            ball.homing_timer = 0
            if mate is not None:
                ball.receiver, ball.receiver_timer = mate, frames + 40
        else:
            power = config.PASS_POWER
            if mate is not None:
                # mira um pouco à frente de quem está correndo
                mvx, mvy = mate.x - mate.prev_pos[0], mate.y - mate.prev_pos[1]
                lead = min(20.0, f.distance_to(mate) / config.PASS_POWER * 0.5)
                tx, ty = mate.x + mvx * lead, mate.y + mvy * lead
                f.facing = unit(tx - ball.x, ty - ball.y)
                ball.homing_timer = config.PASS_HOMING_FRAMES
                ball.homing_player = mate
                ball.homing_target = (mate.x, mate.y)
                ball.homing_force = config.PASS_HOMING_FORCE
            else:
                power *= 1.15                         # passe para o espaço vai um pouco mais forte
                ball.homing_timer = 0
            ball.vx, ball.vy = f.facing[0] * power, f.facing[1] * power
        self.last_touch = f
        self.assets.play("shoot", 0.25)
        return True

    def use_power(self, f):
        if self.freeze or self.ending:
            return False
        used = f.power.use(f, self)
        if used and f.power.needs_ball:
            self._release(f, f.power.release_frames, keep_receiver=f.power.keeps_receiver)
        return used

    def cut(self, f, direction=None):
        """Corte: drible lateral rápido. Com a bola vindo solta e rápida: carrinho de bloqueio."""
        if not self.freeze and f is not self.possessor and self.block_dive(f):
            return
        lx, ly = direction or f.facing
        if direction is None:
            lx, ly = -ly, lx
        if not f.dash((lx, ly), frames=6, cooldown=30):
            return
        self.assets.play("dash", 0.3)
        owner = self.possessor
        if (not self.freeze and owner is not None and owner.team != f.team and self.touching(f, 12)
                and not self._shielded(owner)):
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
                self.burst(random.uniform(200, self.arena.width - 200),
                           random.uniform(self.arena.height * 0.1, self.arena.height * 0.45), theme.TEAM_COLORS[team], 6,
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
            f.update_stamina()
            if f.tackle_timer > 0:
                self._tackle(f)
            if f.block_timer > 0:
                f.block_timer -= 1
                if f.block_timer == 0 and not f.block_hit:
                    f.stun(config.BLOCK_MISS_STUN)        # errou o tempo: fica no chão
                    self.dust(f.x, f.y + 20, 5)
        for w in self.ball_walls:
            w.update(self)
        self.ball_walls = [w for w in self.ball_walls if w.alive]

        for i, a in enumerate(self.fighters):
            for b in self.fighters[i + 1:]:
                if a.team != b.team and (a.magic_timer > 0 or b.magic_timer > 0):
                    continue            # drible mágico: passa por dentro do marcador
                if a.team != b.team and (a.exo_timer > 0) != (b.exo_timer > 0):
                    self._exo_bump(a if a.exo_timer > 0 else b, b if a.exo_timer > 0 else a)
                _separate(a, b)
                self.arena.resolve(a)
                self.arena.resolve(b)

        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]

        if not self.freeze and not self.ending:
            self._update_ball()
        elif self.freeze:
            self.freeze -= 1
            if self.freeze == 0:
                self._kickoff()

        self._star_effects()
        self._update_bets()
        for f in self.fighters:
            if not f.is_cpu:
                hub.publish_slot(f.slot, cooldown=f.super_cd / f.power.cooldown,
                                 stamina=f.stamina, tired=f.exhausted)

    def _update_bets(self):
        """Aposta no gol (Aryel): o tempo corre; acabou sem gol = RED (fica sem fôlego)."""
        if self.freeze or self.ending:
            return
        for f in self.fighters:
            if f.bet_timer <= 0:
                continue
            f.bet_timer -= 1
            if self.frame % 6 == 0:
                self.burst(f.x + random.uniform(-10, 10), f.y - 50, (240, 196, 60), 1, speed=1, size=3)
            if f.bet_timer == 0:
                self._lose_bet(f)

    def _lose_bet(self, f):
        f.bet_timer = 0
        f.stamina, f.exhausted = 0.0, True
        self.popup(f.x, f.y - 80, "RED", (230, 80, 70))
        self.assets.play("cancel", 0.4)

    def _exo_bump(self, exo, foe):
        """Exoesqueleto (Borba Jr): quem tromba nele cai."""
        if foe.stunned or exo.distance_to(foe) > exo.radius + foe.radius + 4:
            return
        ux, uy = exo.direction_to(foe)
        if foe.stun(45):
            foe.knock = [ux * 8, uy * 8]
            if self.possessor is foe:
                self._release(foe, 30)
            self.popup(foe.x, foe.y - 74, "CAIU", theme.BONE)
            self.burst(foe.x, foe.y, (200, 208, 222), 8, speed=3)
            self.camera.shake(4)
            self.assets.play("hit", 0.45)

    @staticmethod
    def _shielded(owner):
        """Com a bola protegida: drible mágico (Faísca) ou exoesqueleto (Borba Jr)."""
        return owner is not None and (owner.magic_timer > 0 or owner.exo_timer > 0)

    def _star_effects(self):
        """Brilho dos poderes dos craques: drible mágico (dourado), faro de gol (verde) e o rastro
        do chute trovão."""
        if self.frame % 3 == 0:
            for f in self.fighters:
                if f.magic_timer > 0:
                    self.burst(f.x + random.uniform(-10, 10), f.y - random.uniform(0, 40), (255, 226, 120), 1, speed=1)
                if f.nose_timer > 0:
                    self.burst(f.x + random.uniform(-12, 12), f.y + 18, (150, 236, 150), 1, speed=0.8)
        ball = self.ball
        if ball.thunder_timer > 0:
            self.burst(ball.x, ball.y - ball.z, (255, 236, 120), 2, speed=1.5)
            if self.frame % 2 == 0:
                self.burst(ball.x, ball.y - ball.z, (255, 255, 255), 1, speed=2.5)

    def _tackle(self, f):
        """Carrinho do Guerreiro: derruba adversários e leva a bola."""
        f.tackle_timer -= 1
        for foe in self.foes_of(f):
            if f.distance_to(foe) < f.radius + foe.radius + 8 and not foe.stunned and foe.stun(60):
                self.burst(foe.x, foe.y, (236, 230, 220), 8, speed=3)
                self.camera.shake(5)
                self.assets.play("hit", 0.5)
        if (not self.freeze and self.touching(f, 4) and self.possessor is not f
                and not self._shielded(self.possessor)):
            if self.possessor is not None:
                self._release(self.possessor, 30)
            self._take(f)

    def _human(self, f, inp):
        stick = inp.axis()
        f.sprint_held = inp.held("sprint")
        f.marking = inp.held("mark") and f is not self.possessor
        auto = self.mark_steer(f, stick) if f.marking else None
        if auto is not None:
            f.steer(*auto)
            if math.hypot(*stick) < 0.2:
                f.face(self.ball)          # marcando: de frente para a bola
        else:
            f.steer(*stick)
        # CHUTÃO: no próprio campo, com a bola solta, CHUTE afasta para longe do gol.
        # Vale apertar um pouco antes da bola chegar (janela de alguns quadros).
        if inp.pressed("attack") and self.can_clear(f) and not self.can_head(f):
            f.clear_timer = config.CLEAR_WINDOW
        if f.clear_timer > 0:
            f.clear_timer -= 1
            if self.clear_ball(f, self.clearance_dir(f, inp.axis())):
                f.clear_timer = 0
                f.clear_lock = True
        if f.clear_lock or f.clear_timer > 0:
            f.kick_charge = 0
            if not inp.held("attack"):
                f.clear_lock = False
        # CHUTE: toque = rasteiro; segurar e soltar = pelo alto. Bola na altura da cabeça = cabeçada.
        elif inp.held("attack"):
            f.kick_charge = min(f.kick_charge + 1, config.MAX_CHARGE)
            if self.can_head(f) and f.kick_cd <= 0:
                self.header(f)
                f.kick_charge = 0
        elif f.kick_charge:
            if not any(f.input):
                f.face(self.ball)
            self.kick(f, loft=_loft(f.kick_charge), assist=True)
            f.kick_charge = 0
        # PASSE: mesma ideia
        if inp.held("special"):
            f.pass_charge = min(f.pass_charge + 1, config.MAX_CHARGE)
        elif f.pass_charge:
            self.pass_ball(f, high=f.pass_charge >= config.LOFT_FRAMES, direction=stick,
                           power=_loft(f.pass_charge))
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
            slack = config.LOSE_DISTANCE + (config.SPRINT_CARRY_AHEAD if owner.sprinting else 0)
            if not self._can_touch(owner) or d > owner.radius + ball.radius + slack:
                self.possessor = None
                self.contest.clear()
                return
            if self._shielded(owner):
                self.contest.clear()
                return                      # drible mágico / exoesqueleto: ninguém toma
            glued = owner.power is not None and owner.power.glued_carry
            steal_mult = owner.power.steal_mult if owner.power is not None else 1.0
            # disputa: o adversário que fica mais perto da bola por um tempo toma a posse
            for foe in self.foes_of(owner):
                fd = foe.distance_to(ball)
                if self._can_touch(foe) and fd < foe.radius + ball.radius + 6 and fd < d:
                    # MARCAR ajuda a chegar, mas não rouba sozinho: disputa conta pela metade
                    self.contest[foe] = self.contest.get(foe, 0) + (0.5 if foe.marking else 1)
                    needed = config.SPRINT_STEAL_FRAMES if owner.sprinting and not glued else config.STEAL_FRAMES
                    needed *= steal_mult            # Faísca: bola protegida
                    if self.contest[foe] >= needed:
                        self._take(foe)
                        self.burst(ball.x, ball.y, (236, 230, 220), 6, speed=3)
                        self.assets.play("dash", 0.25)
                        return
                else:
                    self.contest.pop(foe, None)
            return
        # bola sem dono: quem encostar e conseguir dominar fica com ela
        low = self._trappable_height()
        receiver = ball.receiver if ball.receiver_timer > 0 else None
        if not low and not (receiver is not None and ball.z < config.HEAD_RANGE[1]):
            return
        best, best_d = None, 1e9
        pull, pull_d = None, 1e9
        lvl = self.assist
        for f in self.fighters:
            if not self._can_touch(f):
                continue
            if not low and f is not receiver:
                continue        # bola no peito: só quem ia receber o lançamento domina
            d = f.distance_to(ball)
            reach = f.radius + ball.radius + 8
            human = not f.is_cpu
            if d < reach + (lvl.trap_range if human else 0):
                rel = math.hypot(ball.vx - (f.x - f.prev_pos[0]), ball.vy - (f.y - f.prev_pos[1]))
                limit = config.TRAP_SPEED + (3 if ball.airborne else 0) + (lvl.trap_bonus if human else 0)
                hooked = ((ball.hook_timer > 0 and ball.hook_owner is f)
                          or (ball.receiver_timer > 0 and ball.receiver is f)
                          or f.nose_timer > 0)      # faro de gol: domina até bola rápida
                if ball.hook_timer > 0 and not hooked:
                    continue        # só quem puxou com o gancho domina
                if d < reach:
                    if (rel < limit or f.dribbling or hooked) and d < best_d:
                        best, best_d = f, d
                elif human and lvl.trap_pull > 0 and rel < limit and d < pull_d:
                    pull, pull_d = f, d
        if best is not None:
            self._take(best)
        elif pull is not None:
            # domínio assistido: a bola que passa perto do pé é puxada um pouco para ele
            ux, uy = unit(pull.x - ball.x, pull.y - ball.y)
            ball.vx += ux * lvl.trap_pull
            ball.vy += uy * lvl.trap_pull

    def _take(self, f):
        ball = self.ball
        if ball.airborne:
            self.popup(f.x, f.y - 74, "DOMINOU", theme.BONE)
        ball.z = ball.vz = 0.0
        ball.receiver, ball.receiver_timer = None, 0
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
        glued = f.power is not None and f.power.glued_carry
        close = (f.dribbling and not f.sprinting) or glued     # correndo, só o Ginga conduz colado
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
        gain = config.CLOSE_GAIN if close else config.CARRY_GAIN
        if f.sprinting and not glued:
            ahead += config.SPRINT_CARRY_AHEAD       # bola mais solta à frente
            gain *= 0.7
        tx, ty = f.x + f.carry_dir[0] * ahead, f.y + f.carry_dir[1] * ahead
        ball.vx = vx + (tx - ball.x) * gain
        ball.vy = vy + (ty - ball.y) * gain
        self.last_touch = f

    def _update_ball(self):
        ball = self.ball
        if self.dunk is not None:
            return                          # a enterrada leva a bola nas mãos
        self._update_possession()
        for f in self.fighters:
            if f is not self.possessor:
                f.carrying_close = False
        if self.possessor is not None:
            self._carry(self.possessor)
        elif ball.z < 30:
            self._nose_pull()
        x0, y0 = ball.x, ball.y
        ball.update(self)
        _bounce_off_walls(ball, self.arena.walls + self.ball_walls)
        for f in self.fighters:
            if f is self.possessor or (ball.ghost_timer > 0 and f.team != ball.ghost_team):
                continue
            if ball.hook_timer > 0:
                continue        # a bola vem presa à corrente do gancho: não bate em ninguém
            if ball.receiver_timer > 0 and f is ball.receiver:
                continue        # o lançamento é para ele: domina em vez de rebater
            owner = self.possessor
            if owner is not None and owner.magic_timer > 0 and f.team != owner.team:
                continue        # drible mágico: a bola passa pelo marcador como se ele não estivesse lá
            if ball.z > config.BODY_HEIGHT:
                continue        # bola alta passa por cima
            # corpo de quem não está com a bola funciona como obstáculo; o caminho inteiro da
            # bola no quadro é conferido, então chute forte não atravessa ninguém
            reach = ball.radius + f.radius + (config.BLOCK_REACH if f.block_timer > 0 else 0)
            t = segment_contact(x0, y0, ball.x, ball.y, f.x, f.y, reach)
            if t is None:
                continue
            if ball.thunder_timer > 0 and f is not ball.thunder_owner and f.exo_timer <= 0:
                self._thunder_hit(f)            # chute trovão: derruba e segue
                continue
            if t > 0:
                ball.x, ball.y = x0 + (ball.x - x0) * t, y0 + (ball.y - y0) * t
            self._body_block(f, reach)
            if f.exo_timer > 0:
                self._exo_block(f)
            x0, y0 = ball.x, ball.y
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
        if self.GOAL_TOP < ball.y < self.GOAL_BOTTOM and (ball.x < Pitch.EDGE or ball.x > Pitch.W - Pitch.EDGE):
            defending = 0 if ball.x < Pitch.EDGE else 1
            if ball.z > config.CROSSBAR:
                self._over_bar(defending)
            else:
                self._goal(scoring_team=1 - defending)
        if not (-100 < ball.x < self.arena.width + 100 and -100 < ball.y < self.arena.height + 100):
            ball.reset(self.arena.width / 2, self.arena.height / 2)

    def _over_bar(self, defending):
        """Passou por cima do gol: tiro de meta para quem defende."""
        x = Pitch.LINE + 110 if defending == 0 else self.arena.width - Pitch.LINE - 110
        self.popup(self.goal_x(defending), self.arena.height / 2 - 60, "POR CIMA", theme.BONE)
        self.ball.reset(x, self.arena.height / 2)
        self.possessor = None
        self.last_touch = None
        self.assets.play("cancel", 0.3)

    def _goal(self, scoring_team):
        scorer = self.last_touch
        own_goal = scorer is not None and scorer.team != scoring_team
        bettors = [f for f in self.fighters if f.bet_timer > 0]
        won = [f for f in bettors if f.team == scoring_team and not own_goal]
        self.score[scoring_team] += 2 if won else 1          # aposta no gol: GREEN, vale 2
        for f in bettors:
            if f in won:
                f.bet_timer = 0
                self.popup(f.x, f.y - 92, "GREEN! VALE 2", (110, 230, 110))
            else:
                f.bet_timer = 0
                self.popup(f.x, f.y - 80, "RED", (230, 80, 70))
        self.freeze = config.GOAL_FREEZE
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
        self.effects.clear()
        self.dunk = None
        self.possessor = None
        self.no_trap.clear()
        self.contest.clear()
        for f, pos in self.spawn_of.items():
            f.x, f.y = pos
            f.vx = f.vy = 0
            f.knock = [0.0, 0.0]
            f.stun_timer = f.tackle_timer = f.sprint_timer = f.dash_timer = 0
            f.block_timer = f.clear_timer = 0
            f.slow_timer = f.pull_timer = 0
            f.magic_timer = f.nose_timer = 0
            f.hack_timer = f.type_timer = f.rush_timer = f.virus_timer = f.bet_timer = 0
            f.lift = 0
            f.end_exo()
            f.clear_lock = False
            f.stamina, f.exhausted = 1.0, False
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
        for f in self.fighters:
            if f.bet_timer > 0:                    # aposta no gol valendo: contagem em cima dele
                sx, sy = self.camera.to_screen(f.x, f.y - 50 - f.lift)
                secs = f.bet_timer // config.FPS + 1
                color = (240, 196, 60) if secs > 3 or (self.frame // 8) % 2 else (230, 80, 70)
                ui.text(screen, f"APOSTA {secs}s", theme.XS, color, (round(sx), round(sy) - 26))
        self._draw_offscreen(screen, ui)
        if self.goal_banner:
            hud.draw_goal_banner(screen, ui, *self.goal_banner, self.banner_age)

    def _draw_offscreen(self, screen, ui):
        """Campo grande: quem saiu da câmera aparece como uma setinha (cor do time) na borda."""
        W, H = config.SCREEN_W, config.SCREEN_H
        for f in self.fighters:
            sx, sy = self.camera.to_screen(f.x, f.y - 20)
            if 0 <= sx <= W and 0 <= sy <= H:
                continue
            ax, ay, ux, uy = hud.edge_arrow(screen, sx, sy, theme.TEAM_COLORS[f.team], 8, top=96, bottom_gap=60)
            ui.text(screen, f.label, theme.XS, f.color, (round(ax - ux * 14), round(ay - uy * 12)))

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


def lob(dist, max_speed=None, t_min=22, t_max=None):
    """Bola alta que cai a ``dist`` pixels: (velocidade, quadros no ar). No ar ela perde 0,4% por
    quadro. Longe demais para a velocidade máxima: fica mais tempo no ar (até t_max) e cai antes."""
    max_speed = max_speed or config.BALL_AIR_MAX_SPEED
    t_max = t_max or config.LOB_MAX_FRAMES
    frames = int(max(t_min, min(t_max, dist / 9)))
    reach = sum(0.996 ** k for k in range(1, frames + 1))
    speed = dist / reach
    if speed > max_speed:
        speed, covered, frames = max_speed, 0.0, 0
        while covered < dist and frames < t_max:
            frames += 1
            covered += speed * 0.996 ** frames
    return speed, frames


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
    if session.soccer:
        return SoccerMatch(game, session)
    return TeamBattleMatch(game, session) if session.team_mode else BattleMatch(game, session)
