"""Arsenal do treino: um suporte de armas na arena com todas as armas do jogo, até as mais raras.

Perto do suporte, ATACAR abre a escolha (a arena fica parada). Cada linha é uma raridade: as de
tiro e as de perto dos heróis, as raras do baú, as roubadas do Templo Gelado e as forjadas do
ferreiro. A comum entra no lugar da arma do herói do mesmo tipo; as outras entram como 3ª arma,
igual ao baú da campanha. HABILIDADE devolve as armas do herói, ESQUIVA fecha.
"""
import math

import pygame

from . import config, theme, weapon_art
from .data import RARE_WEAPONS, duel_arsenal, rarity_color
from .dungeon import glow
from .entities import Entity

STICK = 0.55                    # analógico passou disso = um passo na escolha
VISIBLE = 7                     # armas que cabem numa linha (o resto rola para os lados)


def arsenal_rows():
    """As linhas do arsenal: (título, armas), da comum para a mais rara."""
    ranged, melee = duel_arsenal()
    rares = [w for w in RARE_WEAPONS.values() if not w.roubada and not w.forjada]
    stolen = [w for w in RARE_WEAPONS.values() if w.roubada]
    forged = [w for w in RARE_WEAPONS.values() if w.forjada]
    return [("TIRO", list(ranged)), ("PERTO", list(melee)), ("RARAS", rares),
            ("ROUBADAS", stolen), ("FORJADAS", forged)]


def equip(fighter, weapon):
    """Põe a arma na mão: a comum troca a do herói do mesmo tipo; a rara vira a 3ª arma."""
    if weapon.rare:
        fighter.give_relic(weapon)
        return
    base = list(fighter.base_weapons)
    i = next(k for k, w in enumerate(base) if w.is_melee == weapon.is_melee)
    fighter.clips.pop(base[i], None)
    base[i] = weapon
    fighter.loadout = None if tuple(base) == fighter.stats.weapons else tuple(base)
    fighter.weapon_index = i
    fighter.bow_draw = 0


def restore(fighter):
    """Volta às armas do herói (sem a 3ª arma)."""
    fighter.loadout = None
    if fighter.relic is not None:
        fighter.clips.pop(fighter.relic, None)
    fighter.relic = None
    fighter.weapon_index = 0
    fighter.bow_draw = 0


class ArsenalPick:
    """A tela de escolha do arsenal (por cima da arena parada), só do jogador que abriu."""

    HERO = "herói"              # ``chosen`` quando ele devolveu as armas do herói

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.rows = arsenal_rows()
        self.row = 0
        self.picked = [0] * len(self.rows)
        for r, (_, weapons) in enumerate(self.rows):          # começa marcando o que ele já tem
            for k, w in enumerate(weapons):
                if w in fighter.weapons:
                    self.picked[r] = k
                    if w is fighter.weapon:
                        self.row = r
        self.done = False
        self.chosen = None
        self._last = (0, 0)

    @property
    def weapon(self):
        return self.rows[self.row][1][self.picked[self.row]]

    def update(self, controllers):
        inp = controllers.get(self.fighter)
        if inp is None or not hasattr(inp, "pressed"):
            self.done = True
            return
        if self.handle(inp):
            self.match.assets.play("click", 0.3)

    def handle(self, inp):
        if inp.pressed("dodge") or inp.pressed("switch"):
            self.done = True
            return True
        if inp.pressed("special"):
            restore(self.fighter)
            self.chosen = self.HERO
            self.done = True
            return True
        x, y = inp.axis()
        sx = 1 if x > STICK else -1 if x < -STICK else 0
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        moved = False
        if sy and sy != self._last[1]:
            self.row = (self.row + sy) % len(self.rows)
            moved = True
        if sx and sx != self._last[0]:
            weapons = self.rows[self.row][1]
            self.picked[self.row] = (self.picked[self.row] + sx) % len(weapons)
            moved = True
        self._last = (sx, sy)
        if inp.pressed("attack") or inp.pressed("confirm"):
            equip(self.fighter, self.weapon)
            self.chosen = self.weapon
            self.done = True
            moved = True
        return moved

    # ── desenho ──────────────────────────────
    def draw(self, screen, ui):
        W, H = config.SCREEN_W, config.SCREEN_H
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 215))
        screen.blit(veil, (0, 0))
        screen.fill(theme.INK, (W // 2 - 230, 12, 460, 62))            # cobre o relógio do round
        ui.text(screen, "ARSENAL DO TREINO", theme.M, theme.BRASS, (W // 2, 34))
        ui.text(screen, "TODAS AS ARMAS DO JOGO", theme.XS, theme.MUTED, (W // 2, 60))
        rect = pygame.Rect(0, 0, min(W - 64, 860), 0)
        row_h = 74
        rect.h = 8 + row_h * len(self.rows)
        rect.midtop = (W // 2, 84)
        ui.panel(screen, rect, fill=theme.INK_2)
        for r, (label, weapons) in enumerate(self.rows):
            self._draw_row(screen, ui, r, label, weapons, pygame.Rect(rect.x + 10, rect.y + 6 + r * row_h,
                                                                    rect.w - 20, row_h - 4))
        w = self.weapon
        info = pygame.Rect(rect.x, rect.bottom + 8, rect.w, 50)
        ui.panel(screen, info, fill=theme.INK_2)
        kind = "PERTO" if w.is_melee else "TIRO"
        ui.text(screen, f"{w.name.upper()}  ·  {kind}  ·  DANO {w.damage}", theme.XS, rarity_color(w),
                (info.x + 12, info.y + 16), anchor="midleft")
        ui.text(screen, (w.note or "Arma de herói.").upper(), theme.XS, theme.BONE,
                (info.x + 12, info.y + 34), anchor="midleft")
        ui.text(screen, "SETAS: ESCOLHER   ATACAR: PEGAR   HABILIDADE: ARMAS DO HERÓI   ESQUIVA: SAIR",
                theme.XS, theme.MUTED, (W // 2, H - 18))

    def _draw_row(self, screen, ui, r, label, weapons, rect):
        active = r == self.row
        color = rarity_color(weapons[0]) if weapons else theme.MUTED
        ui.text(screen, label, theme.XS, color if active else theme.MUTED, (rect.x, rect.y + 8), anchor="midleft")
        ui.text(screen, f"{self.picked[r] + 1}/{len(weapons)}", theme.XS, theme.MUTED,
                (rect.right, rect.y + 8), anchor="midright")
        n = min(VISIBLE, len(weapons))
        first = min(max(0, self.picked[r] - n // 2), len(weapons) - n)        # a marcada fica no meio
        cell_w = rect.w // VISIBLE
        for j in range(n):
            k = first + j
            w = weapons[k]
            cell = pygame.Rect(rect.x + j * cell_w, rect.y + 16, cell_w - 4, rect.h - 18)
            picked = self.picked[r] == k
            screen.fill(theme.INK_3 if picked else theme.INK, cell)
            if picked:
                pygame.draw.rect(screen, self.fighter.color if active else theme.LINE_HI, cell, 2)
            img = weapon_art.icon(w.name)
            if img is not None:
                big = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
                screen.blit(big, big.get_rect(center=(cell.centerx, cell.y + 19)))
            name = w.name.upper()
            limit = max(4, (cell.w - 6) // 8)
            ui.text(screen, name if len(name) <= limit else name[:limit - 1] + ".", theme.XS,
                    rarity_color(w) if picked or active else theme.FAINT, (cell.centerx, cell.bottom - 9))
        if first > 0:
            ui.text(screen, "<", theme.XS, theme.BONE, (rect.x - 6, rect.centery + 8))
        if first + n < len(weapons):
            ui.text(screen, ">", theme.XS, theme.BONE, (rect.right + 4, rect.centery + 8))


class WeaponRack(Entity):
    """O suporte do arsenal na arena: perto dele, ATACAR abre a escolha de armas."""

    REACH = 70
    SHOW = ("Martelo do Trovão Eterno", "Cajado do Raio Supremo", "Lâmina Solar")    # no suporte

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0

    @property
    def sort_y(self):
        return self.y - 20

    def can_use(self, fighter):
        return fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def update(self, match):
        self.t += 1

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (0, 0, 0), (sx - 40, sy - 2, 80, 14))
        wood, dark = (122, 84, 52), (74, 50, 32)
        for px in (sx - 34, sx + 30):                                   # os dois pés
            surf.fill(dark, (px, sy - 52, 6, 56))
        surf.fill(wood, (sx - 38, sy - 54, 76, 6))                      # travessa de cima
        surf.fill(wood, (sx - 38, sy - 14, 76, 5))                      # travessa de baixo
        g = glow(46, (255, 140, 200), 0.35 + 0.1 * math.sin(self.t * 0.08))
        surf.blit(g, g.get_rect(center=(sx, sy - 34)), special_flags=pygame.BLEND_ADD)
        for k, name in enumerate(self.SHOW):
            img = weapon_art.rotated(name, 90)
            if img is not None:
                surf.blit(img, img.get_rect(center=(sx - 22 + k * 22, sy - 32)))

    def draw_prompt(self, screen, camera, ui, frame, near):
        sx, sy = camera.to_screen(self.x, self.y + 16)
        ui.text(screen, "ARSENAL", theme.XS, theme.BRASS, (round(sx), round(sy)))
        if near:
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: ESCOLHER ARMA", theme.XS, color, (round(sx), round(sy) + 12))
