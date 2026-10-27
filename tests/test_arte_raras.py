"""Arte e brilho das armas raras: toda rara tem sprite e brilha na mão, no golpe e no tiro."""
import unittest

from apoio import game
from test_treino import pular_intro, rodar, treino

from soulstrike import rare_fx, weapon_art
from soulstrike.arsenal import equip
from soulstrike.data import RARE_WEAPONS, duel_arsenal
from soulstrike.forged import FORGED


class ArteRarasTest(unittest.TestCase):
    def test_toda_rara_tem_sprite_e_cor(self):
        game()
        for w in RARE_WEAPONS.values():
            self.assertIsNotNone(weapon_art.icon(w.name), w.name)
            self.assertIn(w.name, rare_fx.ACCENT, w.name)
            self.assertIsNotNone(rare_fx.accent(w))
        self.assertGreater(weapon_art.icon(FORGED["martelo_trovao"].name).get_width(), 20)

    def test_comum_nao_brilha(self):
        ranged, melee = duel_arsenal()
        for w in ranged + melee:
            self.assertIsNone(rare_fx.accent(w), w.name)
        self.assertEqual(rare_fx.tier(RARE_WEAPONS["besta"]), 1)
        self.assertEqual(rare_fx.tier(RARE_WEAPONS["espelho"]), 2)
        self.assertEqual(rare_fx.tier(FORGED["lamina_solar"]), 3)

    def test_rara_solta_faiscas_e_desenha(self):
        screen, ui = game().screen, game().ui
        for w in (FORGED["coracao_inverno"], FORGED["lamina_solar"], RARE_WEAPONS["espelho"]):
            match, inp = treino()
            pular_intro(match, inp)
            equip(match.player, w)
            p, d = match.player, match.dummy
            inp.hold("attack")
            for _ in range(40):
                p.x, p.y = d.x - (50 if w.is_melee else 150), d.y
                p.facing = (1.0, 0.0)
                rodar(match, inp, 1)
                match.draw(screen, ui)
            self.assertTrue(any(isinstance(q, rare_fx.Sparkle) for q in match.particles), w.name)

    def test_arma_comum_nao_solta_faisca(self):
        match, inp = treino()
        pular_intro(match, inp)
        rodar(match, inp, 60)
        self.assertFalse(any(isinstance(q, rare_fx.Sparkle) for q in match.particles))


if __name__ == "__main__":
    unittest.main()
