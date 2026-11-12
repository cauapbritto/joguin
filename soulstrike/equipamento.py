"""Equipamento da campanha: uma vaga por herói, ao lado da bolsa de armas.

Um equipamento por vez. Pegar outro troca, e o velho cai no chão (um amigo pode pegar). Vem do
baú da sala de recompensas, de elites (chance pequena) e da loja da fase. Diferente das
melhorias (que ficam para sempre na campanha), o equipamento é uma escolha que dá para trocar.

Os efeitos de número (vida, energia, recarga) entram e saem com apply/remove; os outros são
consultados na hora pelo código de cada parte (energia.py, fighter.py, campaign.py).
"""
import math
import random
from dataclasses import dataclass

import pygame

from . import theme
from .entities import Entity, Particle


@dataclass(frozen=True)
class Gear:
    key: str
    name: str
    desc: str
    color: tuple
    icon: tuple                  # desenho 7x7 ("#" = cor, "+" = claro)


GEAR = {g.key: g for g in (
    Gear("amuleto", "Amuleto do Cristal", "+60 de energia máxima.", (120, 200, 255),
         ("..###..", ".#...#.", "#..+..#", "#.+++.#", "#..+..#", ".#...#.", "..###..")),
    Gear("pilha", "Pilha Recarregável", "Parado, ganha +1 de energia a cada 2 s.", (110, 230, 120),
         ("..##...", ".####..", ".#++#..", ".####..", ".#..#..", ".####..", ".####..")),
    Gear("presa", "Presa de Vampiro", "Cada abate devolve 3 de energia e 2 de vida.", (200, 60, 90),
         ("#######", ".#...#.", ".#...#.", ".+...+.", "..#.#..", "..+.+..", "......."),),
    Gear("luva", "Luva de Ferreiro", "Armas de outro herói não gastam energia.", (210, 150, 80),
         (".#.#.#.", ".#.#.#.", "######.", "#+++##.", "#####..", ".####..", ".####..")),
    Gear("mochila", "Mochila Grande", "Uma 4ª vaga na bolsa de armas.", (176, 120, 74),
         ("..###..", ".#...#.", "#######", "#+++++#", "#+###+#", "#+++++#", "#######")),
    Gear("coldre", "Coldre Duplo", "Trocar de arma recarrega o pente da que saiu.", (150, 110, 70),
         ("##...##", "##...##", "#+#.#+#", "#+#.#+#", "###.###", ".#...#.", "......."),),
    Gear("bota", "Bota de Mola", "Esquiva mais longa; esquiva perfeita dá o dobro de energia.", (120, 210, 200),
         ("..##...", "..##...", "..##...", "..####.", "######.", "..+.+..", ".+.+.+.")),
    Gear("coracao", "Coração de Pedra", "+40% de vida, 10% mais lento.", (150, 140, 150),
         (".##.##.", "#######", "#+#####", "#######", ".#####.", "..###..", "...#...")),
    Gear("cracha", "Crachá da Lag Lobby", "A habilidade volta 25% mais rápido.", (90, 170, 255),
         ("...#...", "..###..", "#######", "#+++++#", "#+###+#", "#+++++#", "#######")),
    Gear("ampulheta", "Ampulheta do Templo", "Habilidade com a barra vazia dá +30 de energia (1 vez por etapa).",
         (236, 200, 120), ("#######", ".#+++#.", "..#+#..", "...#...", "..#.#..", ".#+++#.", "#######")),
    Gear("talisma", "Talismã da Sorte", "Uma arma a mais no baú e 15% a mais de almas.", (120, 230, 140),
         ("#.#.#..", "#####..", ".###...", "..#.#.#", "...####", "...+##.", "...#.#.")),
    Gear("capa", "Capa da IARA", "1 vez por etapa, o golpe que derrubaria deixa com 1 de vida.", (180, 120, 230),
         ("..###..", ".#+++#.", "#+###+#", "#+###+#", "#+###+#", "#+###+#", "##.#.##")),
)}

AMULET = 60
HEART_HP = 1.4
HEART_SPEED = 0.9
BADGE_CD = 0.75
BOOT_DASH = 1.35
BATTERY_EVERY = 120
FANG_ENERGY, FANG_HP = 3, 2
HOURGLASS = 30
TALISMAN_SOULS = 1.15
ELITE_CHANCE = 0.06
SHOP_COST = 70


def has(fighter, key):
    return getattr(fighter, "gear", None) == key


def apply(fighter, key, live=False):
    """Coloca o efeito de número do equipamento (``live``: no meio da etapa, já mexe na barra)."""
    if key == "amuleto":
        fighter.energy_bonus += AMULET
        if live and fighter.energy is not None:
            fighter.energy_max += AMULET
    elif key == "coracao":
        ratio = fighter.hp / fighter.max_hp if fighter.max_hp else 1
        fighter.max_hp = round(fighter.max_hp * HEART_HP)
        if live:
            fighter.hp = max(1, round(fighter.max_hp * ratio))
        fighter.speed_mult *= HEART_SPEED
    elif key == "cracha":
        fighter.cd_mult *= BADGE_CD


def remove(fighter, key):
    """Tira o efeito de número (o equipamento saiu da vaga no meio da etapa)."""
    if key == "amuleto":
        fighter.energy_bonus -= AMULET
        if fighter.energy is not None:
            fighter.energy_max -= AMULET
            fighter.energy = min(fighter.energy, fighter.energy_max)
    elif key == "coracao":
        ratio = fighter.hp / fighter.max_hp if fighter.max_hp else 1
        fighter.max_hp = round(fighter.max_hp / HEART_HP)
        fighter.hp = max(1, min(fighter.max_hp, round(fighter.max_hp * ratio)))
        fighter.speed_mult /= HEART_SPEED
    elif key == "cracha":
        fighter.cd_mult /= BADGE_CD


_icons = {}


def icon(key, scale=3):
    """O ícone do equipamento (pixel art 7x7 ampliada)."""
    k = (key, scale)
    if k not in _icons:
        g = GEAR[key]
        light = tuple(min(255, c + 80) for c in g.color)
        surf = pygame.Surface((9 * scale, 9 * scale), pygame.SRCALPHA)
        for y, row in enumerate(g.icon):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):             # contorno escuro
                    surf.fill((24, 17, 28), ((x + 1 + dx) * scale, (y + 1 + dy) * scale, scale, scale))
        for y, row in enumerate(g.icon):
            for x, ch in enumerate(row):
                if ch != ".":
                    surf.fill(light if ch == "+" else g.color, ((x + 1) * scale, (y + 1) * scale, scale, scale))
        _icons[k] = surf
    return _icons[k]


def pick_random(held=()):
    pool = [k for k in GEAR if k not in held] or list(GEAR)
    return random.choice(pool)


class GroundGear(Entity):
    """Equipamento no chão: pula para fora, brilha e ATACAR pega (o velho cai no lugar)."""

    REACH = 58
    TOSS = 22

    def __init__(self, key, start, end):
        super().__init__(*end)
        self.key = key
        self.start, self.end = start, end
        self.x, self.y = start
        self.t = 0
        self.z = 0.0
        self.color = GEAR[key].color

    @property
    def landed(self):
        return self.t >= self.TOSS

    @property
    def sort_y(self):
        return self.y - 30 if self.landed else 1e9

    def can_pick(self, fighter):
        return self.landed and fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def update(self, match):
        self.t += 1
        if not self.landed:
            k = self.t / self.TOSS
            (x0, y0), (x1, y1) = self.start, self.end
            self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            self.z = 46 * 4 * k * (1 - k)
            if self.landed:
                self.z = 0.0
                match.dust(self.x, self.y + 6, 5)
        elif self.t % 20 == 0:
            match.particles.append(Particle(self.x + random.uniform(-12, 12), self.y - 4, 0, -0.5, self.color, 22, 2))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (0, 0, 0), (sx - 14, sy + 2, 28, 8))
        bob = 0 if not self.landed else round(math.sin(self.t * 0.08) * 2) - 6
        img = icon(self.key, 3)
        surf.blit(img, img.get_rect(center=(sx, sy - round(self.z) + bob - 6)))

    def draw_prompt(self, screen, camera, ui, frame, near):
        if not self.landed:
            return
        sx, sy = camera.to_screen(self.x, self.y + 14)
        ui.text(screen, GEAR[self.key].name.upper(), theme.XS, self.color, (round(sx), round(sy)))
        if near:
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: EQUIPAR", theme.XS, color, (round(sx), round(sy) + 12))
