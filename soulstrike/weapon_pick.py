"""Duelo: antes de cada round, cada jogador escolhe uma arma de tiro e uma de perto.

Cada um vê a arma que já tem (MANTER) e mais 3 sorteadas de cada tipo; quem perdeu o round
anterior vê 4. Para cima e para baixo troca a linha, para os lados troca a arma, ATACAR confirma.
A CPU escolhe na hora. Acabou o tempo, vale o que estiver marcado.
"""
import random

import pygame

from . import config, theme, weapon_art
from .data import duel_arsenal

PICK_SECONDS = 8
OPTIONS = 3                     # armas sorteadas de cada tipo
LOSER_OPTIONS = 4               # quem perdeu o round anterior escolhe entre mais
STICK = 0.55                    # analógico passou disso = um passo na escolha


class WeaponChoice:
    """A escolha de um lutador: duas linhas (tiro e perto), cada uma com MANTER + as sorteadas."""

    def __init__(self, fighter, lost=False, rng=random):
        ranged_pool, melee_pool = duel_arsenal()
        current = fighter.base_weapons
        cur_ranged = next((w for w in current if not w.is_melee), ranged_pool[0])
        cur_melee = next((w for w in current if w.is_melee), melee_pool[0])
        n = LOSER_OPTIONS if lost else OPTIONS
        self.fighter = fighter
        self.lost = lost
        self.rows = [
            [cur_ranged] + rng.sample([w for w in ranged_pool if w.name != cur_ranged.name], n),
            [cur_melee] + rng.sample([w for w in melee_pool if w.name != cur_melee.name], n),
        ]
        self.picked = [0, 0]
        self.row = 0
        self.ready = False
        self._last = (0, 0)

    @property
    def loadout(self):
        return self.rows[0][self.picked[0]], self.rows[1][self.picked[1]]

    def handle(self, inp):
        """Controle de um jogador (teclado, controle ou celular)."""
        if self.ready:
            if inp.pressed("dodge") or inp.pressed("switch"):
                self.ready = False          # mudou de ideia
            return False
        x, y = inp.axis()
        sx = 1 if x > STICK else -1 if x < -STICK else 0
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        moved = False
        if sy and sy != self._last[1]:
            self.row = (self.row + sy) % 2
            moved = True
        if sx and sx != self._last[0]:
            row = self.rows[self.row]
            self.picked[self.row] = (self.picked[self.row] + sx) % len(row)
            moved = True
        self._last = (sx, sy)
        if inp.pressed("attack") or inp.pressed("confirm"):
            if self.row == 0:
                self.row = 1                # confirmou a de tiro: passa para a de perto
            else:
                self.ready = True
            moved = True
        return moved

    def choose_for_cpu(self, rng=random):
        """A CPU fica com o tipo que ela usa mais e sorteia o resto (às vezes mantém)."""
        for i, row in enumerate(self.rows):
            self.picked[i] = 0 if rng.random() < 0.3 else rng.randrange(len(row))
        self.ready = True


class WeaponPick:
    """A tela de escolha entre um round e outro (por cima da arena parada)."""

    def __init__(self, match, losers=(), rng=random):
        self.match = match
        self.timer = PICK_SECONDS * config.FPS
        self.choices = {}
        for f in match.fighters:
            choice = WeaponChoice(f, lost=f in losers, rng=rng)
            if f.is_cpu:
                choice.choose_for_cpu(rng)
            self.choices[f] = choice

    @property
    def done(self):
        return self.timer <= 0 or all(c.ready for c in self.choices.values())

    def update(self, controllers):
        self.timer -= 1
        for f, choice in self.choices.items():
            ctrl = controllers.get(f)
            if f.is_cpu or ctrl is None or not hasattr(ctrl, "pressed"):
                continue
            if choice.handle(ctrl):
                self.match.assets.play("click", 0.3)
        if self.done:
            self.apply()

    def apply(self):
        for f, choice in self.choices.items():
            melee_first = f.weapon.is_melee
            f.loadout = choice.loadout
            f.weapon_index = 1 if melee_first else 0
            f.clips.clear()
            f.bow_draw = 0

    # ── desenho ──────────────────────────────
    def draw(self, screen, ui):
        W, H = config.SCREEN_W, config.SCREEN_H
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 215))
        screen.blit(veil, (0, 0))
        secs = max(0, (self.timer + config.FPS - 1) // config.FPS)
        screen.fill(theme.INK, (W // 2 - 230, 12, 460, 62))            # cobre o relógio do round
        ui.text(screen, "ESCOLHA AS ARMAS", theme.M, theme.BRASS, (W // 2, 34))
        ui.text(screen, f"{secs}", theme.S, theme.BONE, (W // 2, 60))
        fighters = list(self.choices)
        n = len(fighters)
        cols = 2
        rows = (n + 1) // 2
        pw, ph = 440, 200 if rows > 1 else 300
        top = 80
        for i, f in enumerate(fighters):
            cx = W // 4 + (i % cols) * (W // 2)
            y = top + (i // cols) * (ph + 16)
            self._draw_panel(screen, ui, self.choices[f], pygame.Rect(cx - pw // 2, y, pw, ph))
        ui.text(screen, "SETAS: ESCOLHER   ATACAR: CONFIRMAR   ESQUIVA: VOLTAR", theme.XS, theme.MUTED,
                (W // 2, H - 18))

    def _draw_panel(self, screen, ui, choice, rect):
        f = choice.fighter
        ui.panel(screen, rect, fill=theme.INK_2)
        head = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, 22)
        screen.fill(f.color, (head.x, head.bottom - 2, head.w, 2))
        name = f"{f.label} · {f.stats.name.upper()}"
        ui.text(screen, name, theme.XS, theme.BONE, (head.x + 8, head.centery), anchor="midleft")
        status = "PRONTO" if choice.ready else ("PERDEU: +1 OPÇÃO" if choice.lost else "")
        if status:
            ui.text(screen, status, theme.XS, theme.MOSS if choice.ready else theme.BRASS,
                    (head.right - 8, head.centery), anchor="midright")
        row_h = (rect.h - 30) // 2
        for r, (label, options) in enumerate((("TIRO", choice.rows[0]), ("PERTO", choice.rows[1]))):
            y = rect.y + 28 + r * row_h
            active = r == choice.row and not choice.ready
            ui.text(screen, label, theme.XS, theme.BONE if active else theme.MUTED, (rect.x + 10, y + 8),
                    anchor="midleft")
            cell_w = (rect.w - 20) // len(options)
            for k, w in enumerate(options):
                cell = pygame.Rect(rect.x + 10 + k * cell_w, y + 18, cell_w - 4, row_h - 26)
                picked = choice.picked[r] == k
                screen.fill(theme.INK_3 if picked else theme.INK, cell)
                if picked:
                    pygame.draw.rect(screen, f.color if active else theme.BONE, cell, 2)
                img = weapon_art.icon(w.name)
                if img is not None:
                    scale = 2 if cell.h > 60 else 1
                    big = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
                    screen.blit(big, big.get_rect(center=(cell.centerx, cell.y + cell.h * 0.4)))
                lines = ["MANTER"] if k == 0 else _wrap(w.name.upper(), max(4, (cell.w - 4) // 8))
                for j, line in enumerate(lines[-2:]):
                    ui.text(screen, line, theme.XS, theme.BONE if picked else theme.MUTED,
                            (cell.centerx, cell.bottom - 8 - (len(lines[-2:]) - 1 - j) * 10))
        if choice.ready:
            pygame.draw.rect(screen, theme.MOSS, rect, 2)


def _wrap(text, width):
    """Quebra o nome da arma em linhas de até ``width`` letras (a fonte tem 8 px por letra)."""
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if len(candidate) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return [ln[:width] for ln in lines]
