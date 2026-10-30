"""Regras da disputa de pênaltis (soulstrike/penalty.py) e a cena de frente (scenes/penalty.py)."""
import random
import unittest

import pygame
from apoio import FakeInput, game

from soulstrike import penalty as P
from soulstrike import progress
from soulstrike.data import CHARACTERS
from soulstrike.scenes import penalty as S
from soulstrike.session import Session, SlotSetup


class MiraTest(unittest.TestCase):
    def test_analogico_vira_casa_da_grade(self):
        self.assertEqual(P.aim_from_axis(0, 0), (0, 1))
        self.assertEqual(P.aim_from_axis(-1, -1), (-1, 2))
        self.assertEqual(P.aim_from_axis(1, 0.1), (1, 1))
        self.assertEqual(P.aim_from_axis(0, 1), (0, 0))
        for cell in ((-1, 0), (0, 2), (1, 1)):
            self.assertEqual(P.aim_from_axis(*P.axis_of(cell)), cell)

    def test_angulo_tem_faixa_menor(self):
        style = P.kick_style("matador")
        lo, hi, _ = P.sweet_band(style, (1, 2))
        lo2, hi2, _ = P.sweet_band(style, (1, 0))
        self.assertLess(hi - lo, hi2 - lo2)

    def test_todo_heroi_tem_jeito_de_bater_e_de_defender(self):
        for c in CHARACTERS:
            self.assertIn(c.key, P.KICK_STYLES)
            self.assertIn(c.key, P.SAVE_STYLES)


class ChuteTest(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(3)
        self.kick = P.kick_style("matador")
        self.keep = P.save_style("matador")

    def test_forca_demais_isola(self):
        shot = P.make_shot((1, 2), 0.99, self.kick, self.rng)
        self.assertEqual(shot.kind, "isolou")
        self.assertFalse(P.resolve(shot, None, self.kick, self.keep, self.rng).goal)

    def test_canto_certo_com_forca_boa_e_goleiro_do_outro_lado_e_gol(self):
        shot = P.make_shot((1, 0), 0.66, self.kick, self.rng)
        out = P.resolve(shot, P.Dive((-1, 0), -2), self.kick, self.keep, self.rng)
        self.assertTrue(out.goal)

    def test_goleiro_no_canto_certo_defende(self):
        shot = P.make_shot((1, 0), 0.66, self.kick, self.rng)
        out = P.resolve(shot, P.Dive((1, 0), -2), self.kick, self.keep, self.rng)
        self.assertFalse(out.goal)
        self.assertIn(out.result, ("defesa", "espalmou"))

    def test_pulo_atrasado_nao_alcanca(self):
        shot = P.make_shot((1, 0), 0.7, self.kick, self.rng)
        out = P.resolve(shot, P.Dive((1, 0), shot.frames - 2), self.kick, self.keep, self.rng)
        self.assertTrue(out.goal)

    def test_chute_fraco_vai_para_o_meio(self):
        weak = P.make_shot((1, 1), 0.2, self.kick, self.rng)
        good = P.make_shot((1, 1), 0.66, self.kick, self.rng)
        self.assertLess(abs(weak.x), abs(good.x))
        self.assertGreater(weak.frames, good.frames)

    def test_cavadinha_depende_do_goleiro(self):
        chip = P.make_shot((1, 1), 0.5, self.kick, self.rng, chip=True)
        self.assertTrue(P.resolve(chip, P.Dive((1, 1), -4), self.kick, self.keep, self.rng).goal)
        self.assertFalse(P.resolve(chip, None, self.kick, self.keep, self.rng).goal)
        ninja = P.save_style("ninja")
        self.assertFalse(P.resolve(chip, P.Dive((1, 1), -4), self.kick, ninja, self.rng).goal)

    def test_decisiva_desvia_menos_para_o_matador(self):
        def spread(key):
            style = P.kick_style(key)
            rng = random.Random(1)
            return sum(abs(P.make_shot((1, 1), 0.66, style, rng, decisive=True).y - 0.51) for _ in range(200))
        self.assertLess(spread("matador"), spread("guerreiro"))


class JeitoDeCadaHeroiTest(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(5)

    def test_tanque_so_bate_no_meio(self):
        shot = P.make_shot((1, 2), 0.66, P.kick_style("tanque"), self.rng)
        self.assertEqual(shot.cell[0], 0)

    def test_paradinha_troca_de_canto_se_o_goleiro_pular_cedo(self):
        ginga = P.kick_style("ginga")
        shot = P.make_shot((1, 1), 0.66, ginga, self.rng, early_dive=(1, 1))
        self.assertEqual(shot.cell[0], -1)
        self.assertEqual(shot.note, "paradinha")
        hacked = P.make_shot((1, 1), 0.66, ginga, self.rng, early_dive=(1, 1), hacked=True)
        self.assertEqual(hacked.cell[0], 1)
        waited = P.make_shot((1, 1), 0.66, ginga, self.rng)
        self.assertLess(waited.power, 0.66)

    def test_drible_magico_troca_o_canto_no_ar(self):
        shot = P.make_shot((1, 1), 0.66, P.kick_style("faisca"), self.rng)
        self.assertLess(shot.x, 0)
        self.assertGreater(shot.swap_at, 0)

    def test_trovao_e_o_mais_rapido(self):
        raio = P.make_shot((1, 1), 0.7, P.kick_style("trovao"), self.rng)
        normal = P.make_shot((1, 1), 0.7, P.kick_style("matador"), self.rng)
        self.assertLess(raio.frames, normal.frames)

    def test_guerreiro_goleiro_nunca_da_rebote(self):
        guerreiro = P.save_style("guerreiro")
        rng = random.Random(2)
        kicker = P.kick_style("aryel_corrompido")
        for _ in range(50):
            shot = P.make_shot((1, 0), 0.66, kicker, rng)
            out = P.resolve(shot, P.Dive((1, 0), -3), kicker, guerreiro, rng)
            self.assertNotEqual(out.result, "rebote")

    def test_trovao_goleiro_sempre_espalma(self):
        trovao = P.save_style("trovao")
        kicker = P.kick_style("matador")
        shot = P.make_shot((1, 0), 0.55, kicker, self.rng)
        out = P.resolve(shot, P.Dive((1, 0), -3), kicker, trovao, random.Random(9))
        self.assertIn(out.result, ("espalmou", "rebote"))

    def test_gancho_do_goleiro_so_uma_vez(self):
        pirata = P.save_style("pirata")
        kicker = P.kick_style("matador")
        shot = P.make_shot((1, 2), 0.6, kicker, self.rng)
        dive = P.Dive((1, 0), -10)          # pulou baixo e a bola foi no alto do mesmo lado
        first = P.resolve(shot, dive, kicker, pirata, self.rng)
        self.assertIn("gancho", first.used)
        again = P.resolve(shot, dive, kicker, pirata, self.rng, keeper_tricks=("gancho",))
        self.assertNotIn("gancho", again.used)

    def test_cpu_nunca_ve_o_canto_escondido(self):
        # com o sinal escondido (Ninja), a CPU acerta o lado só por sorte
        rng = random.Random(4)
        ninja = P.kick_style("ninja")
        paredao = P.save_style("paredao")
        right = sum(1 for _ in range(400)
                    if (d := P.cpu_dive((1, 1), ninja, paredao, "dificil", rng)).cell and d.cell[0] == 1)
        rng = random.Random(4)
        matador = P.kick_style("matador")
        right_tell = sum(1 for _ in range(400)
                         if (d := P.cpu_dive((1, 1), matador, paredao, "dificil", rng)).cell and d.cell[0] == 1)
        self.assertGreater(right_tell, right + 60)


class DisputaTest(unittest.TestCase):
    def test_cinco_cobrancas_e_morte_subita(self):
        s = P.Shootout([["a"], ["b"]], [["ka"], ["kb"]])
        for _ in range(5):
            s.record(True)
            s.record(True)
        self.assertIsNone(s.winner)
        self.assertTrue(s.sudden_death)
        s.record(True)
        self.assertIsNone(s.winner)
        s.record(False)
        self.assertEqual(s.winner, 0)

    def test_acaba_antes_quando_nao_da_mais_para_alcancar(self):
        s = P.Shootout([["a"], ["b"]], [["ka"], ["kb"]])
        for _ in range(3):
            s.record(True)
            s.record(False)
        self.assertEqual(s.winner, 0)       # 3 x 0 com 2 cobranças para cada: acabou

    def test_cobranca_decisiva(self):
        s = P.Shootout([["a"], ["b"]], [["ka"], ["kb"]])
        for _ in range(4):
            s.record(True)
            s.record(True)
        s.record(False)
        self.assertTrue(s.decisive())       # B faz e ganha
        s2 = P.Shootout([["a"], ["b"]], [["ka"], ["kb"]])
        self.assertFalse(s2.decisive())

    def test_revezamento_de_batedor_e_goleiro(self):
        s = P.Shootout([["a1", "a2"], ["b1", "b2"]], [["a1", "a2"], ["b1", "b2"]])
        self.assertEqual((s.kicker(), s.keeper()), ("a1", "b1"))
        s.record(True, (1, 1), "a1")
        self.assertEqual((s.kicker(), s.keeper()), ("b1", "a1"))
        s.record(False)
        self.assertEqual((s.kicker(), s.keeper()), ("a2", "b2"))
        self.assertEqual(s.corners["a1"], [(1, 1)])



class Controle(FakeInput):
    def set_layout(self, layout):
        self.layout = layout


def cena(teams, mode="penaltis", seed=1, inputs=()):
    g = game()
    for slot in inputs:
        g.inputs[slot] = Controle()
    return S.PenaltyScene(g, teams, mode=mode, seed=seed)


def quadros(scene, n, screen=None):
    for _ in range(n):
        scene.update()
        if screen is not None:
            scene.draw(screen)
        for inp in scene.game.inputs.values():
            if hasattr(inp, "end_frame"):
                inp.end_frame()


class CenaTest(unittest.TestCase):
    def tearDown(self):
        from soulstrike.controls import PlayerInput
        g = game()
        for slot in g.inputs:
            g.inputs[slot] = PlayerInput(slot)

    def test_cpu_contra_cpu_vai_ate_o_fim_e_salva_estatisticas(self):
        teams = [[S.Taker("matador", 0), S.Taker("ginga", 0)], [S.Taker("paredao", 1), S.Taker("trovao", 1)]]
        scene = cena(teams)
        screen = pygame.Surface((960, 540))
        for _ in range(9000):
            quadros(scene, 1, screen if scene.ticks % 7 == 0 else None)
            if scene.state == "fim":
                break
        self.assertEqual(scene.state, "fim")
        self.assertIsNotNone(scene.shootout.winner)
        scene.draw(screen)
        data = progress.load()["penaltis"]
        self.assertIn("matador", data["batedores"])
        kicks = sum(t.kicks for team in teams for t in team)
        self.assertEqual(kicks, sum(len(k) for k in scene.shootout.kicks))

    def test_humano_segura_chute_e_solta_no_canto(self):
        teams = [[S.Taker("matador", 0, slot=1, cpu=False)], [S.Taker("paredao", 1)]]
        scene = cena(teams, mode="treino_penaltis", inputs=(1,))
        scene.shootout.first = 0
        scene._next_kick()
        inp = scene.game.inputs[1]
        quadros(scene, 61)
        self.assertEqual(scene.state, "mira")
        inp.hold("attack")
        quadros(scene, 35)
        self.assertTrue(scene.kick.charging)
        inp.release("attack")
        inp.stick = (1.0, -1.0)            # alto à direita
        quadros(scene, 1)
        self.assertEqual(scene.state, "corrida")
        quadros(scene, scene.kick.run + 1)
        self.assertEqual(scene.kick.cell, (1, 2))
        self.assertIsNotNone(scene.kick.shot)

    def test_goleiro_humano_pula_com_a_esquiva(self):
        teams = [[S.Taker("matador", 0)], [S.Taker("paredao", 1, slot=1, cpu=False)]]
        scene = cena(teams, mode="treino_penaltis", inputs=(1,))
        scene.shootout.first = 0
        scene._next_kick()
        self.assertIs(scene.kick.keeper, teams[1][0])
        inp = scene.game.inputs[1]
        for _ in range(400):
            quadros(scene, 1)
            if scene.state == "corrida":
                break
        inp.stick = (-1.0, 0.0)
        inp.tap("dodge")
        quadros(scene, 1)
        self.assertEqual(scene.kick.dive.cell, (-1, 1))
        self.assertLess(scene.kick.dive.t, 0)

    def test_catimba_tres_vezes_da_amarelo(self):
        teams = [[S.Taker("matador", 0)], [S.Taker("paredao", 1, slot=1, cpu=False)]]
        scene = cena(teams, mode="treino_penaltis", inputs=(1,))
        scene.shootout.first = 0
        scene._next_kick()
        keeper = teams[1][0]
        for _ in range(3):
            scene.state, scene.kick.catimba = "mira", 0
            scene._catimba()
        self.assertEqual(keeper.yellows, 1)
        self.assertTrue(scene.kick.card)

    def test_desafio_do_goleiro(self):
        g = game()
        g.session = Session("desafio_goleiro", [SlotSetup(1, char=18), SlotSetup(2, cpu=True)])
        g.inputs[1] = Controle()
        scene = S.start_penalties(g)
        self.assertEqual(scene.challenge["round"], 1)
        self.assertTrue(all(t.cpu for t in scene.teams[1]))
        self.assertIs(scene.kick.keeper, scene.teams[0][0])
        scene.kick.outcome = P.Outcome(False, "defesa", "QUE DEFESA!")
        for _ in range(3):
            scene._record(scene.kick.outcome)
        self.assertEqual(scene.challenge["round"], 2)

    def test_empate_com_penaltis_abre_a_disputa(self):
        from apoio import futebol
        match, _ = futebol()
        match.session.soccer_length = "penaltis"
        match.tiebreak, match.clock = "penaltis", 1
        match._tick_clock()
        self.assertTrue(match.penalties)
        nxt = match.next_scene()
        self.assertIsInstance(nxt, S.PenaltyScene)
        self.assertIs(nxt.match, match)


if __name__ == "__main__":
    unittest.main()
