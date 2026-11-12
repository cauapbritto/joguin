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

    def test_opcoes_abre_o_arquivo_e_volta(self):
        from soulstrike.scenes.menus import ArchiveScene, OptionsScene
        g = game()
        opts = OptionsScene(g)
        g.change(opts)
        opts.index = [k for k, _, _ in OptionsScene.ROWS].index("novidades")
        opts.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        arquivo = g.scene
        self.assertIsInstance(arquivo, ArchiveScene)
        self.assertEqual(len(arquivo.news), len(novidades.NEWS))   # o arquivo tem todas as versões
        arquivo.draw(g.screen)
        # ENTER assiste à edição escolhida (sem a abertura) e ESC volta para o arquivo no mesmo lugar
        arquivo.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode=""))
        escolhida = arquivo.news[arquivo.index][0]
        arquivo.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        reprise = g.scene
        self.assertIsInstance(reprise, NewsScene)
        self.assertFalse(reprise.opening)
        self.assertEqual([v for v, _ in reprise.news], [escolhida])
        reprise.update()
        reprise.draw(g.screen)
        reprise.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertIsInstance(g.scene, ArchiveScene)
        self.assertEqual(g.scene.index, 1)
        g.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertIsInstance(g.scene, OptionsScene)

    def test_abertura_e_todas_as_versoes_nao_vistas(self):
        from soulstrike.scenes import plantao
        g = game()
        todas = [item for item in novidades.history() if not novidades.special(item[0])]
        scene = NewsScene(g, todas)
        self.assertTrue(scene.opening)
        self.assertIsNone(scene.pages[0])                     # a página 0 é a abertura dos âncoras
        self.assertEqual(len(scene.news), min(len(todas), plantao.MAX_AUTO))
        scene.draw(g.screen)

    def test_toda_noticia_cabe_e_desenha(self):
        """Cada notícia de todas as versões: o texto cabe embaixo da TV e a tela desenha."""
        from soulstrike.scenes import plantao
        g = game()
        scene = NewsScene(g, novidades.history(), back=lambda game: None)
        self.assertTrue(scene.stories)
        for i, story in enumerate(scene.stories):
            height = sum(plantao._line_height(scene.ui, line) for line in story.lines) - 8
            self.assertLessEqual(height, plantao.BODY.h, story.label)
            scene.page, scene.age = i, 30
            scene.draw(g.screen)

    def test_pagina_comprida_vira_duas(self):
        from soulstrike.scenes import plantao
        g = game()
        longa = [{"title": "LONGA", "scene": "loja", "lines": ["palavra " * 40] * 4}]
        partes = plantao.stories_of(g.ui, "9.9.9", longa)
        self.assertGreater(len(partes), 1)
        self.assertEqual(partes[0].part, (1, len(partes)))
        self.assertEqual(sum(len(p.lines) for p in partes), 4)

    def test_celular_vira_e_pula(self):
        from soulstrike.net.remote import hub
        g = game()
        scene = NewsScene(g, novidades.pending("", "1.55.0"))   # edição normal: começa na abertura
        g.change(scene)
        status = hub.status()
        self.assertEqual(status["news_page"]["index"], 0)      # abertura
        slot = next(iter(hub._slots))
        self.assertTrue(hub.news_tap(slot, "next"))
        self.assertFalse(hub.news_tap(slot, "voar"))
        scene.update()
        self.assertEqual(scene.page, 1)
        self.assertEqual(hub.status()["news_page"]["index"], 1)
        hub.news_tap(slot, "prev")
        scene.update()
        self.assertEqual(scene.page, 0)
        hub.news_tap(slot, "skip")
        scene.update()
        self.assertEqual(type(g.scene).__name__, "TitleScene")
        self.assertFalse(hub.news_tap(slot, "next"))           # fora da tela de novidades não vale

    def test_rota_do_celular_pede_token(self):
        from soulstrike.net import server
        self.assertEqual(server.handle_news({"slot": 1, "token": "errado", "go": "next"}), 403)

    def test_celular_ve_o_resumo(self):
        from soulstrike.net.remote import hub
        g = game()
        g.change(NewsScene(g, novidades.pending("")))
        status = hub.status()
        self.assertEqual(status["phase"], "news")
        self.assertTrue(status["news"])
        self.assertIn(__version__, status["banner"])


class EdicaoExtraordinaria(unittest.TestCase):
    def test_extraordinaria_conta_tudo_desde_a_rodada_anterior(self):
        for seen in ("1.46.0", "1.47.0", "1.50.0", "1.55.0"):
            self.assertEqual([v for v, _ in novidades.pending(seen, "1.56.0")], ["1.56.0"], seen)
        older = [v for v, _ in novidades.pending("1.45.0", "1.56.0")]
        self.assertEqual(older, ["1.56.0", "1.46.0"])            # o que veio antes da rodada continua
        self.assertEqual(novidades.pending("1.56.0", "1.56.0"), [])
        self.assertIn("1.50.0", dict(novidades.history()))        # as edições do meio ficam no arquivo

    def test_abre_direto_na_primeira_noticia_com_imagem_propria(self):
        from soulstrike.scenes import plantao
        g = game()
        scene = NewsScene(g, novidades.pending("1.46.0", "1.56.0"))
        self.assertTrue(scene.special)
        self.assertFalse(scene.opening)
        self.assertEqual(scene.current.tv, "extra")
        for story in scene.stories:
            self.assertIn(story.tv, plantao.FOOTAGE, story.label)
        for i in range(len(scene.pages)):
            scene.page, scene.age = i, 30
            for t in (0, 45, 95, 140, 199):
                scene.ticks = t
                scene.draw(g.screen)
        scene.page = 0
        while scene.reveal < len(scene.stories):                  # as manchetes entram uma a uma
            scene.update()
        scene.advance()
        self.assertEqual(scene.page, 1)


if __name__ == "__main__":
    unittest.main()
