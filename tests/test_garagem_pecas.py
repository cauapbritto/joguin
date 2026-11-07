"""As peças da garagem lá embaixo (casa_art) e o chão e a parede "garagem" (scenery)."""
import unittest

import pygame

import apoio  # noqa: F401  (janela falsa e progresso temporário)
from soulstrike import casa_art, scenery


class GaragemPecasTest(unittest.TestCase):
    def test_pecas_desenham_com_o_pe_no_chao(self):
        for fn in (casa_art.tool_cart, casa_art.tire_stack, casa_art.oil_drum, casa_art.trophy_shelf):
            b = casa_art.bake(fn)
            self.assertGreater(b.image.get_width(), 20, fn.__name__)
            self.assertLessEqual(b.dy + b.image.get_height(), 8, fn.__name__)     # nada abaixo do pé (só a sombra)

    def test_trofeus_contam(self):
        vazia = casa_art.bake(casa_art.trophy_shelf, 0).image
        cheia = casa_art.bake(casa_art.trophy_shelf, 4).image
        self.assertNotEqual(pygame.image.tobytes(vazia, "RGBA"), pygame.image.tobytes(cheia, "RGBA"))

    def test_placa_painel_e_vaga(self):
        self.assertGreater(casa_art.bake(casa_art.neon_sign).image.get_width(), 250)
        self.assertGreater(casa_art.bake(casa_art.tool_board).image.get_height(), 60)
        floor = pygame.Surface((300, 200))
        casa_art.parking_bay(floor, 20, 10, 230, 170, "CITY DO JOÃO")
        self.assertEqual(tuple(floor.get_at((22, 100)))[:3], (236, 196, 60))

    def test_chao_e_parede_da_garagem(self):
        floor = scenery.paint_floor("teste_garagem", (400, 300), theme="garagem")
        self.assertIsNotNone(floor)
        style = scenery.wall_style("garagem")
        self.assertIsInstance(style, scenery.GarageWall)
