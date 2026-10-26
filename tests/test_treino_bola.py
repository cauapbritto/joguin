"""Treino do futebol e do basquete: bonecos parados e uma lição por vez."""
import unittest

from apoio import FakeInput, game, run

from soulstrike.data import CHARACTERS
from soulstrike.matches import create_match
from soulstrike.session import MODES, Session, SlotSetup
from soulstrike.training import BASKET_LESSONS, DONE_FRAMES, SOCCER_LESSONS, Standing

KEYS = [c.key for c in CHARACTERS]


def treino(mode):
    g = game()
    n = MODES[mode]["slots"]
    g.session = Session(mode, [SlotSetup(s, char=KEYS.index("velocista"), cpu=s > 1) for s in range(1, n + 1)])
    match = create_match(g, g.session)
    inp = match.controllers[match.player] = FakeInput()
    return match, inp


def passa_licao(match):
    run(match, DONE_FRAMES + 2)


class TreinoFutebolTest(unittest.TestCase):
    def test_bonecos_parados_e_placar_nao_acaba(self):
        match, _ = treino("treino_futebol")
        self.assertIsInstance(match.controllers[match.dummy], Standing)
        self.assertIsNone(match.win_score)
        for _ in range(5):
            match._goal(match.player.team)
        self.assertFalse(match.ending)

    def test_licoes_em_ordem(self):
        match, inp = treino("treino_futebol")
        p = match.player
        match.freeze = 0
        inp.tap("dodge")
        run(match, 2)
        self.assertTrue(match.done_timer)
        passa_licao(match)
        self.assertEqual(match.lesson, 1)
        match.last_touch = p
        match.ball.vx = 9.0
        run(match, 1)
        passa_licao(match)
        match.last_touch = p
        match.ball.z = 40
        run(match, 1)
        passa_licao(match)
        self.assertEqual(SOCCER_LESSONS[match.lesson].item, "dummy_ball")
        match.state["marked"] = 999
        run(match, 1)
        passa_licao(match)
        match._goal(p.team)
        run(match, 2 * DONE_FRAMES + 10)             # o gol tem câmera lenta
        self.assertTrue(match.finished_lessons)
        match.draw(match.game.screen, match.game.ui)


class TreinoBasqueteTest(unittest.TestCase):
    def test_barrinha_no_tempo(self):
        match, _ = treino("treino_basquete")
        p = match.player
        run(match, 60)                              # a bola vem para a mão dele
        self.assertIs(match.holder, p)
        match.start_shot(p)
        match.release_shot(p, 0.5)
        run(match, 1)
        self.assertTrue(match.done_timer)

    def test_boneco_arremessa_na_licao_do_toco(self):
        match, _ = treino("treino_basquete")
        match.lesson = 2
        match._begin_lesson()
        self.assertEqual(BASKET_LESSONS[2].item, "dummy_shot")
        run(match, 3)
        self.assertIs(match.holder, match.dummy)
        self.assertTrue(match.dummy.jump_shot)
        match.jump(match.player)
        run(match, 40)
        self.assertGreater(match.player.blocks, 0)
        match.draw(match.game.screen, match.game.ui)


if __name__ == "__main__":
    unittest.main()
