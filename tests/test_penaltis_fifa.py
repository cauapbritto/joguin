"""Pênaltis com cara de FIFA (v1.8.1): bola maior, o pé encosta na bola com pausa de impacto,
câmera aproxima do gol e o goleiro pula, agarra e cai sem cortes (poses novas na folha)."""
import unittest

import pygame
from apoio import game
import test_penaltis
from test_penaltis import cena, quadros

from soulstrike.assets import SPORT_POSES
from soulstrike.scenes import penalty as S

HEROES = ("matador", "paredao", "guerreiro", "tanque", "trovao", "ginga")


def ate(scene, state, limit=3000):
    for _ in range(limit):
        quadros(scene, 1)
        if scene.state == state:
            return True
    return False


class PosesTest(unittest.TestCase):
    def test_folhas_tem_chute_espera_e_mergulho(self):
        self.assertIn(("bate", 4), SPORT_POSES)
        self.assertIn(("espera", 2), SPORT_POSES)
        self.assertIn(("mergulho", 2), SPORT_POSES)
        g = game()
        for key in HEROES:
            sprites = S.taker_sprites(g.assets, key, 0)
            parado = pygame.image.tobytes(sprites.pose("costas", "parado", 0), "RGBA")
            for i in range(4):                     # cada quadro do chute é diferente do parado
                self.assertNotEqual(pygame.image.tobytes(sprites.pose("costas", "bate", i), "RGBA"), parado, key)
            hug = sprites.pose("frente", "mergulho", 1)
            self.assertNotEqual(pygame.image.tobytes(hug, "RGBA"),
                                pygame.image.tobytes(sprites.pose("frente", "parado", 0), "RGBA"), key)


class CenaFifaTest(unittest.TestCase):
    tearDown = test_penaltis.CenaTest.tearDown

    def _cena(self):
        teams = [[S.Taker("matador", 0)], [S.Taker("paredao", 1)]]
        scene = cena(teams, mode="treino_penaltis", seed=6)
        scene.shootout.first = 0
        scene._next_kick()
        return scene

    def test_bola_maior_que_antes(self):
        self.assertGreaterEqual(S.BALL_R[0], 20)
        self.assertGreaterEqual(S.BALL_R[1], 10)

    def test_pausa_de_impacto_no_contato(self):
        scene = self._cena()
        self.assertTrue(ate(scene, "voo"))
        self.assertEqual(scene.kick.freeze, S.HIT_STOP)
        quadros(scene, S.HIT_STOP)
        self.assertEqual(scene.kick.flight, 0)                 # a bola ficou no pé
        quadros(scene, 1)
        self.assertEqual(scene.kick.flight, 1)

    def test_camera_aproxima_no_voo_e_volta_depois(self):
        scene = self._cena()
        self.assertTrue(ate(scene, "voo"))
        quadros(scene, 30)
        self.assertGreater(scene.zoom, 1.2)
        self.assertTrue(ate(scene, "entrada"))
        quadros(scene, 30)
        self.assertLess(scene.zoom, 1.05)

    def test_cobranca_inteira_desenha_sem_erro(self):
        scene = self._cena()
        screen = pygame.Surface((960, 540))
        for _ in range(3):                                     # gol, defesa ou fora: tudo desenha
            for _ in range(600):
                quadros(scene, 1, screen)
                if scene.state == "resultado" and scene.t >= S.RESULT_FRAMES - 1:
                    break
            quadros(scene, 2, screen)


if __name__ == "__main__":
    unittest.main()
