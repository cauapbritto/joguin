"""Modo basquete (etapa 1): medidas da quadra, física da cesta e a partida rodando."""
import math
import random
import unittest

from apoio import FakeInput, game, run

from soulstrike import basketball as B
from soulstrike import config
from soulstrike.arena import BASKET_MAPS, MAPS_BY_KEY, Court
from soulstrike.basket_assist import (aim_point, board_hit, bounce, flight_frames, rim_contact, shot_velocity,
                                      through_hoop)
from soulstrike.matches import create_match
from soulstrike.session import Session, SlotSetup


class Parado:
    def update(self, me, match):
        me.steer(0, 0)


def basquete(chars=(0, 1, 2, 3), humans=(), key="quadra_ginasio"):
    """Partida de basquete com todos parados, menos as vagas em `humans` (controle falso)."""
    g = game()
    slots = [SlotSetup(i + 1, char=c, cpu=(i + 1) not in humans) for i, c in enumerate(chars)]
    g.session = Session("basket2", slots)
    g.session.map_key = key
    match = B.BasketballMatch(g, g.session)
    inputs = {}
    for f in match.fighters:
        if f.slot in humans:
            inputs[f.slot] = match.controllers[f] = FakeInput()
        else:
            match.controllers[f] = Parado()
        f.x, f.y = 900 + f.slot * 40, 1080          # todo mundo longe da jogada
    return match, inputs


def arremesso(match, team, x, y, certo=True):
    """Coloca a bola na mão de alguém do time em (x, y), arremessa e deixa a bola voar."""
    f = next(f for f in match.fighters if f.team == team)
    f.x, f.y = x, y
    match.ball.reset(x, y)
    match._give(f)
    old = dict(B.MAKE_CHANCE)
    B.MAKE_CHANCE.update({k: (1.0 if certo else 0.0) for k in old})
    try:
        match.shoot(f)
    finally:
        B.MAKE_CHANCE.update(old)
    run(match, 200)
    return f


class Medidas(unittest.TestCase):
    def test_aros_espelhados(self):
        self.assertEqual(Court.hoop_x(0), 184)
        self.assertEqual(Court.hoop_x(1), 1816)
        self.assertEqual(Court.hoop_x(0) + Court.hoop_x(1), Court.W)

    def test_linha_de_3_e_garrafao(self):
        self.assertTrue(Court.in_key(0, 300, 600))
        self.assertFalse(Court.in_key(0, 500, 600))
        self.assertTrue(Court.in_key(1, 1700, 700))
        self.assertFalse(Court.is_three(0, 400, 600))
        self.assertTrue(Court.is_three(0, 700, 600))
        self.assertTrue(Court.is_three(1, 1880, 100))        # canto: fora da reta
        self.assertFalse(Court.is_three(1, 1500, 600))

    def test_tres_quadras_com_arte(self):
        for key in BASKET_MAPS:
            cfg = MAPS_BY_KEY[key]
            self.assertFalse(cfg.battle)
            for name in ("cesta.png", "aro_frente.png"):
                self.assertTrue((config.TILES_DIR / key / name).exists(), (key, name))


class Geometria(unittest.TestCase):
    def test_trajetoria_chega_no_alvo(self):
        g = config.GRAVITY
        x, y, z = 600.0, 500.0, 40.0
        n = flight_frames(500)
        vx, vy, vz = shot_velocity(x, y, z, 184, 600, 98, n, g)
        for _ in range(n):
            vz -= g
            x, y, z = x + vx, y + vy, z + vz
        self.assertAlmostEqual(x, 184, places=6)
        self.assertAlmostEqual(y, 600, places=6)
        self.assertAlmostEqual(z, 98, places=6)

    def test_aro_e_rebote(self):
        self.assertIsNone(rim_contact(184, 600, 96, 184, 600, 96, 20, 12))        # no meio: passa
        hit = rim_contact(184 + 26, 600, 100, 184, 600, 96, 20, 12)
        self.assertIsNotNone(hit)
        normal, depth = hit
        self.assertGreater(depth, 0)
        vx, vy, vz = bounce((-3.0, 0.0, -2.0), normal, 0.5)
        self.assertGreater(vx, -3.0)
        self.assertEqual(bounce((3.0, 0.0, 2.0), normal, 0.5), (3.0, 0.0, 2.0))   # já saindo

    def test_cesta_so_descendo_pelo_meio(self):
        self.assertTrue(through_hoop(100, 94, 186, 602, 184, 600, 96, 20, 12))
        self.assertFalse(through_hoop(94, 100, 186, 602, 184, 600, 96, 20, 12))      # subindo
        self.assertFalse(through_hoop(100, 94, 202, 600, 184, 600, 96, 20, 12))      # pela borda

    def test_tabela(self):
        bx = Court.board_x(0)
        self.assertTrue(board_hit(bx + 20, bx + 8, 0, 120, bx, 0, 60, Court.BOARD_Z, 12))
        self.assertFalse(board_hit(bx + 20, bx + 8, 0, 40, bx, 0, 60, Court.BOARD_Z, 12))   # embaixo
        bx = Court.board_x(1)
        self.assertTrue(board_hit(bx - 20, bx - 8, 10, 120, bx, 1, 60, Court.BOARD_Z, 12))

    def test_mira_de_erro_fica_na_borda(self):
        self.assertEqual(aim_point(184, 600, 600, 600, 0, 1), (184, 600))
        x, y = aim_point(184, 600, 600, 600, 26, 1)
        self.assertAlmostEqual(math.hypot(x - 184, y - 600), 26, places=6)


class Partida(unittest.TestCase):
    def setUp(self):
        random.seed(3)

    def test_modo_no_menu_e_create_match(self):
        g = game()
        g.session = Session("basket2", [SlotSetup(i + 1, char=i, cpu=True) for i in range(4)])
        g.session.map_key = "quadra_rua"
        self.assertTrue(g.session.basket)
        match = create_match(g, g.session)
        self.assertIsInstance(match, B.BasketballMatch)
        self.assertEqual(match.arena.cfg.key, "quadra_rua")

    def test_cesta_de_2_e_de_3(self):
        match, _ = basquete()
        side = match.hoop_of(0)
        hx = Court.hoop_x(side)
        dx = -1 if side == 1 else 1
        arremesso(match, 0, hx + dx * 350, 600)
        self.assertEqual(match.score, [2, 0])
        arremesso(match, 0, hx + dx * 600, 600)
        self.assertEqual(match.score, [5, 0])

    def test_enterrada_entra(self):
        for key in BASKET_MAPS:
            match, _ = basquete(key=key)
            side = match.hoop_of(1)
            hx = Court.hoop_x(side)
            arremesso(match, 1, hx + (90 if side == 0 else -90), 620)
            self.assertEqual(match.score, [0, 2], key)

    def test_erro_bate_no_aro_e_nao_conta(self):
        match, _ = basquete()
        side = match.hoop_of(0)
        hx = Court.hoop_x(side)
        arremesso(match, 0, hx + (-400 if side == 1 else 400), 600, certo=False)
        self.assertEqual(match.score, [0, 0])

    def test_quem_leva_sai_com_a_bola(self):
        match, _ = basquete()
        side = match.hoop_of(0)
        arremesso(match, 0, Court.hoop_x(side) + (300 if side == 0 else -300), 600)
        self.assertEqual(match.score[0], 2)
        self.assertIsNotNone(match.holder)
        self.assertEqual(match.holder.team, 1)

    def test_humano_passa_e_arremessa(self):
        match, inputs = basquete(humans=(1,))
        me = next(f for f in match.fighters if f.slot == 1)
        mate = next(f for f in match.fighters if f.team == me.team and f is not me)
        me.x, me.y = 1000, 600
        mate.x, mate.y = 1200, 600
        match.ball.reset(me.x, me.y)
        match._give(me)
        inputs[1].stick = (1.0, 0.0)
        inputs[1].tap("special")
        run(match, 40, inputs)
        self.assertIs(match.holder, mate)

    def test_dez_segundos_de_posse(self):
        match, _ = basquete()
        f = next(f for f in match.fighters if f.team == 0)
        match.ball.reset(f.x, f.y)
        match._give(f)
        run(match, B.SHOT_CLOCK * config.FPS + 2)
        self.assertEqual(match.holder.team, 1)

    def test_intervalo_troca_lado_e_empate_vai_para_proxima_cesta(self):
        match, _ = basquete()
        self.assertEqual(match.hoop_of(0), 1)
        match.clock = 1
        run(match, 2)
        self.assertEqual(match.half, 2)
        self.assertEqual(match.hoop_of(0), 0)
        run(match, 100)
        match.clock = 1
        run(match, 2)
        self.assertTrue(match.overtime)
        self.assertFalse(match.ending)
        run(match, 100)
        side = match.hoop_of(1)
        arremesso(match, 1, Court.hoop_x(side) + (300 if side == 0 else -300), 600)
        self.assertTrue(match.ending or match.finished)
        run(match, 400)
        self.assertTrue(match.finished)
        self.assertEqual(match.result.score, (0, 2))

    def test_cpu_contra_cpu_joga_a_partida_toda(self):
        g = game()
        g.session = Session("basket2", [SlotSetup(i + 1, char=5, cpu=True) for i in range(4)])
        g.session.map_key = "quadra_soul"
        match = create_match(g, g.session)
        screen = g.screen
        frames = 0
        while not match.finished and frames < 2 * (B.HALF_SECONDS + 10) * config.FPS + 3000:
            match.update()
            if frames % 300 == 0:
                match.draw(screen, g.ui)
            frames += 1
        self.assertTrue(match.finished)
        self.assertGreater(sum(match.score), 0)
        self.assertEqual(sum(f.points for f in match.fighters), sum(match.score))


if __name__ == "__main__":
    unittest.main()
