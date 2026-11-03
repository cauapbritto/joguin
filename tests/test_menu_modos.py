"""Tela de modos em dois níveis: modalidades (cartões) e os modos de cada uma."""
import unittest

import pygame
from apoio import game

from soulstrike import settings
from soulstrike.scenes.menus import CATEGORY_KEYS, MODE_GROUPS, MODE_TEXT, ModeScene, TitleScene, category_of
from soulstrike.scenes.select import CharSelectScene, LobbyScene
from soulstrike.session import MODES


def tecla(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


class ModosTest(unittest.TestCase):
    def setUp(self):
        game()
        settings.path().unlink(missing_ok=True)
        settings.load()

    def tearDown(self):
        settings.path().unlink(missing_ok=True)
        settings.load()

    def test_todo_modo_esta_em_uma_modalidade(self):
        listed = [m for groups in MODE_GROUPS.values() for _, modes in groups for m in modes]
        self.assertEqual(len(listed), len(set(listed)))
        for mode in MODES:
            if mode == "campaign":
                continue
            self.assertIn(mode, listed, mode)
            self.assertIn(mode, MODE_TEXT)
        self.assertEqual(category_of("penaltis"), "futebol")
        self.assertEqual(category_of("treino"), "duelos")
        self.assertEqual(category_of("treino_basquete"), "basquete")

    def test_primeiro_nivel_mostra_4_cartoes(self):
        g = game()
        scene = ModeScene(g)
        g.scene = scene
        self.assertIsNone(scene.category)
        self.assertEqual(len(scene.card_rects), 4)
        scene.draw(g.screen)
        scene.handle(tecla(pygame.K_RIGHT))
        scene.handle(tecla(pygame.K_RIGHT))
        self.assertEqual(CATEGORY_KEYS[scene.cat_index], "futebol")
        scene.handle(tecla(pygame.K_RETURN))
        self.assertEqual(scene.category, "futebol")
        values = [v for _, v in scene.menu.options]
        self.assertEqual(values, ["soccer1", "soccer2", "penaltis", "desafio_goleiro", "treino_futebol",
                                  "treino_penaltis"])
        scene.draw(g.screen)
        # LB/RB (PageUp/PageDown) trocam de modalidade sem voltar
        scene.handle(tecla(pygame.K_PAGEDOWN))
        self.assertEqual(scene.category, "basquete")
        scene.handle(tecla(pygame.K_PAGEDOWN))
        self.assertEqual(scene.category, "campanha")
        scene.draw(g.screen)
        # Esc volta aos cartões, e de lá ao título
        scene.handle(tecla(pygame.K_ESCAPE))
        self.assertIsNone(scene.category)
        scene.handle(tecla(pygame.K_ESCAPE))
        self.assertIsInstance(g.scene, TitleScene)

    def test_todas_as_modalidades_desenham(self):
        g = game()
        for cat in CATEGORY_KEYS:
            scene = ModeScene(g, cat)
            for i in range(len(scene.menu.options)):
                scene.menu.index = i
                scene.draw(g.screen)

    def test_lembra_o_ultimo_modo(self):
        g = game()
        settings.change("ultimo_modo", "")
        scene = ModeScene(g, "basquete")
        g.scene = scene
        scene.handle(tecla(pygame.K_RETURN))                # BASQUETE 1 x 1 (o primeiro)
        self.assertIsInstance(g.scene, LobbyScene)
        self.assertEqual(settings.get("ultimo_modo"), "basket1")
        scene = ModeScene(g)
        self.assertEqual(CATEGORY_KEYS[scene.cat_index], "basquete")
        # voltar do lobby cai dentro da modalidade
        g.scene.handle(tecla(pygame.K_ESCAPE))
        self.assertIsInstance(g.scene, ModeScene)
        self.assertEqual(g.scene.category, "basquete")

    def test_clique_no_cartao_abre(self):
        g = game()
        scene = ModeScene(g)
        scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=scene.card_rects[1].center))
        self.assertEqual(scene.category, "duelos")
        scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=scene.menu.rects[0].center))
        self.assertIsInstance(game().scene, CharSelectScene)
        self.assertEqual(game().session.mode, "cpu")

    def test_capitulo_2_so_depois_de_zerar(self):
        g = game()
        from soulstrike import progress
        values = [v for _, v in ModeScene(g, "campanha").menu.options]
        self.assertEqual("campaign2" in values, progress.campaign_cleared())


if __name__ == "__main__":
    unittest.main()
