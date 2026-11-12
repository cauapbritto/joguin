"""Energia da campanha (estilo Soul Knight): cada herói tem uma barra que as armas fortes gastam.

- As armas do próprio herói são de graça (continuam com pente e recarga).
- Arma comum de outro herói gasta 1 por tiro (as de perto, nada).
- Raras, roubadas e forjadas de tiro gastam bem mais e perdem o pente: o limite passa a ser a energia.
- Raras e forjadas de PERTO: o golpe normal é de graça, só o efeito especial gasta (o giro do
  machado, a onda da Lâmina Solar, o 3º golpe do teclado...). Sem energia, bate sem o efeito.
  A Foice do Ceifador é a exceção: cada golpe dela gasta.
- A energia também volta lutando: acertos logo depois da habilidade, abate com arma de perto,
  esquiva perfeita, orbe grande de elite e chefão, e o amigo pode passar energia (segurar LARGAR).
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
BIG_ORB_ENERGY = 15              # orbe grande: elite e chefão soltam um a mais
ABILITY_HIT = 3                  # cada acerto logo depois de usar a habilidade
ABILITY_MAX = 15                 # ... até isto por uso da habilidade
ABILITY_WINDOW = 120             # quadros depois da habilidade em que os acertos contam
MELEE_KILL = 2                   # abate com arma de perto
PERFECT_DODGE = 4                # esquiva perfeita
PASS_AMOUNT = 20                 # segurar LARGAR perto de um amigo passa isto da sua barra
PASS_HOLD = 30                   # quadros segurando LARGAR para passar
SIFAO = 0.04                     # melhoria SIFÃO: 4% do dano causado vira energia (mínimo 1)

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
    "Escudo de Choque": 0,
    # roubadas
    "Estalactites": 8, "Espelho de Cristal": 7, "Bola de Neve": 8, "Cajado do Raio Supremo": 6,
    # forjadas
    "Arco das Mil Almas": 10, "Canhão do Vazio": 12, "Lança do Dragão": 12, "Coração do Inverno": 3,
    "Cetro da Tempestade": 1, "Foice do Ceifador": 3,
}

# armas de perto que gastam a cada golpe (as outras de perto só gastam no efeito especial)
PAY_EVERY_SWING = {"Foice do Ceifador"}

# efeito especial das armas de perto: (golpe comum, 3º golpe seguido). O golpe sem efeito é de graça.
SPECIAL_COSTS = {
    "Machado do Lenhador": (2, 2),           # o giro (sem energia, golpe só para a frente)
    "Teclado Mecânico": (0, 2),              # o 3º golpe solta as teclas
    "Manopla do Exo": (0, 6),                # o 3º soco abre a onda de choque
    "Lâmina Solar": (2, 4),                  # a onda de luz; no 3º, onda e giro
    "Martelo do Trovão Eterno": (2, 6),      # o raio; no 3º, o arremesso do martelo
}


def enabled(fighter):
    return getattr(fighter, "energy", None) is not None


def free_swing(weapon):
    """Arma de perto em que o golpe normal é de graça (só o efeito especial gasta)."""
    return weapon.is_melee and weapon.name not in PAY_EVERY_SWING


def base_cost(weapon):
    """Quanto a arma gasta por disparo, sem contar de quem ela é."""
    if free_swing(weapon):
        return 0
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


def special_cost(fighter, weapon, third=False):
    """Quanto custa o efeito especial deste golpe de perto (0 = de graça ou sem efeito)."""
    if weapon is None or not enabled(fighter) or not free_swing(weapon) or weapon in fighter.stats.weapons:
        return 0
    if weapon.name in SPECIAL_COSTS:
        normal, third_cost = SPECIAL_COSTS[weapon.name]
    elif weapon.forjada:
        normal, third_cost = 2, 4
    elif weapon.rare and (weapon.spin or weapon.special):
        normal, third_cost = (2, 2) if weapon.spin else (0, 4)
    else:
        return 0
    return third_cost if third else normal


def pay_special(fighter, weapon, third=False):
    """Paga o efeito especial do golpe de perto. Devolve False se não tem energia (golpe sem efeito)."""
    price = special_cost(fighter, weapon, third)
    if price <= 0:
        return True
    if fighter.energy < price:
        return False
    fighter.energy -= price
    return True


def shown_cost(fighter, weapon):
    """O número que aparece no HUD e no celular: o tiro, ou o efeito especial do golpe de perto."""
    return cost(fighter, weapon) or special_cost(fighter, weapon)


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


def on_damage(attacker, victim, dealt, match):
    """O herói acertou alguém: habilidade recém-usada e SIFÃO devolvem energia; abate de perto também."""
    if not enabled(attacker) or dealt <= 0 or attacker is victim:
        return
    got = 0
    if attacker.ability_energy_timer > 0 and attacker.ability_energy_left > 0:
        add = gain(attacker, min(ABILITY_HIT, attacker.ability_energy_left))
        attacker.ability_energy_left -= ABILITY_HIT
        got += add
    if attacker.siphon > 0:
        got += gain(attacker, max(1, round(dealt * attacker.siphon)))
    if victim.hp <= 0 and attacker.weapon.is_melee and attacker.melee_flash > 0:
        got += gain(attacker, MELEE_KILL)
    if got and match is not None:
        match.particles.append(Particle(attacker.x, attacker.y - 30, 0, -1.0, ENERGY_COLOR, 18, 3))


def on_ability(fighter):
    """Usou a habilidade: os acertos dos próximos 2 s enchem um pouco a barra."""
    if enabled(fighter):
        fighter.ability_energy_timer = ABILITY_WINDOW
        fighter.ability_energy_left = ABILITY_MAX


def on_perfect_dodge(fighter, match):
    if gain(fighter, PERFECT_DODGE) and match is not None:
        match.popup(fighter.x, fighter.y - 78, f"+{PERFECT_DODGE} ENERGIA", ENERGY_COLOR)


def pass_to(giver, friend, match):
    """Passa até PASS_AMOUNT da barra para o amigo. Devolve quanto passou."""
    if not (enabled(giver) and enabled(friend)) or giver.energy <= 0:
        return 0
    got = gain(friend, min(PASS_AMOUNT, giver.energy))
    giver.energy -= got
    if got and match is not None:
        match.popup(friend.x, friend.y - 78, f"+{got} ENERGIA", ENERGY_COLOR)
        for k in range(8):
            t = k / 8
            match.particles.append(Particle(giver.x + (friend.x - giver.x) * t, giver.y - 20 + (friend.y - giver.y) * t,
                                            0, -0.6, ENERGY_LIGHT, 20, 3))
        match.assets.play("alma", 0.3)
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
        r = (4 if self.amount < BIG_ORB_ENERGY else 8) + (1 if (self.age // 8) % 2 else 0)
        pygame.draw.ellipse(surf, (8, 10, 20), (sx - 5, sy + 3, 10, 4))
        pygame.draw.circle(surf, (30, 70, 140), (sx, sy - 6 + bob), r + 2)
        pygame.draw.circle(surf, ENERGY_COLOR, (sx, sy - 6 + bob), r)
        surf.fill(ENERGY_LIGHT, (sx - 1, sy - 8 + bob, 2, 2))
