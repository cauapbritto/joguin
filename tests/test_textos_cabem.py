"""Nenhum texto de menu passa da borda do painel onde ele está (nem é cortado com reticências)."""
import unittest

import pygame
from apoio import game

from soulstrike import config, progress
from soulstrike.ui import UI


class _Espiao:
    """Guarda os painéis e textos desenhados num quadro e os textos cortados com reticências."""

    def __enter__(self):
        self.panels, self.texts, self.cuts = [], [], []
        self._panel, self._text, self._clamp = UI.panel, UI.text, UI.clamp_lines
        espiao = self

        def panel(ui, surf, rect, *a, **k):
            if surf.get_size() == (config.SCREEN_W, config.SCREEN_H):
                espiao.panels.append(pygame.Rect(rect))
            return espiao._panel(ui, surf, rect, *a, **k)

        def text(ui, surf, t, size, color, pos, *a, **k):
            r = espiao._text(ui, surf, t, size, color, pos, *a, **k)
            if r is not None and surf.get_size() == (config.SCREEN_W, config.SCREEN_H) \
                    and surf.get_clip() == surf.get_rect():
                espiao.texts.append((t, pygame.Rect(r)))
            return r

        def clamp(ui, lines, size, width, limit):
            if len(lines) > limit:
                espiao.cuts.append(" ".join(lines))
            return espiao._clamp(ui, lines, size, width, limit)

        UI.panel, UI.text, UI.clamp_lines = panel, text, clamp
        return self

    def __exit__(self, *exc):
        UI.panel, UI.text, UI.clamp_lines = self._panel, self._text, self._clamp

    def problemas(self, scene, screen):
        self.panels.clear()
        self.texts.clear()
        self.cuts.clear()
        scene.draw(screen)
        out = [("cortado", c) for c in self.cuts]
        tela = screen.get_rect()
        for t, r in self.texts:
            if not tela.contains(r):
                out.append(("fora da tela", t))
                continue
            donos = [p for p in self.panels if p.collidepoint(r.center) or p.collidepoint(r.topleft)
                     or p.collidepoint(r.topright)]
            if donos and not min(donos, key=lambda p: p.w * p.h).inflate(-4, -4).contains(r):
                out.append(("vaza do painel", t))
        return out


class TextosCabemTest(unittest.TestCase):
    def setUp(self):
        self.g = game()
        for c in (1, 2, 3, 4):
            progress.record_chapter(c)

    def test_descricao_dos_modos(self):
        from soulstrike.scenes.menus import CATEGORY_KEYS, ModeScene
        g = self.g
        scene = ModeScene(g)
        with _Espiao() as espiao:
            for cat in CATEGORY_KEYS:
                scene.open(cat)
                for i, (_, mode) in enumerate(scene.menu.options):
                    scene.menu.index = i
                    self.assertEqual(espiao.problemas(scene, g.screen), [], mode)

    def test_cartoes_da_selecao(self):
        from soulstrike.scenes.select import CharSelectScene
        from soulstrike.session import Session, SlotSetup
        g = self.g
        with _Espiao() as espiao:
            for mode, n in (("duel", 2), ("duel2", 4), ("soccer2", 4), ("basket1", 2), ("basket2", 4),
                            ("campaign", 3), ("campaign", 4)):
                g.session = Session(mode, [SlotSetup(i + 1, cpu=False) for i in range(n)])
                scene = CharSelectScene(g)
                for k in range(len(scene.roster)):
                    for card in scene.cards:
                        scene._change_char(card, 1)
                    self.assertEqual(espiao.problemas(scene, g.screen), [], f"{mode} {n} jogadores, {k}")

    def test_telas_de_info(self):
        from soulstrike.scenes.menus import ControlsScene, CreditsScene, OptionsScene
        g = self.g
        with _Espiao() as espiao:
            for cls in (ControlsScene, OptionsScene, CreditsScene):
                self.assertEqual(espiao.problemas(cls(g), g.screen), [], cls.__name__)

    def test_historias_cabem_na_caixa(self):
        from soulstrike.campaign import STORY
        from soulstrike.scenes.campaign import StoryScene
        g = self.g
        with _Espiao() as espiao:
            for key in STORY:
                scene = StoryScene(g, key, lambda: None)
                for page in range(len(scene.pages)):
                    scene.page = page
                    scene.shown = 10 ** 6
                    self.assertEqual(espiao.problemas(scene, g.screen), [], f"{key} página {page}")

    def test_novidades_nao_somem_itens(self):
        from soulstrike import novidades
        from soulstrike.scenes.menus import NewsScene, TitleScene
        g = self.g
        history = novidades.history()
        scene = NewsScene(g, history, back=TitleScene)
        total = sum(len(p[3]) for v, e in history for p in novidades.pages_of(v, e))
        self.assertEqual(sum(len(p[3]) for p in scene.pages), total)
        with _Espiao() as espiao:
            for page in range(len(scene.pages)):
                scene.page, scene.age = page, 99
                self.assertEqual(espiao.problemas(scene, g.screen), [], scene.pages[page][:2])


if __name__ == "__main__":
    unittest.main()
