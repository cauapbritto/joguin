"""Energia da campanha (estilo Soul Knight): cada herói tem uma barra que as armas fortes gastam.

- As armas do próprio herói são de graça (continuam com pente e recarga).
- Arma comum de outro herói gasta 1 por tiro (as de perto, nada).
- Raras, roubadas e forjadas gastam bem mais e perdem o pente: o limite passa a ser a energia.
- A energia não volta sozinha na masmorra (só no Fácil, devagar): volta com os orbes azuis que os
  inimigos derrubam, com o item ENERGIA e no acampamento (a barra enche antes de cada masmorra).
- Sem energia, a arma de tiro vira arma de bater: o herói dá coronhada com ela (e a rara de perto
  bate sem o efeito especial).

Só vale na campanha: fora dela ``fighter.energy`` é None e nada disso acontece.
"""
import math
import random

import pygame

from .data import WeaponStats
from .entities import Entity, Particle

ENERGY_MAX = 200
ENERGY_COLOR = (90, 170, 255)
ENERGY_LIGHT = (200, 232, 255)
UPGRADE_ENERGY = 50              # melhoria ENERGIA: +50 na barra
ITEM_ENERGY = 60                 # item ENERGIA (o raio azul): +60 além de deixar a habilidade pronta
ORB_ENERGY = 4                   # cada orbe pequeno

# coronhada: a arma de tiro sem energia vira arma de perto comum
BASH = WeaponStats("Coronhada", "melee", 12, reach=58, cooldown=22)

# custo por disparo (golpe, nas de perto) das armas que fogem da regra geral
COSTS = {
    # raras de tiro rápido (jato, feixe): pouco por tiro, mas atiram muito
    "Lança-chamas": 1, "Lanterna das Almas": 1,
    # raras
    "Besta": 4, "Bumerangue": 4, "Cajado do Raio": 4, "Canhão de Mão": 5, "Colmeia": 4,
    "Arco de Espinhos": 4, "Crânio Uivante": 4, "Foice Espectral": 4, "Taser de Rede": 4,
    "Rifle de Plasma": 3, "Drone de Bolso": 14,
    "Machado do Lenhador": 2, "Teclado Mecânico": 1, "Escudo de Choque": 0,
    # roubadas
    "Estalactites": 8, "Espelho de Cristal": 7, "Bola de Neve": 8, "Cajado do Raio Supremo": 6,
    "Manopla do Exo": 3,
    # forjadas
    "Arco das Mil Almas": 10, "Canhão do Vazio": 12, "Lança do Dragão": 12, "Coração do Inverno": 3,
    "Cetro da Tempestade": 1, "Lâmina Solar": 3, "Martelo do Trovão Eterno": 4, "Foice do Ceifador": 2,
}


def enabled(fighter):
    return getattr(fighter, "energy", None) is not None


def base_cost(weapon):
    """Quanto a arma gasta por disparo, sem contar de quem ela é."""
    if weapon.name in COSTS:
        return COSTS[weapon.name]
    if weapon.forjada:
        return 3 if weapon.is_melee else 10
    if weapon.roubada:
        return 3 if weapon.is_melee else 7
    if weapon.rare:
        return 2 if weapon.is_melee else 4
    return 0 if weapon.is_melee else 1


def cost(fighter, weapon):
    """Energia que este disparo custa para este herói (0 = de graça)."""
    if weapon is None or not enabled(fighter) or weapon is BASH:
        return 0
    if weapon in fighter.stats.weapons:
        return 0                                   # a arma do próprio herói nunca gasta
    return base_cost(weapon)


def uses_energy(fighter, weapon):
    """Arma que troca o pente pela energia (as raras, roubadas e forjadas)."""
    return enabled(fighter) and weapon is not None and weapon.rare and cost(fighter, weapon) > 0


def spend(fighter, weapon):
    c = cost(fighter, weapon)
    if c:
        fighter.energy = max(0, fighter.energy - c)


def gain(fighter, amount):
    if not enabled(fighter) or fighter.energy >= fighter.energy_max:
        return 0
    got = min(amount, fighter.energy_max - fighter.energy)
    fighter.energy += got
    return got


def fill(fighter):
    if enabled(fighter):
        fighter.energy = fighter.energy_max


class EnergyOrb(Entity):
    """Orbe azul que cai do inimigo: pula para fora, pisca no chão e vem até quem chega perto."""

    kind = "orbe"
    MAGNET = 130
    LIFE = 14 * 60

    def __init__(self, x, y, amount=ORB_ENERGY):
        super().__init__(x, y)
        self.amount = amount
        self.radius = 8
        a = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 3.5)
        self.vx, self.vy = math.cos(a) * speed, math.sin(a) * speed
        self.age = 0
        self.timer = self.LIFE

    @property
    def sort_y(self):
        return self.y

    def update(self, match):
        self.age += 1
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False
            return
        # vai até o jogador mais perto que ainda tem espaço na barra
        best, best_d = None, self.MAGNET
        for f in match.alive_players:
            if enabled(f) and f.energy < f.energy_max:
                d = math.hypot(f.x - self.x, f.y - self.y)
                if d < best_d:
                    best, best_d = f, d
        if best is not None and self.age > 12:
            ux, uy = (best.x - self.x) / (best_d or 1), (best.y - self.y) / (best_d or 1)
            pull = 1.2 + 6 * (1 - best_d / self.MAGNET)
            self.vx = self.vx * 0.8 + ux * pull
            self.vy = self.vy * 0.8 + uy * pull
        else:
            self.vx *= 0.9
            self.vy *= 0.9
        self.x += self.vx
        self.y += self.vy
        if self.age % 10 == 0:
            match.particles.append(Particle(self.x, self.y - 6, 0, -0.4, ENERGY_COLOR, 16, 2))

    def apply(self, fighter, match):
        if not enabled(fighter) or fighter.energy >= fighter.energy_max:
            return                                   # barra cheia: deixa para o amigo
        gain(fighter, self.amount)
        match.burst(self.x, self.y - 6, ENERGY_COLOR, 4, speed=2)
        match.assets.play("alma", 0.15)
        self.alive = False

    def draw(self, surf, camera):
        if self.timer < 120 and (self.timer // 6) % 2:
            return
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        bob = round(math.sin(self.age * 0.15) * 2)
        r = 4 + (1 if (self.age // 8) % 2 else 0)
        pygame.draw.ellipse(surf, (8, 10, 20), (sx - 5, sy + 3, 10, 4))
        pygame.draw.circle(surf, (30, 70, 140), (sx, sy - 6 + bob), r + 2)
        pygame.draw.circle(surf, ENERGY_COLOR, (sx, sy - 6 + bob), r)
        surf.fill(ENERGY_LIGHT, (sx - 1, sy - 8 + bob, 2, 2))
