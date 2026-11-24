"""Oficina do Borba Jr: a porta abre ao zerar o capítulo 2, o estande de tiro e o exo que desmonta."""
import unittest

from test_casa import _Input, casa_da_turma, passo, reset_progress

from soulstrike import segredos
from soulstrike.casa import OFICINA_DOOR, HubMatch, door_open
from soulstrike.oficina import (COUNT, DOOR, EXO_AT, EXO_POKES, EXO_WALK, LANES, MISS, RACK, RANGE_X, RUN,
                                OficinaMatch, gun_ready, lane_of, lane_rect, record)


def _na_oficina(chars=("guerreiro", "atirador")):
    match, _ = casa_da_turma(chars, walk=True)
    of = OficinaMatch(match.game, match.run, walk=True)
    inputs = {}
    for f in of.players:
        inputs[f.slot] = of.controllers[f] = _Input()
    return of, inputs


def _na_baia(p, k):
    r = lane_rect(k)
    p.x, p.y = RANGE_X - 40, r.centery


class OficinaTest(unittest.TestCase):
    def tearDown(self):
        reset_progress()

    def test_largada_livre(self):
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        of, _ = _na_oficina(("guerreiro", "atirador", "ninja", "tanque"))
        for f in of.players:
            self.assertTrue(of.arena.is_free(f.x, f.y, 12))
            self.assertIsNone(lane_of(f))

    def test_porta_abre_no_capitulo_2_e_ida_e_volta(self):
        reset_progress(capitulo1_zerado=True)
        self.assertFalse(door_open("oficina"))
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        match, _ = casa_da_turma(walk=True)
        p = match.players[0]
        p.x, p.y = OFICINA_DOOR
        self.assertEqual(match.room_near(p), "oficina")
        match.interact(p)
        while not match.finished:
            match.update()
        of = match.next_scene().then().match
        self.assertIsInstance(of, OficinaMatch)
        q = of.players[0]
        q.x, q.y = DOOR.center
        self.assertTrue(of.door_near(q))
        of.interact(q)
        while not of.finished:
            of.update()
        back = of.next_scene().then().match
        self.assertIsInstance(back, HubMatch)
        for f in back.players:
            self.assertLess(abs(f.x - OFICINA_DOOR[0]), 120)
            self.assertTrue(back.arena.is_free(f.x, f.y, 12))

    def test_ninguem_entra_no_estande(self):
        reset_progress(capitulo2_zerado=True)
        of, _ = _na_oficina()
        self.assertFalse(of.arena.is_free(RANGE_X + 100, lane_rect(1).centery, 12))
        _na_baia(of.players[0], 2)
        self.assertTrue(of.arena.is_free(of.players[0].x, of.players[0].y, 12))

    def test_desafio_de_30_s_conta_pontos_e_salva_recorde(self):
        reset_progress(capitulo2_zerado=True)
        of, inputs = _na_oficina()
        a, b = of.players[:2]
        _na_baia(a, 0)
        _na_baia(b, 1)
        self.assertEqual((lane_of(a), lane_of(b)), (0, 1))
        self.assertTrue(of.interact(a))
        ch = of.challenge
        self.assertEqual(set(ch.players), {a, b})
        passo(of, inputs, COUNT + 1)
        self.assertTrue(ch.running)
        t = ch.targets[0]
        t.up, t.age, t.life, t.timer, t.x = False, 0, 80, 50, RANGE_X + 200
        of.interact(a)                                   # alvo deitado: perde ponto (não fica negativo)
        self.assertEqual(ch.score[a], 0)
        passo(of, inputs, 60)
        t.up, t.age, t.life, t.timer = True, 5, 80, 60
        of.interact(a)
        self.assertGreater(ch.score[a], 300)             # rápido: NA MOSCA!
        self.assertFalse(t.up)
        got = ch.score[a]
        passo(of, inputs, RUN)
        self.assertEqual(ch.state, "end")
        rec = record()
        self.assertEqual(rec["pontos"], got)
        self.assertEqual(rec["slot"], a.slot)
        self.assertTrue(ch.new_record)
        passo(of, inputs, 300)
        self.assertIsNone(of.challenge)

    def test_suporte_so_troca_para_arma_liberada(self):
        reset_progress(capitulo1_zerado=True, capitulo2_zerado=True)
        of, _ = _na_oficina()
        p = of.players[0]
        p.x, p.y = RACK.centerx, RACK.bottom + 40
        self.assertTrue(of.rack_near(p))
        seen = set()
        for _ in range(10):
            of.interact(p)
            seen.add(of.gun_of(p))
        self.assertIn("revolver", seen)
        self.assertIn("rifle_plasma", seen)
        self.assertNotIn("besta", seen)
        self.assertFalse(gun_ready("besta", 3))

    def test_exo_anda_e_desmonta(self):
        reset_progress(capitulo2_zerado=True)
        of, inputs = _na_oficina()
        p = of.players[0]
        p.x, p.y = EXO_AT[0] + 30, EXO_AT[1] + 20
        for _ in range(EXO_POKES):
            self.assertTrue(of.interact(p))
            passo(of, inputs, 5)
        self.assertGreater(of.exo_walk, 0)
        passo(of, inputs, EXO_WALK + 2)
        self.assertTrue(of.exo_broken)
        self.assertTrue(segredos.is_found("parafuso"))


if __name__ == "__main__":
    unittest.main()
