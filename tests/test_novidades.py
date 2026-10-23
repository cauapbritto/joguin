"""Tela de novidades: aparece uma vez quando o jogo abre numa versão nova."""
import unittest

from apoio import game

import pygame

from soulstrike import __version__, novidades, settings
from soulstrike.scenes.menus import NewsScene
from soulstrike.updater import parse_version


class Novidades(unittest.TestCase):
    def test_versao_atual_tem_novidades(self):
        self.assertIn(__version__, novidades.NEWS)
        for version, lines in novidades.NEWS.items():
            self.assertTrue(lines, version)
            parse_version(version)

    def test_mostra_so_o_que_nao_viu(self):
        news = {"1.1.0": ["a"], "1.2.0": ["b"], "1.3.0": ["c"]}
        old = dict(novidades.NEWS)
        novidades.NEWS.clear()
        novidades.NEWS.update(news)
        try:
            self.assertEqual([v for v, _ in novidades.pending("1.1.0", "1.3.0")], ["1.3.0", "1.2.0"])
            self.assertEqual(novidades.pending("1.3.0", "1.3.0"), [])
            self.assertEqual([v for v, _ in novidades.pending("", "1.2.0")], ["1.2.0"])
            self.assertEqual(novidades.pending("", "9.9.9"), [])
        finally:
            novidades.NEWS.clear()
            novidades.NEWS.update(old)

    def test_marca_como_vista(self):
        novidades.mark_seen()
        self.assertEqual(settings.get("versao_vista"), __version__)
        self.assertEqual(novidades.to_show(), [])

    def test_tela_desenha_e_volta_ao_titulo(self):
        g = game()
        scene = NewsScene(g, novidades.pending(""))
        scene.draw(g.screen)
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        self.assertEqual(type(g.scene).__name__, "TitleScene")


if __name__ == "__main__":
    unittest.main()
