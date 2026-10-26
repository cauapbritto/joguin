"""Modo basquete: 2 x 2 no estilo NBA Jam (quadra, cestas, bola e a partida).

A quadra tem as medidas de arena.Court nas três versões (ginásio, rua e Arena Soul). A cesta é
desenhada em duas camadas: a de trás (poste, tabela, rede de trás) entra na ordem dos jogadores, e
a da frente (aro e rede da frente) passa por cima da bola, que assim aparece entrando na rede.
"""
import math
import random

import pygame

from . import config, hud, theme
from .ai import BALL_DIFFICULTIES, BasketballAI
from .arena import BASKET_MAPS, Court
from .basket_powers import create_basket_power
from .basket_assist import (JUMP_FRAMES, aim_point, board_hit, bounce, flight_frames, green_half, miss_distance,
                            rim_contact, shot_error, shot_velocity, steal_chance, through_hoop)
from .entities import Entity
from .matches import Match, Result, _bounce_off_walls, _separate
from .net.remote import hub
from .soccer_assist import pick_receiver, unit

HALF_SECONDS = 120              # dois tempos de 2 minutos
WARMUP_SECONDS = 60             # aquecimento antes da bola ao alto: cada um com a sua bola
WARM_STATE = ("ball", "holder", "shot", "no_catch", "catch_lock", "alley")   # o que cada bola tem
COMEBACK_GAP = 10              # perdendo por tanto ou mais: o time ganha uma ajuda (estilo NBA Jam)
COMEBACK_GREEN = (0.05, 0.02)   # faixa verde a mais (meia distância, de 3)
SHOT_CLOCK = 10                 # segundos com a bola sem arremessar: perde a posse
CATCH_HEIGHT = 56               # bola mais baixa que isso pode ser pega
HAND_Z = 40                     # altura de onde sai o arremesso
PASS_SPEED = 11.0
PASS_HOMING = 120               # quadros no máximo que o passe persegue o companheiro
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
# tipos de enterrada: os mais vistosos só com fogo, Enterrada Voadora ou alley-oop
DUNKS = ("CRAVADA", "GIRO 360", "PENDURADO NO ARO")
SHOW_DUNKS = ("MOINHO", "CAMBALHOTA", "GIRO 360")
HANG_FRAMES = 30                # Pendurado no Aro: tempo segurando no aro antes de cair
RIM_SHAKE = 24
GLUE_STEAL = 0.04               # Marcação Colada: chance por quadro encostado (uns 0,4s em média)                  # quadros que o aro treme depois da enterrada
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


def _run_velocity(f):
    """Quanto o jogador andou no último quadro (com limite: um teleporte não conta como corrida)."""
    vx, vy = f.x - f.prev_pos[0], f.y - f.prev_pos[1]
    speed = math.hypot(vx, vy)
    return (vx, vy) if speed <= 12 else (0.0, 0.0)


def who(f):
    """Nome no placar final: o personagem, com a vaga na frente quando é gente jogando."""
    name = f.stats.name.upper()
    return name if f.is_cpu else f"{f.label} {name}"


def stat_line(f):
    """Números de um jogador no placar final: os pontos e o que mais ele fez (cabe numa linha)."""
    extras = [(n, one if n == 1 else many) for n, one, many in (
        (f.dunks, "ENTERRADA", "ENTERRADAS"), (f.blocks, "TOCO", "TOCOS"), (f.steals, "ROUBO", "ROUBOS")) if n]
    if not extras:
        return f"{f.points} PTS"
    n, word = max(extras, key=lambda e: e[0])
    return f"{f.points} PTS  {n} {word}"


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


def _fire_frames(side):
    """Fogo animado em volta do aro (arte da Arena Soul, serve nas três quadras)."""
    frames = []
    for i in range(1, 5):
        try:
            img = pygame.image.load(str(config.TILES_DIR / "quadra_soul" / f"aro_fogo_{i}.png")).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return []
        frames.append(pygame.transform.flip(img, True, False) if side == 1 else img)
    return frames


class HoopLayer(Entity):
    """Uma das camadas da cesta. Sem a arte, desenha uma cesta simples."""

    def __init__(self, side, image, front):
        x = Court.HOOP_SPRITE[0] if side == 0 else Court.W - Court.HOOP_SPRITE[0] - 200
        super().__init__(x, Court.HOOP_SPRITE[1])
        self.side = side
        self.image = image
        self.front = front
        self.sort_y = Court.MID_Y + (Court.RIM_R if front else 0)
        self.shake = 0                       # depois da enterrada a cesta treme
        self.fire = False                    # alguém que ataca esta cesta está pegando fogo
        self.fire_frames = _fire_frames(side) if front else []
        self.ticks = 0

    def update(self, match):
        pass

    def draw(self, surf, camera):
        dy = round(math.sin(self.shake * 1.3) * self.shake / 6) if self.shake else 0
        self.ticks += 1
        if self.image is not None:
            surf.blit(self.image, (round(self.x - camera.x), round(self.y - camera.y) + dy))
            if self.fire and self.fire_frames:
                frame = self.fire_frames[(self.ticks // 6) % len(self.fire_frames)]
                surf.blit(frame, (round(self.x - camera.x), round(self.y - camera.y) + dy))
            return
        hx, cy = Court.hoop_x(self.side), Court.MID_Y
        rim = pygame.Rect(0, 0, Court.RIM_R * 2, 16)
        rim.center = (round(hx - camera.x), round(cy - Court.RIM_Z - camera.y) + dy)
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
    RIM_Z = Court.RIM_Z

    def __init__(self, game, session, warmup=False):
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
            fighter.power = create_basket_power(fighter.stats)
            fighter.points = 0
            fighter.blocks = fighter.steals = fighter.dunks = 0      # números do placar final
            fighter.glue_timer = 0           # Marcação Colada
            fighter.wall_timer = 0           # Toco Voador
            fighter.hot_timer = 0            # Mão Quente
            fighter.ghost_timer = 0          # Bola Fantasma (vale para o próximo arremesso)
            fighter.frost_timer = 0          # Congelar: faixa verde estreita
            fighter.fly_dunk = False         # enterrada voadora (ninguém toca no ar)
            fighter.alley_dunk = False       # a enterrada veio de um alley-oop
            fighter.jump = 0                 # quadros desde o pulo (0 = no chão)
            fighter.jump_shot = False        # o pulo é de arremesso (com a barrinha)
            fighter.dunking = 0              # quadros que faltam do voo da enterrada
            fighter.dunk_from = fighter.dunk_to = (0.0, 0.0)
            fighter.dunk_move = ""            # tipo da enterrada (DUNKS ou SHOW_DUNKS)
            fighter.hang = 0                 # quadros pendurado no aro depois de cravar
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
                self.controllers[fighter] = BasketballAI(session.difficulty)
                fighter.speed *= BALL_DIFFICULTIES[session.difficulty]["speed"]
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
        self.lids = {0: 0, 1: 0}             # Tampa no Aro: quadros que faltam em cada aro
        self.alley = None                    # alley-oop no ar: quem passou, para quem, quem caiu
        self.pass_to = None                  # passe teleguiado no ar: para quem e a que velocidade
        self.warmup = 0                      # quadros que faltam do aquecimento (0 = jogo valendo)
        self.warm = {}                       # aquecimento: o estado da bola de cada jogador
        self._only = None                    # aquecimento: só este jogador pega a bola da vez
        self._tip_off()
        if warmup:
            self._start_warmup()

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
        if self.warmup:
            return self.fighters + [st["ball"] for st in self.warm.values()] + self.hoops
        return self.fighters + [self.ball] + self.hoops

    def focus_points(self):
        if self.warmup:
            pts = [(f.x, f.y - 20) for f in self.fighters if not f.is_cpu]
            return pts or [(f.x, f.y - 20) for f in self.fighters]
        ball = self.ball
        pts = [(ball.x, ball.y - ball.z)]
        pts += [(f.x, f.y - 20) for f in self.fighters if not f.is_cpu]
        if len(pts) == 1:
            pts += [(f.x, f.y - 20) for f in self.fighters]
        return pts

    def ball_bounced(self, ball):
        if ball.vz > 2:
            self.assets.play("quique", min(0.45, ball.vz * 0.08))

    # ── ações ────────────────────────────────
    def _give(self, f):
        self.holder = f
        self.shot = None
        self.pass_to = None
        ball = self.ball
        ball.vx = ball.vy = ball.vz = 0.0
        if f.team != getattr(self, "_shot_team", None):
            self.shot_clock = 0
        self._shot_team = f.team

    def _release(self, f, frames=18):
        if self.holder is f:
            self.holder = None
        self.no_catch[f] = frames

    def release_ball(self, f, frames=18):
        """Tira a bola da mão (poderes, hack, atropelo)."""
        self._release(f, frames)
        f.jump_shot = False

    def grab(self, f):
        """A bola vai direto para a mão (gancho, interceptação)."""
        ball = self.ball
        ball.x, ball.y, ball.z = f.x, f.y, 20.0
        self.alley = None
        self._give(f)

    def freeze_foe(self, foe, frames):
        """Congelar: lento e com a faixa verde estreita. O Exo e o Faro de Cesta não sentem."""
        if foe.exo_timer > 0 or foe.nose_timer > 0:
            return False
        if not foe.slow(frames):
            return False
        foe.frost_timer = max(foe.frost_timer, frames)
        return True

    def use_power(self, f):
        if self.warmup or self.freeze or self.ending or f.power is None:
            return False
        if not f.power.use(f, self):
            return False
        hub.publish_slot(f.slot, cooldown=1.0) if not f.is_cpu else None
        return True

    def glued_by(self, f):
        """Adversário de Marcação Colada em cima de f (ou None)."""
        return next((o for o in self.foes_of(f) if o.glue_timer > 0 and o.distance_to(f) < 90
                     and not o.stunned), None)

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
            if self.glued_by(f) is None:
                return self.dunk(f)
            self.popup(f.x, f.y - 90, "SEM ENTERRADA", theme.MUTED)   # marcação colada
        f.jump = 1
        f.jump_shot = True
        three = Court.is_three(side, f.x, f.y)
        half = green_half(dist, three, self.on_fire(f)) + f.power.green_bonus
        if self.comeback(f.team):
            half += COMEBACK_GREEN[1 if three else 0]
        if f.hot_timer > 0:
            half = 0.5                        # Mão Quente: a faixa inteira
        if f.frost_timer > 0:
            half *= 0.4                       # Congelar: faixa estreita
        f.shot_half = half
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
        self.shot = {"team": f.team, "three": three, "shooter": f, "side": side, "ghost": f.ghost_timer > 0}
        f.ghost_timer = 0
        f.facing = unit(hx - f.x, hy - f.y)
        self.assets.play("arremesso", 0.35)

    def dunk(self, f, flying=False, alley=False):
        """Enterrada: voa até o aro com a bola em cima da cabeça e crava. No caminho, só um toco
        segura. A voadora (Cauanzera) e a do alley-oop vão alto, por cima de todo mundo."""
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        dist = math.hypot(hx - f.x, hy - f.y)
        ux, uy = unit(f.x - hx, f.y - hy) if dist > 1 else ((1.0, 0.0) if side == 0 else (-1.0, 0.0))
        if (ux > 0) != (side == 0):
            ux = -ux                          # nunca por trás da tabela
        f.dunk_from = (f.x, f.y)
        f.dunk_to = (hx + ux * (DUNK_REACH + 6), hy + uy * (DUNK_REACH + 6))
        f.dunking = max(8, round(dist / (10 if flying else 13)))
        f.dunk_total = f.dunking
        f.fly_dunk = flying
        f.alley_dunk = alley
        f.jump, f.jump_shot = 0, False
        f.facing = unit(hx - f.x, hy - f.y)
        show = flying or alley or self.on_fire(f)
        f.dunk_move = random.choice(SHOW_DUNKS if show else DUNKS)
        self.popup(f.x, f.y - 90, f.dunk_move + "!", theme.BRASS if show else theme.BONE)
        self.assets.play("dash", 0.4)
        return True

    def _dunk_release(self, f):
        side = self.hoop_of(f.team)
        hx, hy = self.hoop_pos(side)
        ball = self.ball
        if f.exo_timer > 0 and self.lids[side] > 0:
            self.lids[side] = 0
            self.popup(hx, hy - 150, "ARRANCOU A TAMPA", theme.BRASS)
            self.burst(hx, hy - Court.RIM_Z, (150, 226, 240), 20, speed=5)
        wall = None if f.alley_dunk else next(
            (o for o in self.foes_of(f) if o.wall_timer > 0 and not o.stunned
             and math.hypot(o.x - hx, o.y - hy) < 260), None)
        if wall is not None:
            # Toco Voador: o Paredão sobe e tira a enterrada
            wall.wall_timer = 0
            wall.jump = 1
            self._release(f, 30)
            ux, uy = unit(f.x - hx, f.y - hy)
            ball.x, ball.y, ball.z = f.x, f.y, f.lift + 50
            ball.vx, ball.vy, ball.vz = ux * 6, uy * 6, 3.0
            f.jump, f.fly_dunk, f.alley_dunk = JUMP_FRAMES // 2, False, False
            self._toco(wall, ball, "TOCO VOADOR!")
            return
        self._release(f)
        ux, uy = unit(f.x - hx, f.y - hy)
        ball.x, ball.y = hx + ux * DUNK_REACH, hy + uy * DUNK_REACH
        ball.z = Court.RIM_Z + 30
        ball.vx, ball.vy, ball.vz = shot_velocity(ball.x, ball.y, ball.z, hx, hy, Court.RIM_Z - 6, 8,
                                                  config.GRAVITY)
        self.shot = {"team": f.team, "three": False, "shooter": f, "side": side, "dunk": True}
        show = f.fly_dunk or f.alley_dunk or f.dunk_move in SHOW_DUNKS
        f.facing = unit(hx - f.x, hy - f.y)
        f.spin = 0
        if f.dunk_move == "PENDURADO NO ARO":
            f.hang = HANG_FRAMES             # fica no aro e só depois desce
        else:
            f.jump = JUMP_FRAMES // 2        # desce do aro
        f.fly_dunk = f.alley_dunk = False
        for hoop in self.hoops:
            if hoop.side == side:
                hoop.shake = RIM_SHAKE
        rim_y = hy - Court.RIM_Z
        self.burst(hx, rim_y, f.color, 22 if show else 14, speed=6 if show else 4)
        self.burst(hx, rim_y, (255, 236, 170), 10, speed=3)
        self.camera.shake(6 if show else 4)
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
        f.feint_timer = FEINT_FRAMES + f.power.feint_bonus
        self.popup(f.x, f.y - 80, "FINTA", theme.BONE)
        self.assets.play("dash", 0.3)
        return True

    def steal(self, f, direction=None):
        """CORTE sem a bola: arrancada curta; encostando em quem tem a bola, tenta roubar."""
        if (f.jump or f.steal_cd > 0 or f.stunned or self.freeze or self.ending or self.holder is f
                or self.warmup):
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
        if owner.magic_timer > 0 or owner.exo_timer > 0 or owner.moto_timer > 0:
            self.popup(f.x, f.y - 74, "NÃO TIRA", theme.MUTED)
            return False
        chance = steal_chance(owner.facing, f.x - owner.x, f.y - owner.y, owner.protecting)
        chance *= owner.power.steal_mult
        if random.random() >= chance:
            self.popup(f.x, f.y - 74, "ERROU", theme.MUTED)
            return False
        self._release(owner, 30)
        self._give(f)
        f.steals += 1
        self.popup(f.x, f.y - 74, "ROUBO!", theme.BRASS)
        self.burst(self.ball.x, self.ball.y - 10, (236, 230, 220), 8, speed=3)
        self.assets.play("hit", 0.3)
        return True

    def pass_ball(self, f, direction=None):
        if self.holder is not f or self.freeze or self.ending or self.warmup:
            return False
        if direction is None or math.hypot(*direction) < 0.2:
            direction = f.facing
        direction = unit(*direction)
        mates = self.mates_of(f)
        mate = pick_receiver(f.x, f.y, direction, mates, 60)
        if mate is None and mates:
            # fora do cone: vai para o companheiro mais perto da direção apontada (no 2 x 2, o único)
            mate = max(mates, key=lambda m: unit(m.x - f.x, m.y - f.y)[0] * direction[0]
                       + unit(m.x - f.x, m.y - f.y)[1] * direction[1])
        if mate is not None:
            vx, vy = _run_velocity(mate)
            dist = math.hypot(mate.x - f.x, mate.y - f.y)
            frames = max(8, round(dist / (PASS_SPEED * f.power.pass_speed)))
            tx, ty = mate.x + vx * frames, mate.y + vy * frames
        else:
            frames = 40
            tx, ty = f.x + direction[0] * PASS_SPEED * frames, f.y + direction[1] * PASS_SPEED * frames
        f.jump_shot = False
        self._launch(f, tx, ty, 30, max(8, round(math.hypot(tx - f.x, ty - f.y) / PASS_SPEED)), z0=30 + f.lift)
        self.catch_lock = 5                  # quem está colado não rouba o passe na saída da mão
        if mate is not None:
            # passe teleguiado: a bola corrige o caminho até a mão do companheiro, mesmo correndo
            self.pass_to = {"to": mate, "speed": PASS_SPEED * f.power.pass_speed, "frames": PASS_HOMING}
        self.assets.play("chute", 0.25)
        return True

    def ask_ball(self, f):
        """Sem a bola, PASSE pede a bola: o companheiro da CPU passa na hora."""
        owner = self.holder
        if owner is not None and owner.team == f.team and owner is not f and owner.is_cpu and not self.warmup:
            self.pass_ball(owner, (f.x - owner.x, f.y - owner.y))
            return True
        return False

    def _launch(self, f, tx, ty, tz, frames, z0=30):
        ball = self.ball
        self._release(f)
        ball.z = z0
        ball.vx, ball.vy, ball.vz = shot_velocity(ball.x, ball.y, ball.z, tx, ty, tz, frames, config.GRAVITY)

    # ── ciclo ────────────────────────────────
    def comeback(self, team):
        """O time está perdendo por COMEBACK_GAP pontos ou mais (a ajuda some quando encosta)."""
        return not self.warmup and self.score[1 - team] - self.score[team] >= COMEBACK_GAP

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
        if self.warmup:
            self._warm_step()
            return
        for f in self.fighters:
            f.prev_pos = (f.x, f.y)
            self._update_moves(f)
            if f.super_cd > 0 and self.frame % 2 == 0 and self.comeback(f.team):
                f.super_cd -= 1                 # perdendo de muito: o SUPER volta 50% mais rápido
        for side in (0, 1):
            if self.lids[side] > 0:
                self.lids[side] -= 1
        for hoop in self.hoops:
            hoop.shake = max(0, hoop.shake - 1)
            hoop.fire = any(f.fire_timer > 0 and self.hoop_of(f.team) == hoop.side for f in self.fighters)
        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]
        for f, ctrl in self.controllers.items():
            if self.freeze or f.stunned:
                f.steer(0, 0)
                f.protecting = False
            elif hasattr(ctrl, "axis"):         # teclado, controle ou celular
                self._human(f, ctrl)
            else:
                ctrl.update(f, self)
            if f.glue_timer > 0 and not f.stunned and not self.freeze:
                self._glue_steer(f)
            f.update(self)
            f.update_stamina()
        for i, a in enumerate(self.fighters):
            for b in self.fighters[i + 1:]:
                if a.magic_timer > 0 or b.magic_timer > 0:
                    continue                    # drible mágico: atravessa os marcadores
                _separate(a, b)
                self.arena.resolve(a)
                self.arena.resolve(b)
        if self.freeze:
            self.freeze -= 1
            if self.freeze == 0:
                self._tip_off()
            return
        self._power_rules()
        for f in self.fighters:
            if f.steal_timer > 0:
                self._check_steal(f)
            if f.jump or f.dunking or f.hang:
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

    def _glue_steer(self, f):
        """Marcação Colada: corre grudado em quem está com a bola."""
        owner = self.holder
        if owner is None or owner.team == f.team:
            return
        dx, dy = owner.x - f.x, owner.y - f.y
        d = math.hypot(dx, dy)
        if d > 4:
            f.steer(dx / d, dy / d)
        f.sprint_held = f.stamina > 0.1

    def _power_rules(self):
        """Regras dos poderes que valem a cada quadro: marcação colada, moto, hack."""
        owner = self.holder
        for f in self.fighters:
            if f.glue_timer > 0 and owner is not None and owner.team != f.team and not f.stunned:
                # colado, rouba logo (não na hora): dá tempo de passar, fintar ou proteger
                if (f.distance_to(owner) < f.radius + owner.radius + 10 and not owner.dunking
                        and owner.magic_timer <= 0 and owner.exo_timer <= 0 and not owner.protecting
                        and owner.feint_timer <= 0 and random.random() < GLUE_STEAL):
                    self.release_ball(owner, 30)
                    self._give(f)
                    f.steals += 1
                    f.glue_timer = 0                    # a marcação colada rouba uma vez só
                    self.popup(f.x, f.y - 74, "ROUBOU", theme.BRASS)
                    owner = f
            if f.moto_timer > 0:
                for foe in self.foes_of(f):
                    if f.distance_to(foe) > f.radius + foe.radius + 6 or foe.stunned:
                        continue
                    if foe.giant_timer > 0:
                        f.moto_timer = 0
                        f.stun(40)
                        self.popup(f.x, f.y - 90, "BATEU", theme.BONE)
                        self.camera.shake(5)
                        break
                    if foe.stun(45):
                        self.popup(foe.x, foe.y - 74, "ATROPELADO", theme.BONE)
                        self.camera.shake(3)
                        if self.holder is foe:
                            self.release_ball(foe, 30)
                            self._give(f)
                            owner = f
        if owner is not None and owner.hacked:
            self.release_ball(owner, 40)
            self.ball.vz = 2.0

    def _power_glow(self, f):
        """Brilho dos poderes que duram (para todo mundo ver quem está com o quê)."""
        if self.frame % 3:
            return
        glow = None
        if f.glue_timer > 0:
            glow = (150, 196, 255)
        elif f.wall_timer > 0:
            glow = (236, 230, 220)
        elif f.hot_timer > 0:
            glow = (255, 150, 50)
        elif f.ghost_timer > 0:
            glow = (210, 210, 255)
        elif f.frost_timer > 0:
            glow = (200, 236, 250)
        elif f.magic_timer > 0:
            glow = (255, 226, 120)
        elif f.nose_timer > 0:
            glow = (150, 236, 150)
        if glow is not None:
            self.burst(f.x + random.uniform(-12, 12), f.y - random.uniform(0, 44) - f.lift, glow, 1,
                       speed=1, gravity=-0.03, size=3)

    def alley_oop(self, user, mate):
        """Alley-oop Trovão: passe alto e forte para o companheiro, que sobe e crava."""
        vx, vy = mate.x - mate.prev_pos[0], mate.y - mate.prev_pos[1]
        dist = math.hypot(mate.x - user.x, mate.y - user.y)
        frames = max(14, round(dist / (PASS_SPEED * 1.3)))
        tx, ty = mate.x + vx * frames, mate.y + vy * frames
        user.jump_shot = False
        self._launch(user, tx, ty, CATCH_HEIGHT + 30, frames, z0=40 + user.lift)
        self.alley = {"from": user, "to": mate, "age": 0, "hit": set()}
        self.catch_lock = 5
        self.burst(self.ball.x, self.ball.y - 40, (255, 236, 120), 12, speed=5)
        self.camera.shake(5)
        return True

    def _update_alley(self):
        """O passe do alley-oop derruba quem entra na frente; o Gigante intercepta."""
        alley, ball = self.alley, self.ball
        alley["age"] += 1
        if alley["age"] > 150 or (ball.z <= 0.5 and ball.vz <= 0):
            self.alley = None
            return
        for foe in self.foes_of(alley["from"]):
            if foe in alley["hit"]:
                continue
            d = math.hypot(foe.x - ball.x, foe.y - ball.y)
            if foe.giant_timer > 0 and d < foe.radius + 30 and ball.z < 140:
                self.grab(foe)
                self.popup(foe.x, foe.y - 90, "INTERCEPTOU", theme.BRASS)
                return
            if d < foe.radius + 14 and ball.z < 110 and foe.stun(45):
                alley["hit"].add(foe)
                self.popup(foe.x, foe.y - 74, "DERRUBADO", theme.BONE)
                self.burst(foe.x, foe.y - 30, (255, 236, 120), 10, speed=4)

    def _faro_pull(self):
        """Faro de Cesta: a bola solta perto vem para a mão do Matador."""
        ball = self.ball
        for f in self.fighters:
            if f.nose_timer <= 0 or f.stunned or ball.z > 130:
                continue
            d = math.hypot(f.x - ball.x, f.y - ball.y)
            if 10 < d < 280:
                ball.vx += (f.x - ball.x) / d * 0.45
                ball.vy += (f.y - ball.y) / d * 0.45
                speed = math.hypot(ball.vx, ball.vy)
                if speed > 9:
                    ball.vx, ball.vy = ball.vx / speed * 9, ball.vy / speed * 9
                return

    def _update_moves(self, f):
        """Pulo (arco do desenho e barrinha), enterrada, finta, roubo e pegando fogo."""
        if not f.dunking:
            f.spin = 0                           # a cambalhota acaba no aro (ou no toco)
        if f.hang:
            # Pendurado no Aro: balança segurando no aro e depois cai
            f.hang -= 1
            hx, hy = self.hoop_pos(self.hoop_of(f.team))
            ux, uy = unit(f.dunk_to[0] - hx, f.dunk_to[1] - hy)
            f.x, f.y = hx + ux * (Court.RIM_R + 6), hy + uy * (Court.RIM_R + 6)
            f.vx = f.vy = 0.0
            f.lift = Court.RIM_Z - 48 + math.sin(f.hang * 0.5) * 3      # as mãos no aro
            if f.hang == 0:
                f.jump = JUMP_FRAMES // 2
        elif f.dunking:
            f.dunking -= 1
            k = 1 - f.dunking / f.dunk_total
            (x0, y0), (x1, y1) = f.dunk_from, f.dunk_to
            f.x, f.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            f.vx = f.vy = 0.0
            peak = 110 if (f.fly_dunk or f.alley_dunk) else JUMP_H
            f.lift = peak * math.sin(k * math.pi / 2) if k < 0.85 else peak * (1 - (k - 0.85) * 2)
            if (f.fly_dunk or f.alley_dunk) and self.frame % 3 == 0:
                self.burst(f.x, f.y + 18, (84, 162, 222), 2, speed=1)
            if f.dunk_move == "GIRO 360" and k < 0.9:
                a = k * math.tau / 0.9           # uma volta inteira no ar
                hx, hy = self.hoop_pos(self.hoop_of(f.team))
                bx, by = unit(hx - f.x, hy - f.y)
                c, s_ = math.cos(a), math.sin(a)
                f.facing = (bx * c - by * s_, bx * s_ + by * c)
            elif f.dunk_move == "CAMBALHOTA":
                f.spin = -360 * min(1.0, k / 0.85) * (1 if f.facing[0] >= 0 else -1)
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
        for name in ("feint_timer", "steal_timer", "steal_cd", "glue_timer", "wall_timer", "hot_timer",
                     "ghost_timer", "frost_timer"):
            if getattr(f, name) > 0:
                setattr(f, name, getattr(f, name) - 1)
        if f.meter_flash is not None:
            timing, half, frames = f.meter_flash
            f.meter_flash = (timing, half, frames - 1) if frames > 1 else None
        if f.moto_timer > 0 and f.hack_timer > 0:
            f.hack_timer = f.stun_timer = 0     # de moto, o hack não pega
        if f.hacked:
            f.glue_timer = f.wall_timer = 0
        self._power_glow(f)
        if f.fire_timer > 0:
            f.super_cd = 0                      # pegando fogo: o SUPER recarrega na hora
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
        if inp.pressed("super") and self.warmup:
            f.warm_ready = not f.warm_ready       # no aquecimento, SUPER diz "estou pronto"
            self.popup(f.x, f.y - 90, "PRONTO!" if f.warm_ready else "AINDA NÃO", theme.MOSS)
            self.assets.play("confirm" if f.warm_ready else "cancel", 0.3)
        elif inp.pressed("super") and not self.use_power(f):
            self.assets.play("cancel", 0.2)

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
            if owner.dunking and owner.dunk_move == "MOINHO":
                # moinho: a bola dá uma volta grande com o braço esticado
                a = (1 - owner.dunking / owner.dunk_total) * math.tau * 1.25
                ball.x, ball.y = owner.x + fx * 30 * math.cos(a), owner.y + 2
                ball.z = owner.lift + config.BODY_HEIGHT + 30 * math.sin(a) - 4
            elif owner.jump or owner.dunking:
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
        if self.alley is not None:
            self._update_alley()
            if self.holder is not None:
                return
        self._steer_pass()
        if self.warmup:
            self._catch()                       # aquecimento: sem toco e sem puxar o rebote
            return
        if self._block():
            return
        self._faro_pull()
        self._rebound_pull()
        self._catch()

    def _steer_pass(self):
        """Passe teleguiado: a cada quadro a bola refaz a trajetória até o companheiro (pela frente
        dele, se estiver correndo). Quem estiver no caminho ainda pode cortar o passe."""
        p = self.pass_to
        if p is None:
            return
        mate, ball = p["to"], self.ball
        p["frames"] -= 1
        if p["frames"] <= 0 or mate.stunned or self.shot is not None or self.alley is not None:
            self.pass_to = None
            return
        mvx, mvy = _run_velocity(mate)
        speed = max(p["speed"], math.hypot(mvx, mvy) * 1.8)
        dist = math.hypot(mate.x - ball.x, mate.y - ball.y)
        frames = max(2, round(dist / speed))
        tx, ty = mate.x + mvx * frames, mate.y + mvy * frames
        ball.vx, ball.vy, ball.vz = shot_velocity(ball.x, ball.y, ball.z, tx, ty, 30 + mate.lift, frames,
                                                  config.GRAVITY)

    def _block_dunk(self):
        if self.warmup:
            return False
        """Toco na enterrada: quem está no ar encosta em quem voa para o aro e a bola sai."""
        owner = self.holder
        if owner is None or not owner.dunking or owner.fly_dunk or owner.alley_dunk:
            return False                        # a voadora e a do alley-oop passam por cima
        for f in self.foes_of(owner):
            if self._reach_lift(f) < 10 or f.distance_to(owner) > f.radius + owner.radius + self._block_reach(f):
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

    @staticmethod
    def _reach_lift(f):
        """Altura do pulo para o toco; o Gigante alcança sem pular."""
        return max(f.lift, 30) if f.giant_timer > 0 else f.lift

    @staticmethod
    def _block_reach(f):
        return BLOCK_REACH + f.power.block_bonus + (16 if f.giant_timer > 0 else 0)

    def _toco(self, f, ball, text="TOCO!"):
        f.blocks += 1
        self.popup(f.x, f.y - 90, text, theme.BRASS)
        self.burst(ball.x, ball.y - ball.z, (236, 230, 220), 10, speed=4)
        self.camera.shake(4)
        self.hit_pause(4)
        self.assets.play("toco", 0.6)
        self.assets.play("torcida", 0.2)

    def _block(self):
        """Toco: quem está no ar encosta no arremesso (ou na enterrada) do adversário."""
        ball, shot = self.ball, self.shot
        if shot is None or shot.get("touched") or shot.get("blocked"):
            return False
        hx, hy = self.hoop_pos(shot["side"])
        for f in self.fighters:
            if f.team == shot["team"] or f.stunned:
                continue
            if shot.get("ghost") and not f.power.ghost_proof:
                continue                        # bola fantasma: atravessa mãos e tocos
            if (f.wall_timer > 0 and ball.vz < 0 and math.hypot(ball.x - hx, ball.y - hy) < 110
                    and math.hypot(f.x - hx, f.y - hy) < 260):
                # Toco Voador: o Paredão sobe e tira a bola antes do aro
                f.wall_timer = 0
                f.jump = 1
                ux, uy = unit(ball.x - hx, ball.y - hy) if math.hypot(ball.x - hx, ball.y - hy) > 1 else (0.0, 1.0)
                ball.vx, ball.vy, ball.vz = ux * 6, uy * 6, 3.0
                shot["blocked"] = True
                self.shot = None
                self._toco(f, ball, "TOCO VOADOR!")
                return True
            lift = self._reach_lift(f)
            if lift < 10:
                continue
            reach = lift + config.BODY_HEIGHT + 64
            d = math.hypot(f.x - ball.x, f.y - ball.y)
            if d < f.radius + ball.radius + self._block_reach(f) and ball.z < reach:
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
            self.assets.play("tabela", 0.4)
        if (self.lids[side] > 0 and z0 >= Court.RIM_Z > ball.z - ball.radius
                and math.hypot(ball.x - hx, ball.y - hy) < Court.RIM_R + ball.radius):
            # Tampa no Aro: a bola bate na tampa e volta
            ux, uy = unit(ball.x - hx, ball.y - hy) if math.hypot(ball.x - hx, ball.y - hy) > 1 \
                else ((1.0, 0.0) if side == 0 else (-1.0, 0.0))
            ball.z = Court.RIM_Z + ball.radius
            ball.vz = abs(ball.vz) * 0.5 + 2.0
            ball.vx, ball.vy = ux * 3.0, uy * 3.0
            self.shot_clock = 0
            if self.shot is not None:
                self.shot["touched"] = True
            self.assets.play("tabela", 0.5)
            self.burst(hx, hy - Court.RIM_Z, (150, 226, 240), 6, speed=3)
            return
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
                self.assets.play("aro", 0.35)
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
        alley = self.alley
        best, best_d = None, 1e9
        for f in self.fighters:
            if f.stunned or f in self.no_catch or (self._only is not None and f is not self._only):
                continue
            high = CATCH_HEIGHT + f.lift + (40 if f.giant_timer > 0 else 0)
            reach = 12 + (14 if f.giant_timer > 0 else 0) + (12 if f.nose_timer > 0 else 0)
            if alley is not None:
                if f is alley["to"]:
                    high, reach = high + 70, reach + 16    # o alley-oop vai alto, na mão dele
                elif ball.z > CATCH_HEIGHT * 0.6:
                    continue
            if ball.z >= high:
                continue                     # no pulo, pega mais alto (rebote)
            d = math.hypot(f.x - ball.x, f.y - ball.y)
            if d < f.radius + ball.radius + reach and d < best_d:
                best, best_d = f, d
        if best is not None and alley is not None and best is alley["to"]:
            self.alley = None
            self._give(best)
            hx, hy = self.hoop_pos(self.hoop_of(best.team))
            if math.hypot(hx - best.x, hy - best.y) < Court.THREE_R + 120:
                self.dunk(best, alley=True)
                self.popup(best.x, best.y - 110, "ALLEY-OOP!", theme.BRASS)
            return
        if best is not None:
            self.alley = None
            if self.shot is not None and best.team != self.shot["team"]:
                self.popup(best.x, best.y - 74, "REBOTE", theme.BONE)
            self._give(best)

    def _basket(self, side):
        team = next(t for t, s in self.attack.items() if s == side)
        shot = self.shot
        if self.warmup:
            # aquecimento: a cesta não conta, só comemora um pouco
            hx, hy = self.hoop_pos(side)
            shooter = shot["shooter"] if shot is not None else None
            if shooter is not None:
                shooter.warm_makes += 1
                self.popup(hx, hy - Court.RIM_Z - 30, f"{shooter.label} · {shooter.warm_makes}", theme.BONE)
            self.burst(hx, hy - Court.RIM_Z, theme.TEAM_COLORS[team], 10, speed=4, gravity=0.12, size=3)
            self.assets.play("rede", 0.35)
            self.shot = None
            return
        points = 3 if shot is not None and shot["three"] and shot["team"] == team else 2
        self.score[team] += points
        scorer = shot["shooter"] if shot is not None and shot["team"] == team else None
        if scorer is not None:
            scorer.points += points
            if shot.get("dunk"):
                scorer.dunks += 1
        title = "CESTA DE 3!" if points == 3 else "CESTA!"
        self.banner = (title, scorer.label if scorer else "", team)
        self.banner_age = 0
        self._streak(scorer, team)
        hx, hy = self.hoop_pos(side)
        self.burst(hx, hy - Court.RIM_Z, theme.TEAM_COLORS[team], 26, speed=6, gravity=0.12, size=4)
        self.burst(hx, hy - Court.RIM_Z, theme.BONE, 12, speed=4, gravity=0.12, size=3)
        self.camera.shake(5)
        self.hit_pause(6)
        self.assets.play("rede", 0.5)
        clean = shot is not None and not shot.get("touched")      # chuá: nem encostou no aro
        self.assets.play("torcida", 0.55 if points == 3 or clean or (shot or {}).get("dunk") else 0.35)
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
            self.assets.play("fogo", 0.6)
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
            self.assets.play("buzina", 0.4)
            self.freeze = 90
        elif self.score[0] != self.score[1]:
            self._end(0 if self.score[0] > self.score[1] else 1)
        else:
            self.overtime = True
            self.banner = ("EMPATE", "PRÓXIMA CESTA VENCE", None)
            self.banner_age = 0
            self.assets.play("buzina", 0.4)
            self.freeze = 90

    def _turnover(self, f):
        """10 segundos com a bola sem arremessar: ela vai para o adversário mais perto."""
        self.popup(f.x, f.y - 74, f"{SHOT_CLOCK} SEGUNDOS", theme.BRASS)
        self._release(f, 40)
        foes = self.foes_of(f)
        if foes:
            self._give(min(foes, key=lambda o: o.distance_to(f)))
        self.assets.play("apito", 0.3)

    # ── aquecimento ──────────────────────────
    def _start_warmup(self):
        """Cada time no lado da cesta que ataca, cada jogador com a sua bola."""
        self.warmup = WARMUP_SECONDS * config.FPS
        main = self.ball
        self.warm = {}
        for f in self.fighters:
            hx, hy = self.hoop_pos(self.hoop_of(f.team))
            inward = 1 if hx < Court.W / 2 else -1
            f.x = hx + inward * random.uniform(260, 520)
            f.y = hy + random.uniform(-260, 260)
            f.prev_pos = (f.x, f.y)
            f.facing = (float(-inward), 0.0)
            f.warm_ready = False
            f.warm_makes = 0
            f.warm_spot = None
            f.warm_release = 0
            ball = BasketBall(f.x, f.y)
            self.warm[f] = {"ball": ball, "holder": f, "shot": None, "no_catch": {}, "catch_lock": 0,
                            "alley": None}
        self.main_ball = main
        self.banner = ("AQUECIMENTO", "SUPER: PRONTO", None)
        self.banner_age = 0

    def _swap_in(self, f):
        for k in WARM_STATE:
            setattr(self, k, self.warm[f][k])
        self._only = f

    def _swap_out(self, f):
        for k in WARM_STATE:
            self.warm[f][k] = getattr(self, k)
        self._only = None

    def _warm_half(self, f):
        """No aquecimento cada time fica na sua metade da quadra."""
        mid = Court.W / 2
        if self.hoop_of(f.team) == 1:
            f.x = max(f.x, mid + 30)
        else:
            f.x = min(f.x, mid - 30)

    def _warm_step(self):
        self.warmup -= 1
        for hoop in self.hoops:
            hoop.shake = max(0, hoop.shake - 1)
        for effect in self.effects:
            effect.update(self)
        self.effects = [e for e in self.effects if e.alive]
        for f in self.fighters:
            self._swap_in(f)
            f.prev_pos = (f.x, f.y)
            self._update_moves(f)
            ctrl = self.controllers[f]
            if f.stunned:
                f.steer(0, 0)
            elif hasattr(ctrl, "axis"):
                self._human(f, ctrl)
            else:
                self._warm_ai(f)
            f.update(self)
            f.update_stamina()
            if f.jump or f.dunking or f.hang:
                f.steer(0, 0)
            f.protecting = False
            self._warm_half(f)
            self._update_ball()
            ball = self.ball
            mid = Court.W / 2
            wrong = ball.x > mid if self.hoop_of(f.team) == 0 else ball.x < mid
            if self.holder is None and wrong and ball.z < 20:
                ball.reset(f.x, f.y)            # a bola que fugiu para o outro lado volta para a mão
                self._give(f)
            self._swap_out(f)
        for i, a in enumerate(self.fighters):
            for b in self.fighters[i + 1:]:
                _separate(a, b)
                self.arena.resolve(a)
                self.arena.resolve(b)
        humans = [f for f in self.fighters if not f.is_cpu]
        if self.warmup <= 0 or (humans and all(f.warm_ready for f in humans)):
            self._end_warmup()

    def _warm_ai(self, f):
        """CPU no aquecimento: anda até um lugar, arremessa (ou enterra) e vai buscar a bola."""
        ball = self.ball
        hx, hy = self.hoop_pos(self.hoop_of(f.team))
        if self.holder is f:
            if f.jump_shot:
                f.steer(0, 0)
                if f.jump >= f.warm_release:
                    self.release_shot(f)
                return
            if f.jump or f.dunking or f.hang:
                return
            if f.warm_spot is None:
                inward = 1 if hx < Court.W / 2 else -1
                dist = random.choice((160, 380, 520, 720))
                a = random.uniform(-1.2, 1.2)
                f.warm_spot = (hx + inward * math.cos(a) * dist, hy + math.sin(a) * dist * 0.8)
            tx, ty = f.warm_spot
            d = math.hypot(tx - f.x, ty - f.y)
            if d > 24:
                f.steer((tx - f.x) / d, (ty - f.y) / d)
                return
            f.steer(0, 0)
            f.facing = unit(hx - f.x, hy - f.y)
            f.warm_spot = None
            if self.start_shot(f) and f.jump_shot:
                f.warm_release = round(JUMP_FRAMES * random.uniform(0.42, 0.58))
            return
        if ball.z > 120:
            f.steer(0, 0)
            return
        tx, ty = ball.x + ball.vx * 8, ball.y + ball.vy * 8
        d = math.hypot(tx - f.x, ty - f.y)
        f.steer(*((tx - f.x) / d, (ty - f.y) / d) if d > 8 else (0, 0))

    def _end_warmup(self):
        self.warmup = 0
        self.warm = {}
        self._only = None
        self.ball = self.main_ball
        self.holder = None
        self.shot = None
        self.no_catch = {}
        self.catch_lock = 0
        self.alley = None
        for f in self.fighters:
            f.meter_flash = None
            f.streak = f.fire_timer = 0
        self.banner = ("BOLA AO ALTO", "VALENDO!", None)
        self.banner_age = 0
        self.assets.play("apito", 0.4)
        self._tip_off()

    def _tip_off(self):
        """Bola ao alto no meio da quadra; cada time no seu lado (no 2º tempo, lados trocados)."""
        self.ball.reset(Court.W / 2, Court.MID_Y)
        self.ball.z, self.ball.vz = 60.0, 6.0
        self.holder = None
        self.shot = None
        self.pass_to = None
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
            f.fly_dunk = f.alley_dunk = False
            f.hang, f.spin = 0, 0
            hx, _ = self.hoop_pos(self.hoop_of(f.team))
            f.facing = (1.0, 0.0) if hx > f.x else (-1.0, 0.0)
        self.alley = None

    def _end(self, team):
        self.result_team = team
        self.ending = config.DEATH_ANIM_FRAMES + 30
        self.holder = None
        self.assets.play("buzina", 0.45)
        self.assets.play("torcida", 0.5)
        self.assets.stop_music(1800)

    def _finish(self):
        team = self.result_team
        winners = [f for f in self.fighters if f.team == team]
        lines = [("PLACAR", f"{self.score[0]} x {self.score[1]}")]
        for f in sorted(self.fighters, key=lambda f: (f.team, f.slot)):
            lines.append((who(f), stat_line(f)))
        best = max(self.fighters, key=lambda f: (f.points + 2 * (f.blocks + f.steals), f.team == team))
        lines.append(("DESTAQUE", who(best)))
        self.result = Result(f"TIME {theme.TEAM_NAMES[team]} VENCEU", theme.TEAM_COLORS[team], winners,
                             lines, score=tuple(self.score))
        self.finished = True

    # ── desenho ──────────────────────────────
    def draw_under(self, view, cam):
        p = self.holder
        if p is not None and not self.warmup:
            rect = pygame.Rect(0, 0, 54, 18)
            rect.center = (round(p.x - cam.x), round(p.y - cam.y) + 22)
            pygame.draw.ellipse(view, (232, 232, 220), rect, 1)

    def draw_over_walls(self, view, cam):
        """Tampa no Aro: um disco por cima do aro tampado."""
        for side in (0, 1):
            frames = self.lids[side]
            if frames <= 0 or (frames < 40 and (frames // 4) % 2 == 0):
                continue
            hx, hy = self.hoop_pos(side)
            rect = pygame.Rect(0, 0, Court.RIM_R * 2 + 10, 14)
            rect.center = (round(hx - cam.x), round(hy - Court.RIM_Z - cam.y))
            pygame.draw.ellipse(view, (20, 40, 56), rect)
            pygame.draw.ellipse(view, (150, 226, 240), rect, 2)

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
        W, H = config.SCREEN_W, config.SCREEN_H
        return [pygame.Rect(W // 2 - 166, 0, 332, 96), pygame.Rect(0, H - 52, W, 52)]   # placar e SUPER
