"""Modo basquete: 2 x 2 no estilo NBA Jam (quadra, cestas, bola e a partida).

A quadra tem as medidas de arena.Court nas três versões (ginásio, rua e Arena Soul). A cesta é
desenhada em duas camadas: a de trás (poste, tabela, rede de trás) entra na ordem dos jogadores, e
a da frente (aro e rede da frente) passa por cima da bola, que assim aparece entrando na rede.
"""
import math
import random

import pygame

from . import config, hud, theme
from .ai import BasketballAI
from .arena import BASKET_MAPS, Court
from .basket_assist import (JUMP_FRAMES, aim_point, board_hit, bounce, flight_frames, green_half, miss_distance,
                            rim_contact, shot_error, shot_velocity, steal_chance, through_hoop)
from .entities import Entity
from .matches import Match, Result, _bounce_off_walls, _separate
from .net.remote import hub
from .soccer_assist import pick_receiver, unit

HALF_SECONDS = 120              # dois tempos de 2 minutos
SHOT_CLOCK = 10                 # segundos com a bola sem arremessar: perde a posse
CATCH_HEIGHT = 56               # bola mais baixa que isso pode ser pega
HAND_Z = 40                     # altura de onde sai o arremesso
PASS_SPEED = 11.0
DUNK_RANGE = 280                # dentro do garrafão e até tão longe do aro: enterrada automática
DUNK_REACH = 36                 # de onde a mão solta a bola na enterrada (do centro do aro)
RIM_KEEP = 0.55                 # quanto da força sobra quando a bola bate no aro
BOARD_KEEP = 0.6                # e na tabela
FLOOR_BOUNCE = 0.72             # a bola de basquete quica bem mais que a de futebol
JUMP_H = 34                     # altura do pulo (arremesso, toco e rebote)
BLOCK_REACH = 16                # alcance do braço no toco, além do corpo
STEAL_REACH = 14                # o roubo pega encostando (folga além dos corpos)
STEAL_COOLDOWN = 36
FEINT_FRAMES = 20               # quem tenta roubar nesse tempo erra e fica parado
FEINT_STUN = 30                 # 0,5 s parado
FIRE_STREAK = 3                 # cestas seguidas do mesmo jogador para pegar fogo
FIRE_SECONDS = 20
REBOUND_PULL = 0.12             # a bola que bateu no aro é puxada para o mais perto
BALL_COLOR = (226, 112, 36)
SEAM_COLOR = (60, 24, 8)


class BasketBall(Entity):
    radius = config.BALL_RADIUS

    def __init__(self, x, y):
        super().__init__(x, y)
        self.reset(x, y)

    def reset(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = self.vz = 0.0
        self.z = 0.0
        self.spin = 0.0
        self.squash = 0
        self.near_hoop = False      # perto da cesta, a ordem de desenho é a do chão (entra na rede)

    @property
    def airborne(self):
        return self.z > 0.5 or self.vz > 0

    @property
    def sort_y(self):
        return self.y + (5000 if self.z > config.BODY_HEIGHT and not self.near_hoop else 0)

    def update(self, match):
        """No ar a bola só sofre a gravidade (a conta do arremesso fica exata); no chão ela quica."""
        self.vz -= config.GRAVITY
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        if self.z <= 0:
            self.z = 0.0
            if self.vz < -1.5:
                self.vz = -self.vz * FLOOR_BOUNCE
                self.vx *= 0.9
                self.vy *= 0.9
                self.squash = 3
                match.ball_bounced(self)
            else:
                self.vz = 0.0
                self.vx *= 0.985
                self.vy *= 0.985
        if self.squash:
            self.squash -= 1
        self.spin += math.hypot(self.vx, self.vy) * 0.15 + abs(self.vz) * 0.05

    def draw(self, surf, camera):
        gx, gy = round(self.x - camera.x), round(self.y - camera.y)
        shrink = max(0.5, 1 - self.z / 220)
        sw, sh = round(24 * shrink), max(4, round(9 * shrink))
        shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surf.blit(shadow, (gx - sw // 2, gy + 10 - sh // 2))
        sx, sy = gx, gy - round(self.z)
        r = self.radius
        if self.squash:
            rect = pygame.Rect(0, 0, r * 2 + 4, r * 2 - 4)
            rect.center = (sx, sy + 2)
            pygame.draw.ellipse(surf, SEAM_COLOR, rect.inflate(2, 2))
            pygame.draw.ellipse(surf, BALL_COLOR, rect)
            return
        pygame.draw.circle(surf, SEAM_COLOR, (sx, sy), r + 1)
        pygame.draw.circle(surf, BALL_COLOR, (sx, sy), r)
        # costuras girando
        k = math.cos(self.spin)
        pygame.draw.line(surf, SEAM_COLOR, (sx - r + 1, sy), (sx + r - 1, sy), 2)
        w = max(2, round(abs(k) * r))
        pygame.draw.ellipse(surf, SEAM_COLOR, (sx - w // 2, sy - r + 1, w, r * 2 - 2), 2)
        pygame.draw.circle(surf, (250, 170, 110), (sx - 4, sy - 4), 2)


def _hoop_images(key, side):
    """Camadas da cesta (de trás e da frente) da quadra; a da direita é o espelho da esquerda."""
    folder = config.TILES_DIR / key
    images = []
    for name in ("cesta.png", "aro_frente.png"):
        try:
            img = pygame.image.load(str(folder / name)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        images.append(pygame.transform.flip(img, True, False) if side == 1 else img)
    return images


class HoopLayer(Entity):
    """Uma das camadas da cesta. Sem a arte, desenha uma cesta simples."""

    def __init__(self, side, image, front):
        x = Court.HOOP_SPRITE[0] if side == 0 else Court.W - Court.HOOP_SPRITE[0] - 200
        super().__init__(x, Court.HOOP_SPRITE[1])
        self.side = side
        self.image = image
        self.front = front
        self.sort_y = Court.MID_Y + (Court.RIM_R if front else 0)

    def update(self, match):
        pass

    def draw(self, surf, camera):
        if self.image is not None:
            surf.blit(self.image, (round(self.x - camera.x), round(self.y - camera.y)))
            return
        hx, cy = Court.hoop_x(self.side), Court.MID_Y
        rim = pygame.Rect(0, 0, Court.RIM_R * 2, 16)
        rim.center = (round(hx - camera.x), round(cy - Court.RIM_Z - camera.y))
        if self.front:
            pygame.draw.arc(surf, (240, 104, 30), rim, math.pi, math.tau, 4)
            return
        bx = Court.board_x(self.side) - camera.x
        top = cy - Court.BOARD_HALF - Court.BOARD_Z[1] - camera.y
        bottom = cy + Court.BOARD_HALF - Court.BOARD_Z[0] - camera.y
        pygame.draw.rect(surf, (235, 235, 240), (round(bx) - 4, round(top), 8, round(bottom - top)))
        px, _ = Court.pole(self.side)
        pygame.draw.rect(surf, (60, 64, 76), (round(px - camera.x) - 6, round(cy - 150 - camera.y), 12, 150))
        pygame.draw.arc(surf, (240, 104, 30), rim, 0, math.pi, 4)


class BasketballMatch(Match):
    min_zoom = 0.6

    def __init__(self, game, session):
        key = session.map_key if session.map_key in BASKET_MAPS else BASKET_MAPS[0]
        super().__init__(game, session, key)
        spawns = self.arena.cfg.spawns
        self.spawn_of = {}
        for setup in session.slots:
            team = session.team_of(setup.slot)
            k = session.teammates(team).index(setup.slot)
            pos = spawns[team + 2 * k]
            fighter = self._add_fighter(setup, pos, team=team, color=theme.TEAM_COLORS[team] if setup.cpu else None)
            fighter.ring_color = theme.TEAM_COLORS[team]
            fighter.sprites = self.assets.kit_sprites(fighter.stats.key, team)
            fighter.kit = team
            fighter.armed = False
            fighter.power = None
            fighter.points = 0
            fighter.jump = 0                 # quadros desde o pulo (0 = no chão)
            fighter.jump_shot = False        # o pulo é de arremesso (com a barrinha)
            fighter.dunking = 0              # quadros que faltam do voo da enterrada
            fighter.dunk_from = fighter.dunk_to = (0.0, 0.0)
            fighter.shot_half = 0.3          # meia largura da faixa verde deste arremesso
            fighter.meter_flash = None       # (soltou em, faixa, quadros) para mostrar o resultado
            fighter.feint_timer = 0
            fighter.steal_timer = 0
            fighter.steal_cd = 0
            fighter.protecting = False
            fighter.streak = 0               # cestas seguidas
            fighter.fire_timer = 0
            self.spawn_of[fighter] = pos
            if setup.cpu:
                self.controllers[fighter] = BasketballAI()
            else:
                game.inputs[setup.slot].set_layout("soccer")      # mesmas teclas do futebol
                self.controllers[fighter] = game.inputs[setup.slot]
        self.ball = BasketBall(Court.W / 2, Court.MID_Y)
        self.hoops = []
        for side in (0, 1):
            images = _hoop_images(key, side) or (None, None)
            self.hoops += [HoopLayer(side, images[0], False), HoopLayer(side, images[1], True)]
        self.score = [0, 0]
        self.attack = {0: 1, 1: 0}          # time 0 ataca a cesta da direita (troca no 2º tempo)
        self.half = 1
        self.clock = HALF_SECONDS * config.FPS
        self.overtime = False
        self.holder = None                   # quem está com a bola na mão
        self.no_catch = {}                   # quem acabou de soltar a bola não pega de novo na hora
        self.shot = None                     # último arremesso no ar: quem, de onde, se vale 3
        self.shot_clock = 0
        self.catch_lock = 0                  # quadros logo depois do passe em que ninguém pega
        self.banner = None                   # ("CESTA!", "+3 · P1", time) e a idade
        self.banner_age = 0
        self.result_team = None
        self.freeze = 0
        self._tip_off()

    # ── consultas ────────────────────────────
    def hoop_of(self, team):
        """Lado da cesta que o time ataca."""
        return self.attack[team]

    def hoop_pos(self, side):
        return Court.hoop_x(side), Court.MID_Y

    def mates_of(self, f):
        return [o for o in self.fighters if o.team == f.team and o is not f]

    def foes_of(self, f):
        return [o for o in self.fighters if o.team != f.team]

    def world_entities(self):
        return self.fighters + [self.ball] + self.hoops

    def focus_points(self):
        ball = self.ball
        pts = [(ball.x, ball.y - ball.z)]
        pts += [(f.x, f.y - 20) for f in self.fighters if not f.is_cpu]
        if len(pts) == 1:
            pts += [(f.x, f.y - 20) for f in self.fighters]
        return pts

    def ball_bounced(self, ball):
        if ball.vz > 2:
            self.assets.play("click", min(0.35, ball.vz * 0.06))

    # ── ações ────────────────────────────────
    def _give(self, f):
        self.holder = f
        self.shot = None
        ball = self.ball
        ball.vx = ball.vy = ball.vz = 0.0
        if f.team != getattr(self, "_shot_team", None):
            self.shot_clock = 0
        self._shot_team = f.team

    def _release(self, f, frames=18):
        if self.holder is f:
            self.holder = None
        self.no_catch[f] = frames

    def on_fire(self, f):
        return f.fire_timer > 0

    def start_shot(self, f):
        """ARREMESSO com a bola: no garrafão, colado no aro, enterra na hora. Fora dele, pula e a
        barrinha começa a andar; a bola sai quando o jogador solta o botão (release_shot)."""
        if self.holder is not f or self.freeze or self.ending or f.jump or f.dunking:
            return False
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        dist = math.hypot(hx - f.x, hy - f.y)
        if Court.in_key(side, f.x, f.y) and dist < DUNK_RANGE:
            return self.dunk(f)
        f.jump = 1
        f.jump_shot = True
        f.shot_half = green_half(dist, Court.is_three(side, f.x, f.y), self.on_fire(f))
        f.facing = unit(hx - f.x, hy - f.y)
        return True

    def release_shot(self, f, timing=None):
        """Solta o arremesso. timing vai de 0 a 1 no pulo (0.5 = topo); dentro da faixa verde é
        cesta, perto dela bate no aro, longe passa direto."""
        if self.holder is not f or not f.jump_shot:
            return False
        if timing is None:
            timing = f.jump / JUMP_FRAMES
        err = shot_error(timing, f.shot_half)
        f.jump_shot = False
        f.meter_flash = (timing, f.shot_half, 40)
        if err == 0 and abs(timing - 0.5) < 0.04:
            self.popup(f.x, f.y - 90, "NO TEMPO!", theme.MOSS)
        elif err > 0:
            self.popup(f.x, f.y - 90, "CEDO" if timing < 0.5 else "TARDE", theme.BRASS)
        self.launch_shot(f, miss_distance(err, Court.RIM_R))
        return True

    def launch_shot(self, f, miss=0.0):
        """Joga a bola no aro (miss = quão longe do centro, 0 = no meio)."""
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        dist = math.hypot(hx - f.x, hy - f.y)
        three = Court.is_three(side, f.x, f.y)
        tx, ty = aim_point(hx, hy, f.x, f.y, miss, random.choice((-1, 1)))
        self._launch(f, tx, ty, Court.RIM_Z + 2, flight_frames(dist), z0=HAND_Z + f.lift)
        self.shot = {"team": f.team, "three": three, "shooter": f, "side": side}
        f.facing = unit(hx - f.x, hy - f.y)
        self.assets.play("arremesso", 0.35)

    def dunk(self, f):
        """Enterrada: voa até o aro com a bola em cima da cabeça e crava. No caminho, só um toco
        segura."""
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        dist = math.hypot(hx - f.x, hy - f.y)
        ux, uy = unit(f.x - hx, f.y - hy) if dist > 1 else ((1.0, 0.0) if side == 0 else (-1.0, 0.0))
        if (ux > 0) != (side == 0):
            ux = -ux                          # nunca por trás da tabela
        f.dunk_from = (f.x, f.y)
        f.dunk_to = (hx + ux * (DUNK_REACH + 6), hy + uy * (DUNK_REACH + 6))
        f.dunking = max(8, round(dist / 13))
        f.dunk_total = f.dunking
        f.jump, f.jump_shot = 0, False
        f.facing = unit(hx - f.x, hy - f.y)
        self.popup(f.x, f.y - 90, "ENTERRADA", theme.BONE)
        self.assets.play("dash", 0.4)
        return True

    def _dunk_release(self, f):
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        ball = self.ball
        self._release(f)
        ux, uy = unit(f.x - hx, f.y - hy)
        ball.x, ball.y = hx + ux * DUNK_REACH, hy + uy * DUNK_REACH
        ball.z = Court.RIM_Z + 30
        ball.vx, ball.vy, ball.vz = shot_velocity(ball.x, ball.y, ball.z, hx, hy, Court.RIM_Z - 6, 8,
                                                  config.GRAVITY)
        self.shot = {"team": f.team, "three": False, "shooter": f, "side": side, "dunk": True}
        f.jump = JUMP_FRAMES // 2            # desce do aro
        self.camera.shake(3)
        self.assets.play("arremesso", 0.45)

    def jump(self, f):
        """ARREMESSO sem a bola: pula para dar toco ou pegar o rebote mais alto."""
        if f.jump or f.stunned or self.freeze or self.ending or self.holder is f:
            return False
        f.jump = 1
        f.jump_shot = False
        return True

    def feint(self, f, direction=None):
        """CORTE com a bola: troca de mão e dá um passo rápido para o lado. Quem tentar roubar
        nesse instante erra e fica parado."""
        if self.holder is not f or f.jump or f.dunking or self.freeze or self.ending:
            return False
        if direction is None or math.hypot(*direction) < 0.2:
            fx, fy = f.facing
            side = random.choice((-1, 1))
            direction = (-fy * side, fx * side)
        direction = unit(*direction)
        if not f.dash(direction, frames=config.CUT_FRAMES, cooldown=36):
            return False
        f.feint_timer = FEINT_FRAMES
        self.popup(f.x, f.y - 80, "FINTA", theme.BONE)
        self.assets.play("dash", 0.3)
        return True

    def steal(self, f, direction=None):
        """CORTE sem a bola: arrancada curta; encostando em quem tem a bola, tenta roubar."""
        if f.jump or f.steal_cd > 0 or f.stunned or self.freeze or self.ending or self.holder is f:
            return False
        owner = self.holder
        if owner is not None and owner.team != f.team and f.distance_to(owner) < 160:
            direction = (owner.x - f.x, owner.y - f.y)
        elif direction is None or math.hypot(*direction) < 0.2:
            direction = f.facing
        direction = unit(*direction)
        if not f.dash(direction, frames=config.CUT_FRAMES, cooldown=30):
            return False
        f.facing = direction
        f.steal_timer = config.CUT_FRAMES + 3
        f.steal_cd = STEAL_COOLDOWN
        self.assets.play("dash", 0.3)
        self._check_steal(f)
        return True

    def _check_steal(self, f):
        owner = self.holder
        if (owner is None or owner.team == f.team or f.steal_timer <= 0
                or f.distance_to(owner) > f.radius + owner.radius + STEAL_REACH):
            return False
        f.steal_timer = 0
        if owner.feint_timer > 0 or owner.lift > 0:
            # caiu na finta (ou o outro já estava no ar)
            f.dash_timer = 0
            f.stun(FEINT_STUN)
            self.popup(f.x, f.y - 74, "CAIU NA FINTA" if owner.feint_timer > 0 else "ERROU", theme.MUTED)
            return False
        chance = steal_chance(owner.facing, f.x - owner.x, f.y - owner.y, owner.protecting)
        if random.random() >= chance:
            self.popup(f.x, f.y - 74, "ERROU", theme.MUTED)
            return False
        self._release(owner, 30)
        self._give(f)
        self.popup(f.x, f.y - 74, "ROUBO!", theme.BRASS)
        self.burst(self.ball.x, self.ball.y - 10, (236, 230, 220), 8, speed=3)
        self.assets.play("hit", 0.3)
        return True

    def pass_ball(self, f, direction=None):
        if self.holder is not f or self.freeze or self.ending:
            return False
        if direction is None or math.hypot(*direction) < 0.2:
            direction = f.facing
        direction = unit(*direction)
        mate = pick_receiver(f.x, f.y, direction, self.mates_of(f), 60)
        if mate is not None:
            vx, vy = mate.x - mate.prev_pos[0], mate.y - mate.prev_pos[1]
            dist = math.hypot(mate.x - f.x, mate.y - f.y)
            frames = max(8, round(dist / PASS_SPEED))
            tx, ty = mate.x + vx * frames, mate.y + vy * frames
        else:
            frames = 40
            tx, ty = f.x + direction[0] * PASS_SPEED * frames, f.y + direction[1] * PASS_SPEED * frames
        f.jump_shot = False
        self._launch(f, tx, ty, 30, max(8, round(math.hypot(tx - f.x, ty - f.y) / PASS_SPEED)), z0=30 + f.lift)
        self.catch_lock = 5                  # quem está colado não rouba o passe na saída da mão
        self.assets.play("chute", 0.25)
        return True

    def ask_ball(self, f):
        """Sem a bola, PASSE pede a bola: o companheiro da CPU passa na hora."""
        owner = self.holder
        if owner is not None and owner.team == f.team and owner is not f and owner.is_cpu:
            self.pass_ball(owner, (f.x - owner.x, f.y - owner.y))
            return True
        return False

    def _launch(self, f, tx, ty, tz, frames, z0=30):
        ball = self.ball
        self._release(f)
        ball.z = z0
        ball.vx, ball.vy, ball.vz = shot_velocity(ball.x, ball.y, ball.z, tx, ty, tz, frames, config.GRAVITY)

    # ── ciclo ────────────────────────────────
    def step(self):
        if self.banner:
            self.banner_age += 1
            if self.banner_age > 70:
                self.banner = None
        if self.ending:
            self.ending -= 1
            if self.frame % 4 == 0 and self.result_team is not None:
                self.burst(random.uniform(200, Court.W - 200), random.uniform(120, 500),
                           theme.TEAM_COLORS[self.result_team], 6, speed=3, gravity=0.15, size=5)
            if self.ending == 0:
                self._finish()
            return
        for f in self.fighters:
            f.prev_pos = (f.x, f.y)
            self._update_moves(f)
        for f, ctrl in self.controllers.items():
            if self.freeze or f.stunned:
                f.steer(0, 0)
                f.protecting = False
            elif hasattr(ctrl, "axis"):         # teclado, controle ou celular
                self._human(f, ctrl)
            else:
                ctrl.update(f, self)
            f.update(self)
            f.update_stamina()
        for i, a in enumerate(self.fighters):
            for b in self.fighters[i + 1:]:
                _separate(a, b)
                self.arena.resolve(a)
                self.arena.resolve(b)
        if self.freeze:
            self.freeze -= 1
            if self.freeze == 0:
                self._tip_off()
            return
        for f in self.fighters:
            if f.steal_timer > 0:
                self._check_steal(f)
            if f.jump or f.dunking:
                f.steer(0, 0)                   # no ar não dá para mudar de direção
            if f.protecting and self.holder is f:
                self._protect(f)
            else:
                f.protecting = False
        self._update_ball()
        self._update_clock()
        for f in self.fighters:
            if not f.is_cpu:
                hub.publish_slot(f.slot, stamina=f.stamina, tired=f.exhausted)

    def _update_moves(self, f):
        """Pulo (arco do desenho e barrinha), enterrada, finta, roubo e pegando fogo."""
        if f.dunking:
            f.dunking -= 1
            k = 1 - f.dunking / f.dunk_total
            (x0, y0), (x1, y1) = f.dunk_from, f.dunk_to
            f.x, f.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            f.vx = f.vy = 0.0
            f.lift = JUMP_H * math.sin(k * math.pi / 2)
            if f.dunking == 0:
                if self.holder is f:
                    self._dunk_release(f)
                else:
                    f.jump = JUMP_FRAMES // 2
        elif f.jump:
            f.jump += 1
            t = min(1.0, f.jump / JUMP_FRAMES)
            f.lift = JUMP_H * 4 * t * (1 - t)
            if f.jump >= JUMP_FRAMES:
                if f.jump_shot and self.holder is f:
                    self.release_shot(f, 1.0)   # não soltou: sai torto na descida
                f.jump, f.jump_shot, f.lift = 0, False, 0
        for name in ("feint_timer", "steal_timer", "steal_cd"):
            if getattr(f, name) > 0:
                setattr(f, name, getattr(f, name) - 1)
        if f.meter_flash is not None:
            timing, half, frames = f.meter_flash
            f.meter_flash = (timing, half, frames - 1) if frames > 1 else None
        if f.fire_timer > 0:
            f.fire_timer -= 1
            if self.frame % 2 == 0:
                self.burst(f.x + random.uniform(-12, 12), f.y - random.uniform(10, 50) - f.lift,
                           random.choice(((255, 140, 40), (255, 200, 80), (240, 80, 30))), 1,
                           speed=1.2, gravity=-0.08, size=3)
            if f.fire_timer == 0:
                f.streak = 0

    def _protect(self, f):
        """MARCAR com a bola: de costas para o marcador mais perto, andando devagar."""
        f.slow_timer = max(f.slow_timer, 2)
        foes = self.foes_of(f)
        if foes:
            foe = min(foes, key=f.distance_to)
            if f.distance_to(foe) < 220:
                f.facing = unit(f.x - foe.x, f.y - foe.y)
                f.aim_timer = max(f.aim_timer, 2)

    def mark_point(self, f):
        """Onde fica quem MARCA: entre o adversário (o da bola, se estiver perto) e a própria cesta."""
        foes = self.foes_of(f)
        if not foes:
            return None
        owner = self.holder
        if owner is not None and owner.team != f.team and f.distance_to(owner) < 500:
            target = owner
        else:
            target = min(foes, key=f.distance_to)
        hx, hy = self.hoop_pos(1 - self.hoop_of(f.team))
        ux, uy = unit(hx - target.x, hy - target.y)
        return target.x + ux * 44, target.y + uy * 44, target

    def _human(self, f, inp):
        stick = inp.axis()
        f.sprint_held = inp.held("sprint")
        has_ball = self.holder is f
        f.protecting = inp.held("mark") and has_ball
        point = self.mark_point(f) if inp.held("mark") and not has_ball else None
        if point is not None:
            tx, ty, target = point
            dx, dy = tx - f.x, ty - f.y
            d = math.hypot(dx, dy)
            power = min(1.0, d / 40) * (1.0 if f.sprint_held else config.MARK_SPEED)
            mx, my = (dx / d * power, dy / d * power) if d > 6 else (0.0, 0.0)
            if math.hypot(*stick) > 0.2:
                mx, my = mx * 0.5 + stick[0] * 0.5, my * 0.5 + stick[1] * 0.5     # o jogador corrige
            f.steer(mx, my)
            if d < 30:
                f.face(target)
        else:
            f.steer(*stick)
        if has_ball:
            if inp.pressed("attack"):
                self.start_shot(f)
            elif f.jump_shot and not inp.held("attack"):
                self.release_shot(f)
            if inp.pressed("special"):
                self.pass_ball(f, stick)
            if inp.pressed("dodge"):
                self.feint(f, stick)
            elif inp.double_tap:
                self.feint(f, inp.double_tap)
        else:
            if inp.pressed("attack"):
                self.jump(f)
            if inp.pressed("special"):
                self.ask_ball(f)
            if inp.pressed("dodge"):
                self.steal(f, stick)
            elif inp.double_tap:
                self.steal(f, inp.double_tap)
        if inp.pressed("super"):
            self.assets.play("cancel", 0.2)     # os SUPERs do basquete chegam na etapa 5

    def _update_ball(self):
        ball = self.ball
        for f in list(self.no_catch):
            self.no_catch[f] -= 1
            if self.no_catch[f] <= 0:
                del self.no_catch[f]
        if self._block_dunk():
            return
        owner = self.holder
        if owner is not None:
            # a bola quica sozinha ao lado do jogador (o drible é automático)
            fx, fy = owner.facing
            if owner.jump or owner.dunking:
                # no pulo a bola vai nas mãos, em cima da cabeça
                ball.x, ball.y = owner.x + fx * 6, owner.y + 2
                ball.z = owner.lift + config.BODY_HEIGHT + 30
            else:
                ball.x, ball.y = owner.x + fx * 16, owner.y + fy * 8 + 6
                ball.z = abs(math.sin(self.frame * 0.22)) * 22
            ball.vx = ball.vy = ball.vz = 0.0
            ball.spin += 0.2
            ball.near_hoop = False
            return
        x0, z0 = ball.x, ball.z
        ball.update(self)
        for side in (0, 1):
            self._hoop_physics(side, x0, z0)
            if self.holder is not None or self.freeze:
                return
        _bounce_off_walls(ball, self.arena.walls)
        ball.near_hoop = any(abs(ball.x - Court.hoop_x(s)) < 80 and abs(ball.y - Court.MID_Y) < 60 for s in (0, 1))
        if self._block():
            return
        self._rebound_pull()
        self._catch()

    def _block_dunk(self):
        """Toco na enterrada: quem está no ar encosta em quem voa para o aro e a bola sai."""
        owner = self.holder
        if owner is None or not owner.dunking:
            return False
        for f in self.foes_of(owner):
            if f.lift < 10 or f.distance_to(owner) > f.radius + owner.radius + BLOCK_REACH:
                continue
            ball = self.ball
            self._release(owner, 30)
            owner.dunking = 0
            owner.jump = JUMP_FRAMES // 2
            ux, uy = unit(owner.x - f.x, owner.y - f.y)
            ball.vx, ball.vy, ball.vz = ux * 5, uy * 5, 3.0
            self._toco(f, ball)
            return True
        return False

    def _toco(self, f, ball):
        self.popup(f.x, f.y - 90, "TOCO!", theme.BRASS)
        self.burst(ball.x, ball.y - ball.z, (236, 230, 220), 10, speed=4)
        self.camera.shake(4)
        self.hit_pause(4)
        self.assets.play("hit", 0.5)

    def _block(self):
        """Toco: quem está no ar encosta no arremesso (ou na enterrada) do adversário."""
        ball, shot = self.ball, self.shot
        if shot is None or shot.get("touched") or shot.get("blocked"):
            return False
        for f in self.fighters:
            if f.lift < 10 or f.team == shot["team"]:
                continue
            reach = f.lift + config.BODY_HEIGHT + 64
            d = math.hypot(f.x - ball.x, f.y - ball.y)
            if d < f.radius + ball.radius + BLOCK_REACH and ball.z < reach:
                ux, uy = unit(ball.x - f.x, ball.y - f.y) if d > 1 else unit(-ball.vx, -ball.vy)
                ball.vx, ball.vy, ball.vz = ux * 6, uy * 6, 2.5
                shot["blocked"] = True
                self.shot = None
                self.no_catch.pop(f, None)
                self._toco(f, ball)
                return True
        return False

    def _rebound_pull(self):
        """A bola que bateu no aro e está caindo é puxada um pouco para o jogador mais perto."""
        ball, shot = self.ball, self.shot
        if shot is None or not shot.get("touched") or ball.vz >= 0 or ball.z > Court.RIM_Z:
            return
        near = [f for f in self.fighters if not f.stunned and f not in self.no_catch]
        if not near:
            return
        f = min(near, key=lambda o: math.hypot(o.x - ball.x, o.y - ball.y))
        d = math.hypot(f.x - ball.x, f.y - ball.y)
        if 8 < d < 200:
            ball.vx += (f.x - ball.x) / d * REBOUND_PULL
            ball.vy += (f.y - ball.y) / d * REBOUND_PULL

    def _hoop_physics(self, side, x0, z0):
        """Tabela, aro e cesta. Bater no aro ou entrar zera o relógio de posse."""
        ball = self.ball
        hx, hy = self.hoop_pos(side)
        if board_hit(x0, ball.x, ball.y - hy, ball.z, Court.board_x(side), side, Court.BOARD_HALF,
                     Court.BOARD_Z, ball.radius):
            face = Court.board_x(side) + (ball.radius if side == 0 else -ball.radius)
            ball.x = face
            ball.vx = -ball.vx * BOARD_KEEP
            ball.vy *= BOARD_KEEP
            self.assets.play("click", 0.3)
        hit = rim_contact(ball.x, ball.y, ball.z, hx, hy, Court.RIM_Z, Court.RIM_R, ball.radius)
        if hit is not None:
            (nx, ny, nz), depth = hit
            ball.x += nx * depth
            ball.y += ny * depth
            ball.z += nz * depth
            ball.vx, ball.vy, ball.vz = bounce((ball.vx, ball.vy, ball.vz), (nx, ny, nz), RIM_KEEP)
            self.shot_clock = 0
            if self.shot is not None:
                self.shot["touched"] = True
            if math.hypot(ball.vx, ball.vy) + abs(ball.vz) > 2:
                self.assets.play("click", 0.4)
        elif through_hoop(z0, ball.z, ball.x, ball.y, hx, hy, Court.RIM_Z, Court.RIM_R, ball.radius):
            self._basket(side)

    def _catch(self):
        """Bola baixa: o jogador mais perto que encostar pega (inclusive a do passe adversário)."""
        ball = self.ball
        if self.catch_lock > 0:
            self.catch_lock -= 1
            return
        if self.shot is not None and ball.vz > 0 and not self.shot.get("touched"):
            return                           # arremesso subindo: só o toco tira
        best, best_d = None, 1e9
        for f in self.fighters:
            if f.stunned or f in self.no_catch or ball.z >= CATCH_HEIGHT + f.lift:
                continue                     # no pulo, pega mais alto (rebote)
            d = math.hypot(f.x - ball.x, f.y - ball.y)
            if d < f.radius + ball.radius + 12 and d < best_d:
                best, best_d = f, d
        if best is not None:
            if self.shot is not None and best.team != self.shot["team"]:
                self.popup(best.x, best.y - 74, "REBOTE", theme.BONE)
            self._give(best)

    def _basket(self, side):
        team = next(t for t, s in self.attack.items() if s == side)
        shot = self.shot
        points = 3 if shot is not None and shot["three"] and shot["team"] == team else 2
        self.score[team] += points
        scorer = shot["shooter"] if shot is not None and shot["team"] == team else None
        if scorer is not None:
            scorer.points += points
        title = "CESTA DE 3!" if points == 3 else "CESTA!"
        self.banner = (title, scorer.label if scorer else "", team)
        self.banner_age = 0
        self._streak(scorer, team)
        hx, hy = self.hoop_pos(side)
        self.burst(hx, hy - Court.RIM_Z, theme.TEAM_COLORS[team], 26, speed=6, gravity=0.12, size=4)
        self.burst(hx, hy - Court.RIM_Z, theme.BONE, 12, speed=4, gravity=0.12, size=3)
        self.camera.shake(5)
        self.hit_pause(6)
        self.assets.play("torcida", 0.4)
        self.shot = None
        self.shot_clock = 0
        if self.overtime:
            self._end(team)
            return
        # sem cobrança: a bola já sai com o time que levou, embaixo da própria cesta
        ball = self.ball
        ball.reset(hx + (130 if side == 0 else -130), hy)
        takers = [f for f in self.fighters if f.team != team and not f.stunned]
        if takers:
            self._give(min(takers, key=lambda f: f.distance_to(ball)))

    def _streak(self, scorer, team):
        """Cestas seguidas: a terceira do mesmo jogador faz ele pegar fogo. Cesta do outro time
        apaga o fogo de quem está pegando fogo."""
        for f in self.fighters:
            if f is scorer:
                continue
            f.streak = 0
            if f.team != team:
                f.fire_timer = 0
        if scorer is None:
            return
        scorer.streak += 1
        if scorer.streak >= FIRE_STREAK and scorer.fire_timer == 0:
            self.banner = ("PEGANDO FOGO!", scorer.label, team)
            self.burst(scorer.x, scorer.y - 30, (255, 150, 40), 24, speed=5, gravity=-0.05, size=4)
        if scorer.streak >= FIRE_STREAK:
            scorer.fire_timer = FIRE_SECONDS * config.FPS

    def _update_clock(self):
        if self.holder is not None:
            self.shot_clock += 1
            if self.shot_clock >= SHOT_CLOCK * config.FPS:
                self._turnover(self.holder)
        if self.overtime:
            return
        self.clock -= 1
        if self.clock > 0:
            return
        if self.half == 1:
            self.half = 2
            self.clock = HALF_SECONDS * config.FPS
            self.attack = {0: 0, 1: 1}                  # 2º tempo: os times trocam de lado
            self.banner = ("INTERVALO", "TROCA DE LADO", None)
            self.banner_age = 0
            self.assets.play("apito", 0.4)
            self.freeze = 90
        elif self.score[0] != self.score[1]:
            self._end(0 if self.score[0] > self.score[1] else 1)
        else:
            self.overtime = True
            self.banner = ("EMPATE", "PRÓXIMA CESTA VENCE", None)
            self.banner_age = 0
            self.assets.play("apito", 0.4)
            self.freeze = 90

    def _turnover(self, f):
        """10 segundos com a bola sem arremessar: ela vai para o adversário mais perto."""
        self.popup(f.x, f.y - 74, f"{SHOT_CLOCK} SEGUNDOS", theme.BRASS)
        self._release(f, 40)
        foes = self.foes_of(f)
        if foes:
            self._give(min(foes, key=lambda o: o.distance_to(f)))
        self.assets.play("apito", 0.3)

    def _tip_off(self):
        """Bola ao alto no meio da quadra; cada time no seu lado (no 2º tempo, lados trocados)."""
        self.ball.reset(Court.W / 2, Court.MID_Y)
        self.ball.z, self.ball.vz = 60.0, 6.0
        self.holder = None
        self.shot = None
        self.shot_clock = 0
        self.no_catch.clear()
        flip = self.attack[0] == 0
        for f, (x, y) in self.spawn_of.items():
            f.x, f.y = (Court.W - x if flip else x), y
            f.vx = f.vy = 0
            f.knock = [0.0, 0.0]
            f.stun_timer = f.sprint_timer = f.dash_timer = 0
            f.stamina, f.exhausted = 1.0, False
            f.jump = f.dunking = 0
            f.jump_shot, f.lift, f.protecting = False, 0, False
            hx, _ = self.hoop_pos(self.hoop_of(f.team))
            f.facing = (1.0, 0.0) if hx > f.x else (-1.0, 0.0)

    def _end(self, team):
        self.result_team = team
        self.ending = config.DEATH_ANIM_FRAMES + 30
        self.holder = None
        self.assets.play("apito", 0.4)
        self.assets.stop_music(1800)

    def _finish(self):
        team = self.result_team
        winners = [f for f in self.fighters if f.team == team]
        lines = [("PLACAR", f"{self.score[0]} x {self.score[1]}")]
        for f in self.fighters:
            lines.append((f"{f.label} PONTOS", str(f.points)))
        self.result = Result(f"TIME {theme.TEAM_NAMES[team]} VENCEU", theme.TEAM_COLORS[team], winners,
                             lines, score=tuple(self.score))
        self.finished = True

    # ── desenho ──────────────────────────────
    def draw_under(self, view, cam):
        p = self.holder
        if p is not None:
            rect = pygame.Rect(0, 0, 54, 18)
            rect.center = (round(p.x - cam.x), round(p.y - cam.y) + 22)
            pygame.draw.ellipse(view, (232, 232, 220), rect, 1)

    def draw(self, screen, ui):
        super().draw(screen, ui)
        for f in self.fighters:
            if f.jump_shot or f.meter_flash is not None:
                self._draw_meter(screen, f)
        if self.banner:
            hud.draw_basket_banner(screen, ui, *self.banner, self.banner_age)

    def _draw_meter(self, screen, f):
        """Barrinha do arremesso em cima do jogador: a faixa verde é o topo do pulo."""
        if f.jump_shot:
            timing, half, flash = min(1.0, f.jump / JUMP_FRAMES), f.shot_half, False
        else:
            timing, half, frames = f.meter_flash
            flash = True
            if frames % 6 < 2:
                return                          # pisca depois de soltar
        sx, sy = self.camera.to_screen(f.x, f.y - 104 - f.lift)
        bar = pygame.Rect(0, 0, 60, 8)
        bar.center = (round(sx), round(sy))
        screen.fill(theme.SHADOW, bar.inflate(4, 4))
        screen.fill((60, 40, 40), bar)
        g0 = bar.x + round(bar.w * max(0.0, 0.5 - half))
        g1 = bar.x + round(bar.w * min(1.0, 0.5 + half))
        screen.fill((90, 200, 110) if f.fire_timer <= 0 else (255, 170, 60), (g0, bar.y, max(2, g1 - g0), bar.h))
        mx = bar.x + round(bar.w * timing)
        hit = shot_error(timing, half) == 0
        color = theme.BONE if not flash else ((150, 255, 160) if hit else (255, 120, 100))
        screen.fill(theme.SHADOW, (mx - 2, bar.y - 4, 5, bar.h + 8))
        screen.fill(color, (mx - 1, bar.y - 3, 3, bar.h + 6))

    def draw_hud(self, screen, ui):
        hud.draw_basket(screen, ui, self)

    def hud_regions(self):
        W = config.SCREEN_W
        return [pygame.Rect(W // 2 - 166, 0, 332, 96)]
