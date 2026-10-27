"""Brilho das armas raras: a cor do elemento de cada uma na mão, no golpe e nos tiros.

As comuns ficam como sempre. As raras do baú brilham de leve; as roubadas e as forjadas brilham
mais, soltam faíscas em volta de quem segura e deixam um rastro de luz nos tiros. Tudo aqui é só
visual (não muda dano nem alcance).
"""
import math
import random

import pygame

from .entities import Particle

# cor do elemento de cada arma rara (o brilho, as faíscas e o rastro usam esta cor)
ACCENT = {
    "Besta": (190, 210, 255), "Lança-chamas": (255, 140, 50), "Bumerangue": (255, 200, 120),
    "Cajado do Raio": (255, 226, 90), "Canhão de Mão": (255, 170, 80), "Colmeia": (255, 210, 70),
    "Arco de Espinhos": (140, 225, 100), "Machado do Lenhador": (220, 230, 255),
    "Lanterna das Almas": (120, 240, 170), "Crânio Uivante": (120, 240, 170),
    "Foice Espectral": (190, 150, 255),
    "Estalactites": (170, 225, 255), "Espelho de Cristal": (190, 235, 255), "Bola de Neve": (220, 240, 255),
    "Cajado do Raio Supremo": (255, 230, 110),
    "Lâmina Solar": (255, 170, 60), "Martelo do Trovão Eterno": (150, 200, 255),
    "Arco das Mil Almas": (190, 150, 255), "Canhão do Vazio": (170, 100, 255),
    "Coração do Inverno": (170, 225, 255), "Lança do Dragão": (255, 110, 40),
    "Cetro da Tempestade": (255, 236, 120), "Foice do Ceifador": (130, 255, 190),
}
WHITE = (255, 255, 240)


def tier(weapon):
    """0 comum, 1 rara, 2 roubada, 3 forjada."""
    if weapon is None:
        return 0
    if weapon.forjada:
        return 3
    if weapon.roubada:
        return 2
    return 1 if weapon.rare else 0


def accent(weapon):
    """A cor do brilho desta arma, ou None se ela é comum."""
    if not tier(weapon):
        return None
    return ACCENT.get(weapon.name, (255, 220, 140))


_GLOWS = {}


def glow(radius, color, strength):
    """Bola de luz macia (para somar na tela com BLEND_ADD). Guardada em cache."""
    key = (radius, color, round(strength * 20))
    if key not in _GLOWS:
        surf = pygame.Surface((radius * 2, radius * 2))
        k = round(strength * 20) / 20
        for r in range(radius, 0, -1):
            v = k * (1 - r / radius) ** 1.8
            pygame.draw.circle(surf, tuple(round(c * v) for c in color), (radius, radius), r)
        _GLOWS[key] = surf
    return _GLOWS[key]


class Sparkle(Particle):
    """Faísca em forma de estrelinha de 4 pontas que pisca enquanto some."""

    def draw(self, surf, camera):
        t = self.life / self.max_life
        x, y = round(self.x - camera.x), round(self.y - camera.y)
        arm = max(1, round(self.size * t))
        if self.life % 6 < 3 and arm > 1:
            surf.fill(self.color, (x - arm, y, arm * 2 + 1, 1))
            surf.fill(self.color, (x, y - arm, 1, arm * 2 + 1))
        surf.fill(WHITE if t > 0.4 else self.color, (x, y, 1 + (arm > 2), 1 + (arm > 2)))


# ── na mão ───────────────────────────────────
def draw_held(surf, weapon, center, ticks):
    """Brilho pulsando em volta da arma na mão (``center`` é o meio da arma, já na tela)."""
    color = accent(weapon)
    if color is None:
        return
    level = tier(weapon)
    pulse = 0.5 + 0.5 * math.sin(ticks * 0.09)
    radius = (14, 16, 20)[level - 1] + round(3 * pulse)
    strength = (0.30, 0.42, 0.55)[level - 1] + 0.12 * pulse
    g = glow(radius, color, strength)
    surf.blit(g, g.get_rect(center=(round(center[0]), round(center[1]))), special_flags=pygame.BLEND_ADD)
    if level >= 2:
        # duas faíscas girando em volta da arma
        for k in range(2):
            a = ticks * 0.07 + k * math.pi
            px = round(center[0] + math.cos(a) * (radius - 4))
            py = round(center[1] + math.sin(a) * (radius - 4) * 0.5)
            surf.fill(WHITE if (ticks // 4 + k) % 2 else color, (px, py, 2, 2))


def emit_held(fighter, match):
    """De vez em quando, uma faísca sobe da arma de quem segura uma rara."""
    weapon = fighter.weapon
    color = accent(weapon)
    if color is None or not fighter.alive_in_match or not getattr(fighter, "armed", True):
        return
    every = (24, 14, 9)[tier(weapon) - 1]
    if fighter.age % every:
        return
    fx, fy = fighter.facing
    x = fighter.x + fx * 16 + random.uniform(-8, 8)
    y = fighter.y - 14 + fy * 10 + random.uniform(-6, 6)
    match.particles.append(Sparkle(x, y, random.uniform(-0.2, 0.2), random.uniform(-0.9, -0.4),
                                   color if random.random() < 0.7 else WHITE, random.randint(22, 34), 3))


# ── golpes e tiros ───────────────────────────
def on_attack(fighter, weapon, match, tip):
    """Explosão de faíscas na boca da arma (tiro) ou na ponta do golpe (perto)."""
    color = accent(weapon)
    if color is None:
        return
    level = tier(weapon)
    fx, fy = fighter.facing
    for _ in range(3 + 2 * level):
        a = math.atan2(fy, fx) + random.uniform(-0.9, 0.9)
        speed = random.uniform(1.2, 2.6 + level * 0.5)
        match.particles.append(Sparkle(tip[0], tip[1], math.cos(a) * speed, math.sin(a) * speed,
                                       color if random.random() < 0.75 else WHITE, random.randint(12, 22), 3))


def weapon_tip(fighter, weapon):
    """Onde fica a ponta da arma no mundo (aproximado, para as faíscas)."""
    from . import weapon_art
    length = weapon_art.weapon_length(weapon.name) if not weapon.is_melee else fighter.melee_reach(weapon) * 0.6
    fx, fy = fighter.facing
    return fighter.x + fx * min(length, 40), fighter.y - 12 + fy * min(length, 40)


def bullet_weapon(bullet):
    weapon = getattr(bullet, "weapon", None)
    return weapon if tier(weapon) else None


def _moving(bullet):
    return math.hypot(getattr(bullet, "vx", 0), getattr(bullet, "vy", 0)) > 0.5


def emit_trail(bullet, match):
    """Rastro de faíscas atrás dos tiros das raras."""
    weapon = bullet_weapon(bullet)
    if weapon is None or not _moving(bullet):
        return
    level = tier(weapon)
    age = getattr(bullet, "age", match.frame)
    every = (3, 2, 2)[level - 1] * max(1, len(match.bullets) // 4)     # muitos tiros: rastro mais ralo
    if age % every:
        return
    color = accent(weapon)
    x = bullet.x + random.uniform(-3, 3)
    y = bullet.y + random.uniform(-3, 3) - getattr(bullet, "z", 0)
    match.particles.append(Sparkle(x, y, -bullet.vx * 0.08 + random.uniform(-0.3, 0.3),
                                   -bullet.vy * 0.08 + random.uniform(-0.3, 0.3),
                                   color if random.random() < 0.8 else WHITE, random.randint(10, 18), 2 + (level > 1)))


def draw_bullet_glow(surf, camera, bullet):
    """Luz embaixo do tiro das raras (desenhada antes do tiro)."""
    weapon = bullet_weapon(bullet)
    if weapon is None or not _moving(bullet):
        return
    level = tier(weapon)
    g = glow(10 + 3 * level, accent(weapon), 0.35 + 0.1 * level)
    pos = (round(bullet.x - camera.x), round(bullet.y - camera.y - getattr(bullet, "z", 0)))
    surf.blit(g, g.get_rect(center=pos), special_flags=pygame.BLEND_ADD)
