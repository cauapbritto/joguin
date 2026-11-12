"""O visual da arma muda ao evoluir (+1, +2, +3) e ao encantar (fogo, gelo, raio) no ferreiro."""
import unittest

import pygame

from apoio import game
from test_armas_raras import campo

from soulstrike import weapon_art


def cores(img):
    w, h = img.get_size()
    return {tuple(img.get_at((x, y))) for x in range(w) for y in range(h) if img.get_at((x, y)).a}


class VisualTest(unittest.TestCase):
    def setUp(self):
        game()

    def test_sem_nada_e_a_arte_normal(self):
        self.assertEqual(weapon_art.styled("Espada", 0, None), "Espada")
        self.assertEqual(weapon_art.styled("Arma que não existe", 3, "fogo"), "Arma que não existe")

    def test_cada_nivel_e_encanto_tem_um_desenho_diferente(self):
        seen = []
        for level in range(4):
            for enchant in (None, "fogo", "gelo", "raio"):
                key = weapon_art.styled("Espada", level, enchant)
                img = weapon_art.icon2x(key)
                self.assertIsNotNone(img, key)
                self.assertEqual(img.get_size(), weapon_art.icon2x("Espada").get_size())
                seen.append(frozenset(cores(img)))
        self.assertEqual(len(set(seen)), 16)
        self.assertIs(weapon_art.icon2x(weapon_art.styled("Espada", 2, "gelo")),
                      weapon_art.icon2x(weapon_art.styled("Espada", 2, "gelo")))      # feito uma vez só

    def test_fogo_deixa_a_lamina_quente(self):
        img = weapon_art.icon2x(weapon_art.styled("Espada", 0, "fogo"))
        quentes = [c for c in cores(img) if c[0] > 200 and c[2] < 90]
        self.assertTrue(quentes)

    def test_na_mao_usa_o_visual_do_ferreiro(self):
        match, p = campo("besta")
        p.weapon_index = 1
        self.assertEqual(p.weapon_art_name(), "Espada")
        p.forge["Espada"] = [2, "raio"]
        self.assertEqual(p.weapon_art_name(), "Espada|2|raio")
        for _ in range(3):
            match.update()
        match.draw(match.game.screen, match.game.ui)            # desenha na mão e na bolsa do HUD
        self.assertIsInstance(match.game.screen, pygame.Surface)


if __name__ == "__main__":
    unittest.main()
