"""Tela ESTATÍSTICAS: partidas por modalidade, campanha contra a CPU, heróis mais usados e recordes."""
import pygame

from .. import config, stats, theme
from ..data import CHARACTERS
from .menus import TitleScene, _InfoScene

CAT_LABELS = {"duelos": "DUELOS", "futebol": "FUTEBOL", "basquete": "BASQUETE"}


class StatsScene(_InfoScene):
    heading = "ESTATÍSTICAS"

    def __init__(self, game):
        super().__init__(game)
        self.data = stats.load()
        self.by_key = {c.key: c for c in CHARACTERS}

    def handle(self, event):
        if self.is_back(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN) \
                or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
            self.sfx("cancel", 0.4)
            self.game.change(TitleScene(self.game))

    def draw_body(self, screen):
        W = config.SCREEN_W
        ui, d = self.ui, self.data
        num = stats._num
        left = pygame.Rect(64, 88, 404, 168)
        ui.panel(screen, left)
        ui.text(screen, "PARTIDAS", theme.XS, theme.BRASS, (left.x + 16, left.y + 18), anchor="midleft")
        games = d.get("partidas", {}) if isinstance(d.get("partidas"), dict) else {}
        for i, cat in enumerate(stats.CATEGORIES):
            cx = left.x + 70 + i * 132
            ui.text(screen, str(num(games, cat)), theme.L, theme.BONE, (cx, left.y + 62))
            ui.text(screen, CAT_LABELS[cat], theme.XS, theme.MUTED, (cx, left.y + 92))
        cpu = d.get("contra_cpu", {}) if isinstance(d.get("contra_cpu"), dict) else {}
        ui.text(screen, "CONTRA A CPU", theme.XS, theme.BRASS, (left.x + 16, left.y + 124), anchor="midleft")
        line = (f"{num(cpu, 'vitorias')} VITÓRIAS · {num(cpu, 'empates')} EMPATES · "
                f"{num(cpu, 'derrotas')} DERROTAS")
        ui.text(screen, line, theme.XS, theme.BONE, (left.x + 16, left.y + 146), anchor="midleft")

        right = pygame.Rect(484, 88, W - 548, 168)
        ui.panel(screen, right)
        ui.text(screen, "HERÓIS MAIS USADOS", theme.XS, theme.BRASS, (right.x + 16, right.y + 18), anchor="midleft")
        top = stats.top_heroes(d, 4)
        if not top:
            ui.text(screen, "JOGUE UMA PARTIDA PARA COMEÇAR", theme.XS, theme.FAINT, right.center)
        for i, (key, played, won) in enumerate(top):
            x = right.x + 50 + i * (right.w - 40) // 4
            hero = self.by_key.get(key)
            sprites = self.assets.sprites.get(key)
            if sprites is not None:
                img = sprites.portrait
                screen.blit(img, img.get_rect(midbottom=(x, right.y + 100)))
            name = hero.name.upper() if hero else key.upper()
            ui.text(screen, name, theme.XS, theme.BONE, (x, right.y + 116))
            ui.text(screen, f"{played} JOGOS", theme.XS, theme.MUTED, (x, right.y + 134))
            rate = round(100 * won / played) if played else 0
            ui.text(screen, f"{rate}% VIT.", theme.XS, theme.BRASS if rate >= 50 else theme.FAINT,
                    (x, right.y + 150))

        rec = pygame.Rect(64, 272, W - 128, 34 + 36 * len(stats.RECORD_LABELS))
        ui.panel(screen, rec)
        ui.text(screen, "RECORDES", theme.XS, theme.BRASS, (rec.x + 16, rec.y + 18), anchor="midleft")
        for i, (key, label) in enumerate(stats.RECORD_LABELS.items()):
            y = rec.y + 46 + i * 36
            screen.fill(theme.INK, (rec.x + 10, y - 14, rec.w - 20, 30))
            ui.text(screen, label, theme.XS, theme.MUTED, (rec.x + 24, y), anchor="midleft", shadow=False)
            r = d.get(key)
            if isinstance(r, dict) and num(r, "valor"):
                ui.text(screen, str(r.get("quem", ""))[:24], theme.XS, theme.FAINT, (rec.right - 90, y),
                        anchor="midright", shadow=False)
                ui.text(screen, str(num(r, "valor")), theme.S, theme.BONE, (rec.right - 24, y), anchor="midright")
            else:
                ui.text(screen, "—", theme.XS, theme.FAINT, (rec.right - 24, y), anchor="midright", shadow=False)
        self.footer(screen, [("ESC", "VOLTAR")])
