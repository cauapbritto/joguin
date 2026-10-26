"""Duelo: escolher a arma de tiro e a de perto antes de cada round."""
import random
import unittest

from apoio import FakeInput, game

from soulstrike import config
from soulstrike.data import CHARACTERS, duel_arsenal
from soulstrike.matches import BattleMatch, TeamBattleMatch
from soulstrike.session import Session, SlotSetup
from soulstrike.weapon_pick import LOSER_OPTIONS, OPTIONS, PICK_SECONDS, WeaponChoice

KEYS = [c.key for c in CHARACTERS]


def duelo(mode="duel", chars=("guerreiro", "ninja"), pick=True, humans=(1,)):
    g = game()
    slots = [SlotSetup(i + 1, char=KEYS.index(c), cpu=(i + 1) not in humans) for i, c in enumerate(chars)]
    g.session = Session(mode, slots)
    g.session.weapon_pick = pick
    match = (TeamBattleMatch if mode == "duel2" else BattleMatch)(g, g.session)
    inputs = {}
    for f in match.fighters:
        if f.slot in humans:
            inputs[f.slot] = match.controllers[f] = FakeInput()
    return match, inputs


def toque(match, inp, action=None, stick=None):
    if action:
        inp.tap(action)
    if stick is not None:
        inp.stick = stick
    match.update()
    inp.end_frame()
    inp.stick = (0.0, 0.0)
    match.update()


class ArsenalTest(unittest.TestCase):
    def test_tiro_e_perto_sem_repetir(self):
        ranged, melee = duel_arsenal()
        self.assertTrue(all(not w.is_melee for w in ranged))
        self.assertTrue(all(w.is_melee for w in melee))
        names = [w.name for w in ranged + melee]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(ranged), 10)
        self.assertFalse(any(w.rare for w in ranged + melee))

    def test_quem_perdeu_ve_mais_opcoes(self):
        match, _ = duelo(pick=False)
        f = match.fighters[0]
        normal = WeaponChoice(f, rng=random.Random(1))
        lost = WeaponChoice(f, lost=True, rng=random.Random(1))
        self.assertEqual(len(normal.rows[0]), OPTIONS + 1)
        self.assertEqual(len(lost.rows[1]), LOSER_OPTIONS + 1)
        self.assertEqual(normal.rows[0][0].name, "Arco")      # MANTER: a arma que ele já tem
        self.assertEqual(normal.rows[1][0].name, "Espada")


class EscolhaTest(unittest.TestCase):
    def test_sem_escolha_o_round_comeca_direto(self):
        match, _ = duelo(pick=False)
        self.assertIsNone(match.pick)

    def test_arena_parada_ate_confirmar(self):
        match, inputs = duelo()
        self.assertIsNotNone(match.pick)
        intro = match.intro
        for _ in range(30):
            match.update()
        self.assertEqual(match.intro, intro)                  # o round ainda não começou
        self.assertTrue(match.pick.choices[match.fighters[1]].ready)   # a CPU já escolheu

    def test_escolher_e_confirmar(self):
        match, inputs = duelo()
        p1 = match.fighters[0]
        inp = inputs[1]
        choice = match.pick.choices[p1]
        toque(match, inp, stick=(1.0, 0.0))                   # tiro: a 1ª sorteada
        wanted_ranged = choice.rows[0][1]
        toque(match, inp, "attack")                           # confirma o tiro, desce para o perto
        self.assertEqual(choice.row, 1)
        toque(match, inp, stick=(-1.0, 0.0))                  # perto: a última da lista
        wanted_melee = choice.rows[1][-1]
        toque(match, inp, "attack")
        self.assertIsNone(match.pick)
        self.assertEqual(p1.base_weapons, (wanted_ranged, wanted_melee))
        self.assertIs(p1.weapon, wanted_ranged)
        self.assertEqual(p1.ammo, p1.mag_of(wanted_ranged))

    def test_tempo_acabou_vale_o_marcado(self):
        match, inputs = duelo()
        for _ in range(PICK_SECONDS * config.FPS + 5):
            match.update()
        self.assertIsNone(match.pick)
        self.assertGreater(match.intro, 0)

    def test_novo_round_nova_escolha_e_quem_perdeu_ganha_opcao(self):
        match, inputs = duelo(humans=())
        a, b = match.fighters
        match.update()                                        # as duas CPUs escolhem na hora
        self.assertIsNone(match.pick)
        match.intro = 0
        b.hp = 0
        for _ in range(config.ROUND_END_FRAMES * 3):
            match.update()
            if match.pick is not None:
                break
        self.assertIsNotNone(match.pick)
        self.assertTrue(match.pick.choices[b].lost)
        self.assertFalse(match.pick.choices[a].lost)

    def test_duelo_2x2(self):
        match, inputs = duelo("duel2", ("guerreiro", "ninja", "tanque", "geada"))
        self.assertEqual(len(match.pick.choices), 4)
        match.draw(match.game.screen, match.game.ui)
        for _ in range(PICK_SECONDS * config.FPS + 5):
            match.update()
        self.assertTrue(all(f.loadout for f in match.fighters))


if __name__ == "__main__":
    unittest.main()
