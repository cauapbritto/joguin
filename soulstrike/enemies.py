"""Inimigos da campanha: criaturas, a Patrulha Cinza (capítulo 2) e as almas corrompidas
(versões sombrias dos heróis).

Todo inimigo é um Fighter do time 1 com um "cérebro" próprio (subclasse de EnemyAI).
A partida só chama ``ai.update(inimigo, partida)``; cada criatura decide do seu jeito.
"""
import math
import random
from dataclasses import dataclass

import pygame

from . import config
from .ai import FighterAI
from .data import CHARACTERS, CharacterStats, WeaponStats
from .entities import Entity, hostile

SHADOW_TINT = (86, 66, 108)          # almas corrompidas: quase pretas, puxando para o roxo
TINTS = {"aryel": (66, 48, 86),      # Aryel Corrompido é a sombra mais escura de todas
         "borba_exo": (74, 60, 96)}  # Borba Jr Corrompido: placas pretas com veios roxos
SHADOW_KEEP = 0.22                   # quanto da cor original sobra (para ainda reconhecer o herói)
SHADOW_AURA = (170, 90, 230)         # cor dos textos e avisos das sombras
SHADOW_RIM = (104, 34, 160)          # contorno que pulsa em volta delas
SHADOW_EYES = (255, 52, 64)
SMOKE = ((26, 8, 36), (46, 14, 64), (12, 4, 18), (74, 22, 104))


@dataclass(frozen=True)
class EnemyStats(CharacterStats):
    radius: int = config.PLAYER_RADIUS
    elite: bool = False             # conta como inimigo forte (escala de outro jeito com mais jogadores)
    armed: bool = False             # desenha a arma na mão
    knock_resist: float = 0.0       # 1 = não é empurrado
    drop_chance: float = 0.12       # chance de deixar um item ao morrer


def _w(name, kind, damage, speed=0, cooldown=16, reach=0):
    return WeaponStats(name, kind, damage, bullet_speed=speed, cooldown=cooldown, reach=reach)


CREATURES = {
    "diabrete": EnemyStats(
        "diabrete", "Diabrete", 30, 3.3, (214, 72, 64), "", "",
        (_w("Garras", "melee", 6, cooldown=40, reach=28),), "diabrete",
        radius=12, drop_chance=0.10),
    "esqueleto": EnemyStats(
        "esqueleto", "Esqueleto Arqueiro", 44, 2.3, (214, 208, 190), "", "",
        (_w("Arco", "ranged", 8, speed=7.5, cooldown=80),), "esqueleto",
        armed=True, drop_chance=0.14),
    "golem": EnemyStats(
        "golem", "Golem", 220, 1.5, (128, 118, 104), "", "",
        (_w("Punhos", "melee", 14, cooldown=70, reach=46),), "golem",
        radius=22, elite=True, knock_resist=0.85, drop_chance=0.6),
    # Patrulha Cinza (capítulo 2, Lag Lobby): todo golpe é avisado por uma luz vermelha
    "drone": EnemyStats(
        "drone", "Drone", 26, 3.4, (226, 70, 60), "", "",
        (_w("Hélice", "melee", 5, cooldown=40, reach=24),), "drone",
        radius=12, drop_chance=0.10),
    "miliciano": EnemyStats(
        "miliciano", "Miliciano", 50, 2.4, (255, 96, 72), "", "",
        (_w("Fuzil", "ranged", 6, speed=9, cooldown=8),), "miliciano",
        armed=True, drop_chance=0.14),
    "torreta": EnemyStats(
        "torreta", "Torreta", 70, 0.0, (255, 80, 64), "", "",
        (_w("Metralhadora", "ranged", 6, speed=10, cooldown=6),), "torreta",
        radius=18, knock_resist=1.0, drop_chance=0.16),
    "miliciano_exo": EnemyStats(
        "miliciano_exo", "Miliciano de Exo", 240, 2.2, (140, 150, 170), "", "",
        (_w("Punho do Exo", "melee", 14, cooldown=60, reach=44),), "miliciano_exo",
        radius=20, elite=True, knock_resist=0.85, drop_chance=0.6),
}
BIG_KINDS = ("golem", "chefe", "miliciano_exo")       # portal e lugar de nascer maiores
PATROL_RED = (255, 60, 52)                           # luz de aviso da Patrulha Cinza


def shadow_stats(char_key):
    """Alma corrompida: o mesmo herói (com a mesma habilidade), mais escuro e um pouco mais fraco."""
    base = next(c for c in CHARACTERS if c.key == char_key)
    return EnemyStats(
        base.key, f"{base.name} Sombrio", round(base.max_hp * 0.8), base.speed * 0.95, SHADOW_AURA,
        base.ability_name, base.ability_desc, base.weapons, base.sprite,
        elite=True, armed=True, knock_resist=0.3, drop_chance=1.0)


def tint_sprites(sprite_set, tint=SHADOW_TINT, eyes=SHADOW_EYES):
    """Versão sombria de um herói: tira quase toda a cor, escurece puxando para o roxo
    e acende de vermelho as cores dos olhos (e óculos/viseira) que a folha de sprite indica."""
    from .assets import SpriteSet
    halo = tuple(c // 2 for c in eyes)
    poses = {d: {kind: [_shadow(img, tint, eyes, halo, sprite_set.glow) for img in imgs]
                 for kind, imgs in kinds.items()}
             for d, kinds in sprite_set.poses.items()}
    return SpriteSet(poses=poses, hands=sprite_set.hands)


def _shadow(img, tint, eyes, halo, glow):
    # cinza com um resto da cor original por cima
    dark = pygame.transform.grayscale(img)
    color = img.copy()
    color.set_alpha(round(255 * SHADOW_KEEP))
    dark.blit(color, (0, 0))
    dark.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
    body = pygame.mask.from_surface(img)
    dark.blit(body.to_surface(setcolor=(10, 2, 18, 0), unsetcolor=(0, 0, 0, 0)), (0, 0),
              special_flags=pygame.BLEND_RGBA_ADD)
    if not glow:
        return dark
    # olhos acesos (só na metade de cima, onde fica a cabeça), com um brilho em volta
    w, h = img.get_size()
    lit = pygame.mask.Mask((w, h))
    for col in glow:
        lit.draw(pygame.mask.from_threshold(img, (*col, 255), (1, 1, 1, 255)), (0, 0))
    lit.erase(pygame.mask.Mask((w, h - h // 2), fill=True), (0, h // 2))
    if lit.count():
        ring = pygame.mask.Mask((w, h))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            ring.draw(lit, (dx, dy))
        ring.erase(lit, (0, 0))
        ring = ring.overlap_mask(body, (0, 0))
        dark.blit(ring.to_surface(setcolor=(*halo, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
        dark.blit(lit.to_surface(setcolor=(*eyes, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    return dark


# ─────────────────────────────────────────────
#  Efeitos dos inimigos
# ─────────────────────────────────────────────
class Shockwave(Entity):
    """Onda de choque no chão (pancada do Golem e do chefão): machuca, empurra e atordoa."""

    LIFE = 26

    def __init__(self, owner, x, y, radius, damage, stun=30, color=(214, 170, 110)):
        super().__init__(x, y)
        self.owner = owner
        self.radius = radius
        self.damage = damage
        self.stun_frames = stun
        self.color = color
        self.age = 0
        self.applied = False

    def update(self, match):
        if not self.applied:
            self.applied = True
            for f in match.fighters:
                if not hostile(self.owner, f) or not f.alive_in_match:
                    continue
                if math.hypot(f.x - self.x, f.y - self.y) > self.radius + f.radius:
                    continue
                if f.take_damage(self.damage, self.x, self.y, attacker=self.owner, match=match):
                    f.stun(self.stun_frames)
            match.burst(self.x, self.y + 10, self.color, 30, speed=7)
            match.dust(self.x, self.y + 18, 16)
            match.camera.shake(9)
            match.assets.play("explosion", 0.5)
        self.age += 1
        if self.age >= self.LIFE:
            self.alive = False

    def draw(self, surf, camera):
        t = self.age / self.LIFE
        r = int(self.radius * (0.25 + 0.75 * t))
        cx, cy = round(self.x - camera.x), round(self.y + 16 - camera.y)
        layer = pygame.Surface((r * 2 + 8, r + 8), pygame.SRCALPHA)
        alpha = int(200 * (1 - t))
        rect = pygame.Rect(4, 4, r * 2, r)
        pygame.draw.ellipse(layer, (*self.color, alpha // 4), rect)
        pygame.draw.ellipse(layer, (*self.color, alpha), rect, 4)
        surf.blit(layer, (cx - r - 4, cy - r // 2 - 4))


class AimLine(Entity):
    """Linha de mira no chão: o rasante do drone, o tiro da torreta, a investida do exo e o
    Canhão de Pulso do chefão passam exatamente por aqui. ``grow``: vai engrossando até o fim."""

    def __init__(self, x, y, dx, dy, length, frames, color=PATROL_RED, width=2, grow=0, follow=None):
        super().__init__(x, y)
        self.dx, self.dy = dx, dy
        self.length = length
        self.frames = self.left = max(1, frames)
        self.color = color
        self.width = width
        self.grow = grow
        self.follow = follow                 # quem segura a mira (a linha anda junto); morto = some

    @property
    def progress(self):
        return 1 - self.left / self.frames

    def update(self, match):
        if self.follow is not None:
            if not self.follow.alive_in_match:
                self.alive = False
                return
            self.x, self.y = self.follow.x, self.follow.y
        self.left -= 1
        if self.left <= 0:
            self.alive = False

    def end(self, arena=None):
        """Onde a linha acaba (na primeira parede, se a arena vier junto)."""
        x1, y1 = self.x + self.dx * self.length, self.y + self.dy * self.length
        if arena is not None:
            steps = int(self.length // 12)
            for k in range(1, steps + 1):
                px, py = self.x + self.dx * k * 12, self.y + self.dy * k * 12
                if not arena.is_free(px, py, 2):
                    return px, py
        return x1, y1

    def draw(self, surf, camera):
        t = self.progress
        x0, y0 = self.x - camera.x, self.y - 10 - camera.y
        x1, y1 = x0 + self.dx * self.length, y0 + self.dy * self.length
        width = max(1, round(self.width + self.grow * t))
        blink = (self.left // 4) % 2 == 0 or t > 0.7
        color = self.color if blink else tuple(c // 2 for c in self.color)
        if width >= 4:
            layer_w = width * 3
            pygame.draw.line(surf, tuple(c // 3 for c in self.color), (x0, y0), (x1, y1), layer_w)
        pygame.draw.line(surf, color, (x0, y0), (x1, y1), width)
        pygame.draw.circle(surf, (255, 230, 220), (round(x0), round(y0)), max(2, width // 2 + 1))


class Portal(Entity):
    """Fenda sombria de onde sai um inimigo depois de alguns quadros."""

    FRAMES = 60

    def __init__(self, x, y, kind, delay=0):
        super().__init__(x, y)
        self.kind = kind
        self.delay = delay
        self.age = 0
        self.radius = 30 if kind in BIG_KINDS else 22

    @property
    def ready(self):
        return self.age >= self.delay + self.FRAMES

    def update(self, match):
        self.age += 1
        if self.age > self.delay and self.age % 4 == 0:
            a = random.uniform(0, math.tau)
            match.burst(self.x + math.cos(a) * self.radius, self.y + 12 + math.sin(a) * self.radius * 0.4,
                        SHADOW_AURA, 1, speed=1.5)

    def draw(self, surf, camera):
        if self.age <= self.delay:
            return
        t = min(1.0, (self.age - self.delay) / 20)
        rx = round(self.radius * t)
        ry = max(2, round(self.radius * 0.42 * t))
        cx, cy = round(self.x - camera.x), round(self.y + 14 - camera.y)
        layer = pygame.Surface((rx * 2 + 12, ry * 2 + 12), pygame.SRCALPHA)
        c = (rx + 6, ry + 6)
        spin = self.age * 0.2
        pygame.draw.ellipse(layer, (20, 8, 32, 230), (6, 6, rx * 2, ry * 2))
        pygame.draw.ellipse(layer, (*SHADOW_AURA, 200), (6, 6, rx * 2, ry * 2), 2)
        for k in range(6):
            a = spin + k * math.tau / 6
            px, py = c[0] + math.cos(a) * rx * 0.7, c[1] + math.sin(a) * ry * 0.7
            layer.fill((230, 190, 255, 220), (round(px) - 1, round(py) - 1, 2, 2))
        surf.blit(layer, (cx - rx - 6, cy - ry - 6))


# ─────────────────────────────────────────────
#  Cérebros
# ─────────────────────────────────────────────
class EnemyAI:
    """Base: escolhe o jogador vivo mais perto e persegue, contornando paredes."""

    reaction = 6

    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty
        self.tick = random.randrange(self.reaction)
        self.move = (0.0, 0.0)
        self.strafe = random.choice((-1, 1))
        self.last_pos = None
        self.detour = 0
        self.target = None

    @property
    def aggression(self):
        return {"facil": 0.6, "normal": 1.0, "dificil": 1.4}.get(self.difficulty, 1.0)

    def update(self, me, match):
        if me.stunned or not me.alive_in_match:
            me.steer(0, 0)
            return
        self.tick += 1
        if self.tick >= self.reaction or self.target is None or not self.target.alive_in_match:
            self.tick = 0
            self.target = match.nearest_player(me)
            if self.target is not None:
                self.decide(me, match, self.target)
        if self.target is None:
            me.steer(0, 0)
            return
        self.act(me, match, self.target)

    def decide(self, me, match, target):
        self.move = self.chase(me, match, target.x, target.y)

    def act(self, me, match, target):
        me.steer(*self.move)

    def chase(self, me, match, tx, ty, away=False):
        dx, dy = tx - me.x, ty - me.y
        d = math.hypot(dx, dy) or 1
        ax, ay = dx / d, dy / d
        if away:
            ax, ay = -ax, -ay
        if self.last_pos and abs(me.x - self.last_pos[0]) + abs(me.y - self.last_pos[1]) < 0.6 * self.reaction:
            self.strafe = -self.strafe if random.random() < 0.3 else self.strafe
            self.detour = 36
        self.last_pos = (me.x, me.y)
        blocked = match.arena.blocks_segment((me.x, me.y), (tx, ty))
        if self.detour > 0 or (blocked and not away):
            self.detour = max(0, self.detour - self.reaction)
            sx, sy = -ay * self.strafe, ax * self.strafe
            mx, my = sx + ax * 0.45, sy + ay * 0.45
            m = math.hypot(mx, my) or 1
            return mx / m, my / m
        return ax, ay


class DiabreteAI(EnemyAI):
    """Diabrete: chega rápido, rodeia e dá um bote curto (avisado com um brilho)."""

    reaction = 5
    WINDUP = 16

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.lunge_cd = random.randint(40, 120)
        self.orbit = random.uniform(0.5, 1.0)

    def decide(self, me, match, target):
        d = me.distance_to(target)
        if d > 90:
            self.move = self.chase(me, match, target.x, target.y)
        else:
            # rodeia o alvo em vez de grudar nele
            ax, ay = me.direction_to(target)
            self.move = (ax * 0.6 - ay * self.strafe * self.orbit, ay * 0.6 + ax * self.strafe * self.orbit)
        if random.random() < 0.05:
            self.strafe = -self.strafe

    def act(self, me, match, target):
        self.lunge_cd -= 1
        if me.windup > 0:
            me.steer(0, 0)
            me.face(target)
            if me.windup == 1:
                me.start_charge(me.direction_to(target), round(9 * me.damage_bonus))
                me.charge_timer = 9
                match.assets.play("dash", 0.25)
            return
        d = me.distance_to(target)
        me.steer(*self.move)
        if self.lunge_cd <= 0 and 70 < d < 170 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
            self.lunge_cd = round(random.randint(110, 170) / self.aggression)
            me.start_windup(self.WINDUP, (255, 120, 90))
        elif d < me.weapon.reach + target.radius + 4:
            me.attack(match, target)


class EsqueletoAI(EnemyAI):
    """Esqueleto arqueiro: mantém distância, para, mira (brilha) e atira."""

    reaction = 8
    AIM = 26

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.ideal = random.randint(260, 340)

    def decide(self, me, match, target):
        d = me.distance_to(target)
        blocked = match.arena.blocks_segment((me.x, me.y), (target.x, target.y))
        if blocked:
            self.move = self.chase(me, match, target.x, target.y)
        elif d < self.ideal - 70:
            self.move = self.chase(me, match, target.x, target.y, away=True)
        elif d > self.ideal + 80:
            self.move = self.chase(me, match, target.x, target.y)
        else:
            ax, ay = me.direction_to(target)
            self.move = (-ay * self.strafe * 0.7, ax * self.strafe * 0.7)
            if random.random() < 0.08:
                self.strafe = -self.strafe

    def act(self, me, match, target):
        if me.windup > 0:
            me.steer(0, 0)
            me.face(target)
            if me.windup == 1:
                me.attack(match, target)
            return
        me.steer(*self.move)
        d = me.distance_to(target)
        if me.attack_cd <= 0 and d < 560 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
            if random.random() < 0.05 * self.aggression:
                me.start_windup(round(self.AIM / max(0.8, self.aggression)), (240, 236, 200))


class GolemAI(EnemyAI):
    """Golem: anda devagar; perto do alvo levanta os punhos (brilho laranja) e esmaga o chão."""

    reaction = 8
    WINDUP = 48

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.slam_cd = 90

    def act(self, me, match, target):
        self.slam_cd -= 1
        if me.windup > 0:
            me.steer(0, 0)
            if me.windup == 1:
                match.add_effect(Shockwave(me, me.x, me.y, 120, round(20 * me.damage_bonus), stun=34))
                me.melee_flash = 12
            return
        me.steer(*self.move)
        d = me.distance_to(target)
        if self.slam_cd <= 0 and d < 115:
            self.slam_cd = round(150 / self.aggression)
            me.face(target)
            me.start_windup(self.WINDUP, (255, 150, 60))
        elif d < me.weapon.reach + target.radius:
            me.attack(match, target)


class DroneAI(EnemyAI):
    """Drone da Patrulha: voa em círculos em volta do alvo e dá um rasante em linha reta.
    O rasante é avisado pela luz vermelha e pela linha no chão (é só sair de lado), e no fim
    o drone fica tonto um instante."""

    reaction = 5
    WINDUP = 24
    DIVE = 16

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.dive_cd = random.randint(60, 140)
        self.radius = random.uniform(140, 190)
        self.diving = False

    def decide(self, me, match, target):
        d = me.distance_to(target)
        ax, ay = me.direction_to(target)
        if d > self.radius + 60:
            self.move = self.chase(me, match, target.x, target.y)
        else:
            # voa em volta, chegando ou se afastando para ficar na roda
            pull = (d - self.radius) / 80
            self.move = (ax * pull - ay * self.strafe, ay * pull + ax * self.strafe)
        if random.random() < 0.03:
            self.strafe = -self.strafe

    def act(self, me, match, target):
        if self.diving:
            if me.charge_timer <= 0:
                self.diving = False
                me.stun(26)                       # passou direto: fica tonto
            return
        self.dive_cd -= 1
        if me.windup > 0:
            me.steer(0, 0)
            if me.windup == 1:
                me.start_charge(self.dive_dir, round(10 * me.damage_bonus))
                me.charge_timer = self.DIVE
                self.diving = True
                match.assets.play("dash", 0.25)
            return
        me.steer(*self.move)
        d = me.distance_to(target)
        if self.dive_cd <= 0 and 90 < d < 260 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
            self.dive_cd = round(random.randint(120, 180) / self.aggression)
            self.dive_dir = me.direction_to(target)
            me.face(target)
            frames = round(self.WINDUP / max(0.8, self.aggression))
            me.start_windup(frames, PATROL_RED)
            length = me.stats.speed * 4 * self.DIVE
            match.add_effect(AimLine(me.x, me.y, *self.dive_dir, length, frames, width=2))
            match.assets.play("drone", 0.25)


class MilicianoAI(EnemyAI):
    """Miliciano: procura uma parede para se esconder perto do alvo e atira em rajadas de 3.
    A cada duas rajadas para para recarregar, e aí fica exposto (leva mais dano)."""

    reaction = 8
    AIM = 20
    BURST = 3
    BURSTS = 2
    RELOAD = 84
    EXPOSED = 1.35

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.ideal = random.randint(240, 320)
        self.bursts = self.BURSTS
        self.shots = 0
        self.shot_timer = 0
        self.reload = 0
        self.aim = (1.0, 0.0)
        self.cover = None

    def _find_cover(self, me, match, target):
        """Ponto livre colado numa parede, do lado de cá (a parede fica entre ele e o alvo)."""
        best, best_d = None, 1e9
        for wall in match.arena.walls:
            if not wall.visible:
                continue
            r = wall.rect
            cx = min(max(target.x, r.left), r.right)
            cy = min(max(target.y, r.top), r.bottom)
            # o lado da parede oposto ao alvo
            dx, dy = cx - target.x, cy - target.y
            d = math.hypot(dx, dy) or 1
            x, y = cx + dx / d * (me.radius + 14), cy + dy / d * (me.radius + 14)
            if not match.arena.is_free(x, y, me.radius):
                continue
            mine = math.hypot(x - me.x, y - me.y)
            far = math.hypot(x - target.x, y - target.y)
            if far < 150 or mine > 420:
                continue
            if mine < best_d:
                best, best_d = (x, y), mine
        return best

    def decide(self, me, match, target):
        if self.reload > 0 and self.cover is None:
            self.cover = self._find_cover(me, match, target)
        if self.cover is not None and self.reload > 0:
            if math.hypot(self.cover[0] - me.x, self.cover[1] - me.y) < 10:
                self.move = (0.0, 0.0)
            else:
                self.move = self.chase(me, match, *self.cover)
            return
        d = me.distance_to(target)
        blocked = match.arena.blocks_segment((me.x, me.y), (target.x, target.y))
        if blocked or d > self.ideal + 90:
            self.move = self.chase(me, match, target.x, target.y)
        elif d < self.ideal - 80:
            self.move = self.chase(me, match, target.x, target.y, away=True)
        else:
            ax, ay = me.direction_to(target)
            self.move = (-ay * self.strafe * 0.6, ax * self.strafe * 0.6)
            if random.random() < 0.06:
                self.strafe = -self.strafe

    def act(self, me, match, target):
        if self.reload > 0:
            # recarregando: anda até a cobertura (se achou) e fica exposto
            self.reload -= 1
            me.steer(*self.move) if self.cover is not None else me.steer(0, 0)
            me.vulnerability = self.EXPOSED
            if self.reload == 0:
                me.vulnerability = 1.0
                self.bursts = self.BURSTS
                self.cover = None
            return
        if self.shots > 0:
            me.steer(0, 0)
            self.shot_timer -= 1
            if self.shot_timer <= 0:
                self.shots -= 1
                self.shot_timer = 6
                spread = random.uniform(-0.08, 0.08)
                dx, dy = self.aim
                c, s_ = math.cos(spread), math.sin(spread)
                w = me.weapon
                match.spawn_bullet(me, dx * c - dy * s_, dx * s_ + dy * c, w.bullet_speed,
                                   round(w.damage * me.damage_bonus))
                match.assets.play("rajada", 0.18)
                if self.shots == 0:
                    self.bursts -= 1
                    if self.bursts <= 0:
                        self.reload = round(self.RELOAD * max(0.8, 1 / self.aggression))
                        match.popup(me.x, me.y - 50, "RECARREGANDO", (240, 220, 140))
            return
        if me.windup > 0:
            me.steer(0, 0)
            me.face(target)
            if me.windup == 1:
                self.aim = me.direction_to(target) if me.direction_to(target) != (0.0, 0.0) else me.facing
                self.shots, self.shot_timer = self.BURST, 0
            return
        me.steer(*self.move)
        d = me.distance_to(target)
        if me.attack_cd <= 0 and d < 520 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
            if random.random() < 0.05 * self.aggression:
                me.attack_cd = round(70 / self.aggression)
                me.start_windup(round(self.AIM / max(0.8, self.aggression)), PATROL_RED)


class TorretaAI(EnemyAI):
    """Torreta: parada no lugar, gira devagar atrás do alvo com o laser de mira sempre aceso.
    Quando o laser encosta no alvo, pisca e solta uma rajada exatamente por ali."""

    reaction = 4
    TURN = 0.028
    LOCK = 30
    BURST = 4

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.angle = random.uniform(0, math.tau)
        self.sight = None
        self.cooldown = random.randint(30, 80)
        self.locked = 0
        self.shots = 0
        self.shot_timer = 0

    def decide(self, me, match, target):
        self.move = (0.0, 0.0)

    def _ensure_sight(self, me, match):
        if self.sight is None or not self.sight.alive:
            self.sight = AimLine(me.x, me.y, 1.0, 0.0, 520, 10 ** 6, color=PATROL_RED, width=1, follow=me)
            match.add_effect(self.sight)

    def act(self, me, match, target):
        me.steer(0, 0)
        self._ensure_sight(me, match)
        want = math.atan2(target.y - me.y, target.x - me.x)
        diff = (want - self.angle + math.pi) % math.tau - math.pi
        if self.locked <= 0 and self.shots <= 0:
            turn = self.TURN * self.aggression
            self.angle += max(-turn, min(turn, diff))
        dx, dy = math.cos(self.angle), math.sin(self.angle)
        self.sight.dx, self.sight.dy = dx, dy
        me.facing = (dx, dy)
        self.cooldown -= 1
        if self.shots > 0:
            self.shot_timer -= 1
            if self.shot_timer <= 0:
                self.shots -= 1
                self.shot_timer = 5
                w = me.weapon
                match.spawn_bullet(me, dx, dy, w.bullet_speed, round(w.damage * me.damage_bonus))
                match.assets.play("rajada", 0.15)
            if self.shots == 0:
                self.sight.width = 1
                self.cooldown = round(70 / self.aggression)
            return
        if self.locked > 0:
            self.locked -= 1
            self.sight.width = 1 + (self.LOCK - self.locked) // 10
            if self.locked == 0:
                self.shots, self.shot_timer = self.BURST, 0
            return
        clear = not match.arena.blocks_segment((me.x, me.y), (target.x, target.y))
        if self.cooldown <= 0 and abs(diff) < 0.12 and clear and me.distance_to(target) < 520:
            self.locked = round(self.LOCK / max(0.8, self.aggression))
            me.start_windup(self.locked, PATROL_RED)
            match.assets.play("bip", 0.3)


class ExoAI(EnemyAI):
    """Miliciano de Exo (elite): anda devagar, carrega (a linha da investida aparece no chão)
    e investe em linha. Depois da investida o exo trava: fica PRESO uns quadros, levando mais dano."""

    reaction = 8
    WINDUP = 40
    CHARGE = 40
    STUCK = 54

    def __init__(self, difficulty="normal"):
        super().__init__(difficulty)
        self.charge_cd = 90
        self.charging = False
        self.stuck = 0
        self.dir = (1.0, 0.0)

    def act(self, me, match, target):
        if self.charging:
            if me.charge_timer <= 0:
                self.charging = False
                self.stuck = self.STUCK
                me.vulnerability = 1.5
                match.popup(me.x, me.y - 60, "PRESO!", (240, 220, 140))
                match.assets.play("vapor", 0.4)
            return
        if self.stuck > 0:
            self.stuck -= 1
            me.steer(0, 0)
            if self.stuck % 6 == 0:
                match.burst(me.x + random.uniform(-12, 12), me.y - 40, (220, 224, 230), 2, speed=1.5)
            if self.stuck == 0:
                me.vulnerability = 1.0
            return
        self.charge_cd -= 1
        if me.windup > 0:
            me.steer(0, 0)
            if me.windup == 1:
                me.start_charge(self.dir, round(18 * me.damage_bonus), stun=24)
                me.charge_timer = self.CHARGE
                self.charging = True
                match.assets.play("dash", 0.45)
                match.camera.shake(3)
            return
        me.steer(*self.move)
        d = me.distance_to(target)
        if self.charge_cd <= 0 and 110 < d < 430 and not match.arena.blocks_segment((me.x, me.y), (target.x, target.y)):
            self.charge_cd = round(200 / self.aggression)
            self.dir = me.direction_to(target)
            me.face(target)
            frames = round(self.WINDUP / max(0.8, self.aggression))
            me.start_windup(frames, PATROL_RED)
            match.add_effect(AimLine(me.x, me.y, *self.dir, me.stats.speed * 4 * self.CHARGE, frames,
                                     width=3, grow=6))
        elif d < me.weapon.reach + target.radius:
            me.attack(match, target)


class ShadowAI(FighterAI):
    """Alma corrompida: luta como a CPU do duelo, mas não corre atrás dos itens dos heróis."""

    @staticmethod
    def _wanted_pickup(me, target, match):
        return None


SHADOW_LEVEL = {"facil": "facil", "normal": "facil", "dificil": "normal"}
BRAINS = {"diabrete": DiabreteAI, "esqueleto": EsqueletoAI, "golem": GolemAI,
          "drone": DroneAI, "miliciano": MilicianoAI, "torreta": TorretaAI, "miliciano_exo": ExoAI}


def spawn_enemy(match, kind, x, y):
    """Cria o inimigo (Fighter do time 1) e o cérebro dele. kind: criatura ou "sombra:<herói>"."""
    from .fighter import Fighter
    difficulty = match.session.difficulty
    if kind.startswith("sombra:"):
        key = kind.split(":", 1)[1]
        stats = shadow_stats(key)
        sprites = match.assets.shadow_sprites(key)
        # a sombra luta um nível abaixo da dificuldade escolhida (ela é uma cópia mais fraca)
        brain = ShadowAI(SHADOW_LEVEL.get(difficulty, "normal"))
    else:
        stats = CREATURES[kind]
        sprites = match.assets.sprites.get(stats.key) or match.assets.sprites["guerreiro"]
        brain = BRAINS[kind](difficulty)
    weapon = random.randrange(len(stats.weapons))
    f = Fighter(stats, 0, x, y, sprites, stats.name.upper(), SHADOW_AURA, team=1, weapon_index=weapon, is_cpu=True)
    f.radius = f.base_radius = stats.radius
    f.armed = stats.armed
    f.knock_resist = stats.knock_resist
    f.kind = kind
    if kind.startswith("sombra:"):
        f.damage_bonus = 0.85
        f.aura = SHADOW_RIM
        f.ring_color = SHADOW_RIM
        f.overlay = "full"
    else:
        f.ring_color = (90, 40, 50)
        f.overlay = "hp"
    return f, brain
