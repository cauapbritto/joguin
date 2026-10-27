"""Arsenal do treino: dá para pegar qualquer arma do jogo, até as roubadas e as forjadas."""
import unittest

from apoio import game
from test_treino import pular_intro, rodar, treino

from soulstrike.arsenal import ArsenalPick, arsenal_rows, equip
from soulstrike.data import RARE_WEAPONS, duel_arsenal
from soulstrike.forged import FORGED
from soulstrike.training import DONE_FRAMES, LESSONS


def no_arsenal(match):
    p = match.player
    p.x, p.y = match.rack.x, match.rack.y + 30


def abrir(match, inp):
    no_arsenal(match)
    inp.tap("attack")
    rodar(match, inp, 2)
    assert isinstance(match.pick, ArsenalPick), "ATACAR perto do arsenal não abriu a escolha"


def ir_para(match, inp, weapon):
    """Anda pelas linhas e colunas do arsenal até marcar a arma."""
    pick = match.pick
    r = next(i for i, (_, ws) in enumerate(pick.rows) if weapon in ws)
    for axis, target in (("row", r), ("col", None)):
        for _ in range(40):
            if axis == "row" and pick.row == r:
                break
            if axis == "col" and pick.weapon is weapon:
                break
            inp.stick = (0.0, 1.0) if axis == "row" else (1.0, 0.0)
            rodar(match, inp, 1)
            inp.stick = (0.0, 0.0)
            rodar(match, inp, 1)
    assert pick.weapon is weapon


class ArsenalTest(unittest.TestCase):
    def test_tem_todas_as_armas(self):
        weapons = [w for _, ws in arsenal_rows() for w in ws]
        ranged, melee = duel_arsenal()
        for w in list(ranged) + list(melee) + list(RARE_WEAPONS.values()):
            self.assertIn(w, weapons, w.name)
        self.assertIn(FORGED["martelo_trovao"], weapons)
        self.assertEqual(len(weapons), len(set(weapons)))

    def test_pega_o_martelo_do_trovao_pelo_menu(self):
        match, inp = treino()
        pular_intro(match, inp)
        abrir(match, inp)
        hammer = FORGED["martelo_trovao"]
        ir_para(match, inp, hammer)
        inp.tap("attack")
        rodar(match, inp, 2)
        self.assertIsNone(match.pick)
        self.assertIs(match.player.weapon, hammer)
        self.assertIs(match.player.relic, hammer)
        self.assertEqual(match.arsenal_picks, 1)

    def test_comum_troca_a_do_mesmo_tipo_e_habilidade_devolve(self):
        match, inp = treino()
        pular_intro(match, inp)
        p = match.player
        _, melee = duel_arsenal()
        other = next(w for w in melee if w not in p.stats.weapons)
        equip(p, other)
        self.assertIs(p.weapon, other)
        self.assertEqual(len(p.weapons), len(p.stats.weapons))
        self.assertEqual(sum(w.is_melee for w in p.weapons), sum(w.is_melee for w in p.stats.weapons))
        equip(p, RARE_WEAPONS["espelho"])
        self.assertEqual(len(p.weapons), len(p.stats.weapons) + 1)
        abrir(match, inp)
        inp.tap("special")
        rodar(match, inp, 2)
        self.assertIsNone(match.pick)
        self.assertEqual(p.weapons, p.stats.weapons)

    def test_esquiva_fecha_sem_trocar(self):
        match, inp = treino()
        pular_intro(match, inp)
        before = match.player.weapons
        abrir(match, inp)
        x, y = match.dummy.x, match.dummy.y
        inp.tap("dodge")
        rodar(match, inp, 2)
        self.assertIsNone(match.pick)
        self.assertEqual(match.player.weapons, before)
        self.assertEqual(match.arsenal_picks, 0)
        self.assertEqual((match.dummy.x, match.dummy.y), (x, y))

    def test_licao_do_arsenal(self):
        match, inp = treino()
        pular_intro(match, inp)
        match.lesson = len(LESSONS) - 1
        match._begin_lesson()
        abrir(match, inp)
        inp.tap("attack")
        rodar(match, inp, 2)
        self.assertTrue(match.done_timer)
        rodar(match, inp, DONE_FRAMES + 30)
        self.assertTrue(match.finished_lessons)

    def test_toda_arma_funciona_no_boneco(self):
        """Cada arma do arsenal atira/bate no boneco por um tempo sem quebrar o jogo."""
        for _, weapons in arsenal_rows():
            for w in weapons:
                with self.subTest(arma=w.name):
                    match, inp = treino()
                    pular_intro(match, inp)
                    equip(match.player, w)
                    self.assertIs(match.player.weapon, w)
                    p, d = match.player, match.dummy
                    reach = 50 if w.is_melee else 100
                    inp.hold("attack")
                    for k in range(150):
                        p.x, p.y = d.x - reach, d.y
                        p.facing = (1.0, 0.0)
                        if w.charge and k % 50 == 49:
                            inp.release("attack")       # arco: solta para disparar
                        elif w.charge and k % 50 == 0:
                            inp.hold("attack")
                        rodar(match, inp, 1)
                    inp.release("attack")
                    rodar(match, inp, 120)                  # o martelo volta, o buraco negro explode...
                    self.assertGreater(p.damage_dealt, 0, w.name)

    def test_desenha_o_arsenal(self):
        match, inp = treino()
        pular_intro(match, inp)
        screen, ui = game().screen, game().ui
        no_arsenal(match)
        match.draw(screen, ui)
        abrir(match, inp)
        for r in range(len(match.pick.rows)):
            match.pick.row = r
            match.pick.picked[r] = len(match.pick.rows[r][1]) - 1
            match.draw(screen, ui)


if __name__ == "__main__":
    unittest.main()
