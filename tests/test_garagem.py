"""Garagem da Casa (escolher City, Uno ou moto) e a armadura de Uno do capítulo 1."""
import unittest

import pygame
from test_casa import casa_da_turma, passo, reset_progress

from soulstrike import casa, config
from soulstrike.casa import UNO_STAND, VEHICLES, GarageMenu, door_open, vehicle_ready
from soulstrike.fighter import UNO_HITS, UNO_SLOW, uno_pieces


def _junto_da_garagem(match, p):
    _, _, (x, y), _ = next(d for d in match.doors if d[0] == "garagem")
    p.x, p.y = x, y + 20


def _junto_da_armadura(p):
    x, y = UNO_STAND
    p.x, p.y = x, y + 20


class GaragemTest(unittest.TestCase):
    def test_garagem_aberta_desde_o_comeco(self):
        reset_progress()
        self.assertTrue(door_open("garagem"))
        self.assertTrue(vehicle_ready("city"))
        self.assertFalse(vehicle_ready("uno"))
        self.assertFalse(vehicle_ready("moto"))
        reset_progress(capitulo1_zerado=True)
        self.assertTrue(vehicle_ready("uno"))
        self.assertFalse(vehicle_ready("moto"))
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        self.assertTrue(vehicle_ready("moto"))
        reset_progress()

    def test_menu_da_garagem_troca_o_carro(self):
        reset_progress(capitulo1_zerado=True)
        match, inputs = casa_da_turma()
        p = match.players[0]
        _junto_da_garagem(match, p)
        self.assertTrue(match.garage_near(p))
        self.assertTrue(match.interact(p))
        menu = match.menus[p]
        self.assertIsInstance(menu, GarageMenu)
        menu.age = 5
        menu.index = [k for k, _, _ in VEHICLES].index("uno")
        inputs[p.slot].tap("attack")
        menu.handle(inputs[p.slot])
        self.assertEqual(match.run.vehicle, "uno")
        menu.index = [k for k, _, _ in VEHICLES].index("moto")      # ainda trancada
        inputs[p.slot].end_frame()
        inputs[p.slot].tap("attack")
        menu.handle(inputs[p.slot])
        self.assertEqual(match.run.vehicle, "uno")
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        menu.draw(screen, match.game.ui, (400, 400))
        reset_progress()

    def test_moto_estaciona_do_lado_do_city(self):
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        match, _ = casa_da_turma()
        match.choose_vehicle("moto")
        self.assertIn(match.parked_moto, match.props)
        match.choose_vehicle("city")
        self.assertIsNone(match.parked_moto)
        reset_progress()

    def test_a_viagem_vai_no_carro_escolhido(self):
        reset_progress(capitulo1_zerado=True)
        match, inputs = casa_da_turma()
        match.choose_vehicle("uno")
        area = match.door_area
        for k, p in enumerate(match.players):
            p.x, p.y = area.x + 20 + 40 * k, area.bottom - 10
        from soulstrike.campaign import LEAVE_FRAMES, PASSAGE_FRAMES
        passo(match, inputs, PASSAGE_FRAMES + LEAVE_FRAMES + 2)
        scene = match.next_scene()
        self.assertEqual(scene.vehicle, "uno")
        reset_progress()


class ArmaduraTest(unittest.TestCase):
    def test_vestir_a_armadura(self):
        reset_progress()
        match, _ = casa_da_turma()
        p, q = match.players[:2]
        _junto_da_armadura(p)
        self.assertTrue(match.armor_near(p))
        self.assertTrue(match.interact(p))
        self.assertEqual(p.uno_hits, UNO_HITS)
        self.assertEqual(match.run.armor, {p.slot: UNO_HITS})
        _junto_da_armadura(q)
        self.assertFalse(match.armor_near(q))                 # só um veste

    def test_armadura_segura_oito_golpes_e_cai_aos_pedacos(self):
        reset_progress()
        match, _ = casa_da_turma()
        p = match.players[0]
        _junto_da_armadura(p)
        match.interact(p)
        hp = p.hp
        pieces = []
        for _ in range(UNO_HITS):
            p.invulnerable_timer = 0
            p.take_damage(30, match=match)
            pieces.append(uno_pieces(p.uno_hits))
        self.assertEqual(p.hp, hp)                               # nada passou
        self.assertEqual(pieces, [4, 3, 3, 2, 2, 1, 1, 0])
        p.take_damage(10, match=match)
        self.assertEqual(p.hp, hp - 10)

    def test_quem_veste_anda_mais_devagar(self):
        reset_progress()
        match, _ = casa_da_turma()
        p = match.players[0]
        before = p.max_speed
        p.uno_hits = UNO_HITS
        self.assertAlmostEqual(p.max_speed, before * UNO_SLOW)

    def test_armadura_so_vale_no_capitulo_1(self):
        reset_progress()
        match, _ = casa_da_turma()
        run = match.run
        p = match.players[0]
        _junto_da_armadura(p)
        match.interact(p)
        p.uno_hits = 5
        run.carry(match)
        self.assertEqual(run.armor, {p.slot: 5})
        run.prepare(p)
        self.assertEqual(p.uno_hits, 5)                          # passa para a fase
        run.phase_index = 3                                      # capítulo 2: ficou na floresta
        run.prepare(p)
        self.assertEqual(p.uno_hits, 0)
        run.carry(match)
        self.assertEqual(run.armor, {})

    def test_fora_do_capitulo_1_e_enfeite(self):
        reset_progress()
        match, _ = casa_da_turma()
        match.run.phase_index = 3
        again = casa.HubMatch(match.game, match.run, False)
        p = again.players[0]
        _junto_da_armadura(p)
        self.assertFalse(again.armor_near(p))


if __name__ == "__main__":
    unittest.main()
