"""PARA ONDE? Entrando no carro, a turma escolhe o capítulo da viagem (só os já liberados).

Menu no mesmo formato do GarageMenu da Casa: ``handle(inp)`` devolve False para fechar, ``draw(screen,
ui, cam, rect)`` desenha a janelinha pequena (ver janelas.py). Escolhido, chama ``on_pick(capítulo)``."""
import pygame

from . import progress, theme

CHAPTERS = (
    (1, "AS SOMBRAS", "FLORESTA E TEMPLO GELADO", (52, 84, 46), (70, 110, 150)),
    (2, "LAG LOBBY", "O PRÉDIO DA PATRULHA CINZA", (62, 62, 68), (38, 40, 60)),
    (3, "CLEPALOVERS", "A CLÍNICA DE ESTÉTICA", (200, 196, 190), (150, 170, 200)),
    (4, "MANSÃO", "A MANSÃO DO CARIMBO", (110, 104, 70), (60, 40, 70)),
)


def unlocked(chapter):
    """O capítulo 1 sempre; os outros, zerado o anterior (a mesma regra do menu da campanha)."""
    return chapter == 1 or progress.chapter_cleared(chapter - 1)


class ChapterPickMenu:
    """A janelinha PARA ONDE? com os quatro capítulos. Analógico escolhe, ATACAR vai, ESQUIVA fecha."""

    def __init__(self, match, fighter, on_pick, current=1):
        self.match = match
        self.fighter = fighter
        self.on_pick = on_pick
        self.index = max(0, min(3, (current or 1) - 1))
        self.age = 0
        self._last = 0

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                         # o ATACAR que abriu não escolhe
        if any(inp.pressed(a) for a in ("dodge", "special", "cancel")):
            self.match.assets.play("cancel", 0.3)
            return False
        _, y = inp.axis()
        sy = 1 if y > 0.5 else -1 if y < -0.5 else 0
        if sy and sy != self._last:
            self.index = (self.index + sy) % len(CHAPTERS)
            self.match.assets.play("click", 0.25)
        self._last = sy
        if inp.pressed("attack") or inp.pressed("confirm"):
            chapter = CHAPTERS[self.index][0]
            if not unlocked(chapter):
                self.match.assets.play("cancel", 0.3)
                return True
            self.match.assets.play("confirm", 0.5)
            self.on_pick(chapter)
            return False
        return True

    def pick(self, item):
        return False

    def snapshot(self):
        return None

    ROW = 30

    def size(self, ui):
        return 270, 44 + self.ROW * len(CHAPTERS) + 18

    def draw(self, screen, ui, cam, rect=None):
        from . import janelas
        if rect is None:
            rect = janelas.default_rect(self.size(ui), cam, self.fighter)
        body = janelas.panel(screen, ui, rect, self.fighter, "PARA ONDE?", accent=theme.BRASS)
        for i, (chapter, name, where, ground, sky) in enumerate(CHAPTERS):
            row = pygame.Rect(body.x, body.y + i * self.ROW, body.w, self.ROW - 2)
            ready = unlocked(chapter)
            if i == self.index:
                pygame.draw.rect(screen, (70, 60, 40), row)
                pygame.draw.rect(screen, theme.BRASS, row, 1)
            thumb = pygame.Rect(row.x + 4, row.y + 4, 32, 20)           # paisagem do capítulo em miniatura
            screen.fill(sky, (thumb.x, thumb.y, thumb.w, 13))
            screen.fill(ground, (thumb.x, thumb.y + 13, thumb.w, 7))
            screen.fill((48, 48, 54), (thumb.x, thumb.y + 16, thumb.w, 3))
            pygame.draw.rect(screen, (20, 18, 24), thumb, 1)
            if not ready:
                shade = pygame.Surface(thumb.size, pygame.SRCALPHA)
                shade.fill((0, 0, 0, 150))
                screen.blit(shade, thumb.topleft)
            color = theme.BONE if ready else (110, 108, 120)
            ui.text(screen, f"{chapter} · {name}", theme.XS, color, (thumb.right + 8, row.y + 9), anchor="midleft")
            sub = where if ready else f"ZERE O CAPÍTULO {chapter - 1}"
            ui.text(screen, sub, theme.XS, theme.MOSS if ready else (110, 108, 120),
                    (thumb.right + 8, row.y + 21), anchor="midleft")
        ui.text(screen, "ATACAR: IR · ESQUIVA: FECHAR", theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 10))
