"""Tela Sobre o projeto: trechos de código atualizados, que cabem na caixa, e troca de página."""
import pathlib
import re
import unittest

import pygame
from apoio import game

from soulstrike.about import CODE_COLS, PAGES, highlight
from soulstrike.scenes.menus import AboutScene

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


class TrechosTest(unittest.TestCase):
    def test_cada_linha_mostrada_existe_no_arquivo(self):
        """Se o código mudar, o trecho da tela precisa mudar junto (este teste avisa)."""
        for page in PAGES:
            source = _flat((ROOT / page.path).read_text(encoding="utf-8"))
            for line in page.code:
                shown = _flat(line).lstrip("# ")
                if shown in ("", "..."):
                    continue
                with self.subTest(page=page.tab, line=line):
                    self.assertTrue(shown in source, f"não achei em {page.path}: {shown}")

    def test_linhas_cabem_na_caixa(self):
        for page in PAGES:
            for line in page.code:
                with self.subTest(page=page.tab, line=line):
                    self.assertLessEqual(len(line), CODE_COLS)

    def test_cores_nao_perdem_texto(self):
        for page in PAGES:
            for line, parts in zip(page.code, highlight(page.code)):
                self.assertEqual("".join(text for text, _ in parts), line)


class NavegacaoTest(unittest.TestCase):
    def setUp(self):
        self.game = game()
        self.scene = AboutScene(self.game)
        self.game.change(self.scene)

    def _key(self, key):
        self.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_setas_trocam_de_pagina_e_dao_a_volta(self):
        self._key(pygame.K_RIGHT)
        self.assertEqual(self.scene.page, 1)
        self._key(pygame.K_LEFT)
        self._key(pygame.K_LEFT)
        self.assertEqual(self.scene.page, len(AboutScene.TABS) - 1)

    def test_todas_as_paginas_desenham_e_clique_na_aba(self):
        for _ in AboutScene.TABS:
            self.scene.draw(self.game.screen)
            self._key(pygame.K_RIGHT)
        rect = self.scene.tab_rects[3]
        self.scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(self.scene.page, 3)


if __name__ == "__main__":
    unittest.main()
