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
        g.scene = scene
        enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r")
        for _ in scene.pages:                            # ENTER vira as páginas e, na última, sai
            self.assertIs(g.scene, scene)
            scene.update()
            scene.draw(g.screen)
            scene.handle(enter)
        self.assertEqual(type(g.scene).__name__, "TitleScene")

    def test_versao_antiga_vira_uma_pagina(self):
        pages = novidades.pages_of("1.1.0", novidades.NEWS["1.1.0"])
        self.assertEqual(len(pages), 1)
        self.assertIsNone(pages[0][2])
        self.assertEqual(novidades.summary(novidades.NEWS["1.1.0"]), novidades.NEWS["1.1.0"])

    def test_paginas_com_cena_existem(self):
        from soulstrike.scenes.menus import NEWS_SCENES
        for version, entry in novidades.NEWS.items():
            for _, title, scene, lines in novidades.pages_of(version, entry):
                self.assertTrue(title and lines, version)
                if scene is not None:
                    self.assertIn(scene, NEWS_SCENES, version)

    def test_esc_sai_e_setas_viram(self):
        g = game()
        scene = NewsScene(g, novidades.pending(""))
        g.scene = scene
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode=""))
        self.assertEqual(scene.page, 1)
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode=""))
        self.assertEqual(scene.page, 0)
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertEqual(type(g.scene).__name__, "TitleScene")

    def test_opcoes_abre_as_novidades_e_volta(self):
        from soulstrike.scenes.menus import OptionsScene
        g = game()
        opts = OptionsScene(g)
        g.change(opts)
        opts.index = [k for k, _, _ in OptionsScene.ROWS].index("novidades")
        opts.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        news = g.scene
        self.assertIsInstance(news, NewsScene)
        self.assertEqual(len(news.news), len(novidades.NEWS))      # pelo menu, todas as versões
        news.draw(g.screen)
        news.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertIsInstance(g.scene, OptionsScene)

    def test_celular_ve_o_resumo(self):
        from soulstrike.net.remote import hub
        g = game()
        g.change(NewsScene(g, novidades.pending("")))
        status = hub.status()
        self.assertEqual(status["phase"], "news")
        self.assertTrue(status["news"])
        self.assertIn(__version__, status["banner"])


if __name__ == "__main__":
    unittest.main()
