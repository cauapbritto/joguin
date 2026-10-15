"""Inimigos da campanha: criaturas novas e as almas corrompidas (versões sombrias dos heróis).

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
TINTS = {"aryel": (66, 48, 86)}      # Aryel Corrompido é a sombra mais escura de todas
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
}


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


class Portal(Entity):
    """Fenda sombria de onde sai um inimigo depois de alguns quadros."""

    FRAMES = 60

    def __init__(self, x, y, kind, delay=0):
        super().__init__(x, y)
        self.kind = kind
        self.delay = delay
        self.age = 0
        self.radius = 30 if kind in ("golem", "chefe") else 22

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


class ShadowAI(FighterAI):
    """Alma corrompida: luta como a CPU do duelo, mas não corre atrás dos itens dos heróis."""

    @staticmethod
    def _wanted_pickup(me, target, match):
        return None


SHADOW_LEVEL = {"facil": "facil", "normal": "facil", "dificil": "normal"}
BRAINS = {"diabrete": DiabreteAI, "esqueleto": EsqueletoAI, "golem": GolemAI}


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
