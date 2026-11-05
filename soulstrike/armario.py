"""Armário de armas do acampamento: guarda até 4 armas do grupo de uma etapa para a outra.

Perto dele, ATACAR (ou LARGAR ARMA) pendura a arma da mão; sem arma para guardar, ATACAR pega a
primeira pendurada (e a que ele tinha do mesmo tipo vai para o lugar dela). As armas guardadas ficam na
campanha (CampaignRun.rack) e aparecem no armário de todos os acampamentos, inclusive no salvo.
"""
import math

import pygame

from . import theme, weapon_art
from .data import RARE_WEAPONS, common_weapon, rarity_color
from .entities import Entity, Wall

RACK_SIZE = 4


def token_of(weapon):
    """Como a arma fica guardada (no salvo também): "rara:<chave>" ou "comum:<nome>"."""
    for key, w in RARE_WEAPONS.items():
        if w is weapon:
            return "rara:" + key
    return "comum:" + weapon.name


def weapon_of(token):
    kind, _, name = str(token).partition(":")
    if kind == "rara":
        return RARE_WEAPONS.get(name)
    if kind == "comum":
        return common_weapon(name)
    return None


class Armario(Entity):
    """O móvel em si: tábua com 4 ganchos e as armas penduradas (lê a lista da campanha)."""

    REACH = 78

    def __init__(self, x, y, run, style=None):
        super().__init__(x, y)
        self.run = run
        self.style = style
        self.age = 0
        self.wall = Wall(round(x) - 44, round(y) - 10, 88, 20, visible=False)

    @property
    def sort_y(self):
        return self.y

    @property
    def weapons(self):
        return [w for w in (weapon_of(t) for t in self.run.rack) if w is not None]

    def can_use(self, fighter):
        return fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def update(self, match):
        self.age += 1

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (10, 8, 12), (sx - 50, sy + 2, 100, 14))
        if self.style == "lag":
            frame, board, peg = (70, 80, 96), (40, 46, 58), (150, 210, 255)
        else:
            frame, board, peg = (92, 60, 36), (130, 88, 52), (200, 190, 170)
        # dois pés e a tábua
        surf.fill(frame, (sx - 44, sy - 66, 6, 72))
        surf.fill(frame, (sx + 38, sy - 66, 6, 72))
        surf.fill((20, 14, 18), (sx - 42, sy - 70, 84, 52))
        surf.fill(board, (sx - 40, sy - 68, 80, 48))
        for k in range(3):                                   # tábuas
            surf.fill(frame, (sx - 40, sy - 68 + 16 * k, 80, 1))
        surf.fill(frame, (sx - 46, sy - 72, 92, 5))
        weapons = self.weapons
        for i in range(RACK_SIZE):
            hx = sx - 30 + i * 20
            surf.fill(peg, (hx - 1, sy - 64, 3, 4))
            if i < len(weapons):
                w = weapons[i]
                img = weapon_art.rotated(w.name, -90, scale=2)
                if img is not None:
                    bob = round(math.sin(self.age * 0.05 + i) * 1)
                    surf.blit(img, img.get_rect(midtop=(hx, sy - 62 + bob)))
                surf.fill(rarity_color(w), (hx - 4, sy - 20, 9, 2))

    def draw_prompt(self, screen, camera, ui, frame, prompt):
        sx, sy = camera.to_screen(self.x, self.y - 96)
        n = len(self.run.rack)
        ui.text(screen, f"ARMÁRIO {n}/{RACK_SIZE}", theme.XS, theme.BRASS, (round(sx), round(sy)))
        if prompt:
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, prompt, theme.XS, color, (round(sx), round(sy) + 12))
