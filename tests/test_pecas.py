"""Bancas, baú, armário e fogueira desenhados como os heróis, com a cara de cada capítulo."""
import unittest

import pygame

import apoio  # noqa: F401  (janela falsa e progresso temporário)
from soulstrike import pecas
from soulstrike.armario import Armario
from soulstrike.dungeon import Campfire, Chest
from soulstrike.market import Stall


class _Run:
    rack = []


class _Cam:
    x = y = 0


def _desenha(entity):
    surf = pygame.Surface((400, 400), pygame.SRCALPHA)
    entity.x, entity.y = 200, 260
    entity.draw(surf, _Cam())
    return surf.get_bounding_rect()


class PecasTest(unittest.TestCase):
    def test_arte_de_todos_os_capitulos_existe(self):
        for cap in (1, 2, 3, 4):
            for kind in ("loja", "ferreiro"):
                for layer in ("tras", "frente"):
                    self.assertIsNotNone(pecas.image(f"banca_{kind}_{cap}_{layer}"), (kind, cap, layer))
                for pose in ("parado0", "parado1", "ataque0", "ataque1"):
                    self.assertIsNotNone(pecas.npc_frame(kind, cap, pose[:-1], int(pose[-1])), (kind, cap, pose))
            for name in (f"bau_{cap}_fechado", f"bau_{cap}_aberto", f"armario_{cap}", f"fogueira_{cap}"):
                self.assertIsNotNone(pecas.image(name), name)

    def test_banca_tem_gente_atras_do_balcao(self):
        for cap in (1, 2, 3, 4):
            stall = Stall("ferreiro", 200, 260, chapter=cap)
            area = _desenha(stall)
            self.assertGreater(area.height, 100, cap)            # toldo/parede + NPC + balcão
            self.assertGreaterEqual(stall.wall.rect.width, 96)

    def test_capitulos_diferentes_desenham_diferente(self):
        def pixels(entity):
            surf = pygame.Surface((400, 400), pygame.SRCALPHA)
            entity.x, entity.y = 200, 260
            entity.draw(surf, _Cam())
            return pygame.image.tobytes(surf, "RGBA")
        for make in (lambda c: Chest(0, 0, chapter=c), lambda c: Armario(0, 0, _Run(), chapter=c),
                     lambda c: Stall("loja", 0, 0, chapter=c)):
            self.assertEqual(len({pixels(make(c)) for c in (1, 2, 3, 4)}), 4)

    def test_fogueira_do_cap_3_solta_vapor(self):
        self.assertTrue(Campfire(0, 0, 3).steam)
        self.assertFalse(Campfire(0, 0, 1).steam)
        self.assertGreater(Campfire(0, 0, 4).wall.rect.width, Campfire(0, 0, 1).wall.rect.width)

    def test_fora_da_campanha_usa_o_capitulo_1(self):
        self.assertEqual(Stall("loja", 0, 0, chapter=None).chapter, 1)
        self.assertEqual(Chest(0, 0).chapter, 1)
