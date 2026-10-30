"""Animações do futebol (v1.7): só desenho, nenhuma regra muda."""
import math
import unittest

import pygame
from apoio import GOL_D, MEIO, futebol, game, run

from soulstrike import config
from soulstrike import matches as M


class FutebolAnimacaoTest(unittest.TestCase):
    def test_chute_tem_tres_quadros_e_volta_ao_normal(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.ball.reset(f.x + 30, f.y)
        f.facing = (1.0, 0.0)
        self.assertTrue(match.kick(f, (1.0, 0.0)))
        poses = []
        for _ in range(14):
            run(match, 1)
            poses.append(f._pose())
        self.assertIn(("chute", 1), poses)
        self.assertIn(("chute", 2), poses)
        self.assertNotEqual(poses[-1][0], "chute")

    def test_chute_forte_deixa_rastro(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.ball.reset(f.x + 30, f.y)
        match.kick(f, (1.0, 0.0), loft=1.0)
        run(match, 3)
        self.assertTrue(match.ball.trail)

    def test_carrinho_deita_e_levanta(self):
        match, _ = futebol()
        f = match.fighters[1]
        f.block_timer = 8
        match._animate(f)
        self.assertEqual(f._pose(), ("carrinho", 0))
        self.assertNotEqual(f.spin, 0)
        f.block_timer = 0
        match._animate(f)
        self.assertEqual(f.spin, 0)

    def test_gol_estufa_a_rede_e_o_time_comemora(self):
        match, _ = futebol()
        f = match.fighters[0]
        match.last_touch = f
        match.ball.reset(GOL_D + 30, MEIO)
        run(match, 3)
        self.assertEqual(match.score[0], 1)
        self.assertGreater(match.goals[1].bulge, 0)
        self.assertGreater(f.celebrate, 0)
        run(match, M.NET_BULGE * 3)                       # (com a câmera lenta do gol)
        self.assertEqual(match.goals[1].bulge, 0)


if __name__ == "__main__":
    unittest.main()


class JogadasNovasTest(unittest.TestCase):
    """Jogadas novas do futebol (v1.7), cada uma com o seu contra."""

    def test_curva_sai_aberta_volta_e_perde_forca(self):
        from soulstrike import config
        match, _ = futebol()
        f = match.fighters[0]
        f.x, f.y = 600, MEIO
        f.facing = (1.0, 0.0)
        match.ball.reset(f.x + 28, f.y)
        self.assertEqual(match.curve_of(f, (0.2, 0.0)), 0)
        side = match.curve_of(f, (0.3, 0.9))
        self.assertNotEqual(side, 0)
        match.kick(f, (1.0, 0.0), curve=side)
        ball = match.ball
        start = math.atan2(ball.vy, ball.vx)
        self.assertLess(math.hypot(ball.vx, ball.vy), config.KICK_POWER)
        run(match, config.CURVE_FRAMES + 2)
        end = math.atan2(ball.vy, ball.vx)
        self.assertAlmostEqual(start, -end, delta=0.05)          # abriu e voltou

    def test_dominio_orientado_e_antecipacao(self):
        match, inputs = futebol(humans=(1,))
        f, foe = match.fighters
        f.x, f.y = 800, MEIO
        foe.x, foe.y = 1400, MEIO
        match.ball.reset(f.x + 26, f.y)
        f.last_stick = (0.0, 1.0)
        match._take(f)
        self.assertIs(match.possessor, f)
        self.assertGreater(match.ball.y, f.y + 5)                 # já saiu para baixo
        # marcador colado antecipa
        match2, _ = futebol(humans=(1,))
        f, foe = match2.fighters
        f.x, f.y = 800, MEIO
        match2.ball.reset(f.x + 26, f.y)
        foe.x, foe.y = match2.ball.x + 20, f.y
        foe.marking = True
        f.last_stick = (0.0, 1.0)
        match2._take(f)
        self.assertIs(match2.possessor, foe)

    def test_tabela_devolve_na_frente(self):
        match, inputs = futebol(chars=(4, 2, 6, 8), humans=(1,))
        me = match.fighters[0]
        mate = next(m for m in match.fighters if m.team == me.team and m is not me)
        me.x, me.y = 800, MEIO
        mate.x, mate.y = 1000, MEIO
        for o in match.fighters:
            if o.team != me.team:
                o.x, o.y = 200, 200
        match.ball.reset(me.x + 26, me.y)
        match._take(me)
        self.assertTrue(match.pass_ball(me, direction=(1.0, 0.0)))
        self.assertIsNotNone(me.give_go)
        for _ in range(40):
            run(match, 1)
            if match.possessor is mate:
                break
        self.assertIs(match.possessor, mate)
        self.assertTrue(match.give_and_go(me))
        self.assertIs(match.ball.receiver, me)
        self.assertIsNone(me.give_go)

    def test_ponte_segura_mas_curva_e_cabecada_passam(self):
        match, _ = futebol(humans=(2,))
        keeper = match.fighters[1]
        gx, gy = match.goal_center(keeper.team)
        keeper.x, keeper.y = gx - 60, gy
        keeper.marking = True
        self.assertTrue(match.keeping(keeper))
        ball = match.ball
        ball.reset(gx - 300, gy)
        ball.vx = 9.0
        run(match, 18)                                            # a ponte na hora certa
        self.assertTrue(match.keeper_dive(keeper))
        for _ in range(20):
            run(match, 1)
            if match.possessor is keeper:
                break
        self.assertIs(match.possessor, keeper)
        # mesma bola com curva: a ponte não segura
        match, _ = futebol(humans=(2,))
        keeper = match.fighters[1]
        keeper.x, keeper.y = gx - 60, gy
        keeper.marking = True
        ball = match.ball
        ball.reset(gx - 300, gy)
        ball.vx, ball.curve, ball.curve_timer = 9.0, 0.0, 40
        run(match, 18)
        match.keeper_dive(keeper)
        caught = False
        for _ in range(12):
            run(match, 1)
            caught = caught or (match.possessor is keeper and keeper.diving > 0)
        self.assertFalse(caught)                                  # bateu nele, mas não segurou


class ReplayTest(unittest.TestCase):
    def _gol(self, humans=()):
        match, inputs = futebol(humans=humans)
        f = match.fighters[0]
        match.last_touch = f
        run(match, 60, inputs)                  # grava um pouco de jogo antes
        match.ball.reset(GOL_D + 30, MEIO)
        run(match, 3, inputs)
        self.assertEqual(match.score[0], 1)
        return match, inputs

    def test_gol_tem_replay_em_camera_lenta(self):
        match, _ = self._gol()
        for _ in range(400):
            run(match, 1)
            if match.replay is not None:
                break
        self.assertIsNotNone(match.replay)
        screen = pygame.Surface((960, 540))
        x_before = match.ball.x
        match.draw(screen, game().ui)
        self.assertEqual(match.ball.x, x_before)       # desenhar o replay não mexe no jogo
        frames = 0
        while match.replay is not None and frames < 1000:
            run(match, 1)
            frames += 1
        self.assertGreater(frames, 60)
        run(match, config.GOAL_FREEZE)
        self.assertEqual(match.freeze, 0)

    def test_qualquer_botao_pula_o_replay(self):
        match, inputs = self._gol(humans=(1,))
        for _ in range(400):
            run(match, 1, inputs)
            if match.replay is not None:
                break
        inputs[1].tap("attack")
        run(match, 2, inputs)
        self.assertIsNone(match.replay)


class CpuSemBolaTest(unittest.TestCase):
    def test_cpu_vira_goleiro_quando_o_time_perde_a_bola_perto_do_gol(self):
        from soulstrike.ai import SoccerAI
        match, _ = futebol(chars=(4, 2, 7, 12))
        ai = SoccerAI()
        mine = [f for f in match.fighters if f.team == 0]
        foe = next(f for f in match.fighters if f.team == 1)
        home = match.goal_x(0)
        foe.x, foe.y = home + 260, MEIO
        match.possessor = foe
        match.ball.reset(foe.x + 10, foe.y)
        mine[0].x, mine[0].y = home + 300, MEIO          # este pressiona
        mine[1].x, mine[1].y = home + 600, MEIO + 100    # este volta para o gol
        for _ in range(90):
            ai.update(mine[1], match)
            mine[1].update(match)
        self.assertTrue(mine[1].marking)
        self.assertTrue(match.keeping(mine[1]))

