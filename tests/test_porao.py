"""Porão da Casa: abre ao zerar a campanha, a IARA no Cristal, o versículo no escuro e a Arena sem Fim."""
import unittest

from test_casa import _Input, casa_da_turma, passo, reset_progress

from soulstrike import arena_sem_fim, segredos
from soulstrike.arena_sem_fim import ArenaSemFimMatch, wave
from soulstrike.casa import PORAO_DOOR, HubMatch, door_open
from soulstrike.porao import (CRYSTAL, GATE_SPOT, STAIRS_SPOT, STILL_FRAMES, IaraMenu, PoraoMatch, iara_lines)


def _no_porao(chars=("guerreiro", "atirador"), arrive=None):
    match, _ = casa_da_turma(chars, walk=True)
    po = PoraoMatch(match.game, match.run, walk=True, arrive=arrive)
    inputs = {}
    for f in po.players:
        inputs[f.slot] = po.controllers[f] = _Input()
    return po, inputs


class PoraoTest(unittest.TestCase):
    def tearDown(self):
        reset_progress()

    def test_largada_livre_e_volta_da_arena(self):
        reset_progress(vezes_zerada=1)
        for arrive in (None, "arena"):
            po, _ = _no_porao(("guerreiro", "atirador", "ninja", "tanque"), arrive)
            for f in po.players:
                self.assertTrue(po.arena.is_free(f.x, f.y, 12), arrive)

    def test_desce_do_quintal_e_sobe_de_volta(self):
        reset_progress()
        self.assertFalse(door_open("porao"))
        reset_progress(vezes_zerada=1)
        match, _ = casa_da_turma(walk=True)
        p = match.players[0]
        p.x, p.y = PORAO_DOOR
        self.assertEqual(match.room_near(p), "porao")
        match.interact(p)
        while not match.finished:
            match.update()
        po = match.next_scene().then().match
        self.assertIsInstance(po, PoraoMatch)
        q = po.players[0]
        q.x, q.y = STAIRS_SPOT.center
        self.assertTrue(po.stairs_near(q))
        po.interact(q)
        while not po.finished:
            po.update()
        back = po.next_scene().then().match
        self.assertIsInstance(back, HubMatch)
        for f in back.players:
            self.assertTrue(back.arena.is_free(f.x, f.y, 12))
            self.assertLess(abs(f.x - PORAO_DOOR[0]), 120)

    def test_iara_fala_diferente_a_cada_vez_zerada(self):
        um, dois, tres = iara_lines(1), iara_lines(2), iara_lines(5)
        self.assertNotEqual(um, dois)
        self.assertNotEqual(dois, tres)
        self.assertTrue(any("5 VEZES" in line for line in tres))
        reset_progress(vezes_zerada=2)
        po, inputs = _no_porao()
        p = po.players[0]
        p.x, p.y = CRYSTAL[0], CRYSTAL[1] + 30
        self.assertTrue(po.interact(p))
        menu = po.menus[p]
        self.assertIsInstance(menu, IaraMenu)
        self.assertEqual(menu.lines, iara_lines(2))

    def test_versiculo_aparece_parado_no_escuro(self):
        reset_progress(vezes_zerada=1)
        po, inputs = _no_porao(("guerreiro",))
        p = po.players[0]
        p.x, p.y = 470, 610                             # embaixo, longe das velas e do Cristal
        self.assertTrue(po.in_dark(p))
        passo(po, inputs, STILL_FRAMES + 5)
        self.assertTrue(po.verse_found)
        self.assertTrue(segredos.is_found("lampada"))

    def test_perto_da_vela_nao_conta(self):
        reset_progress(vezes_zerada=1)
        po, inputs = _no_porao(("guerreiro",))
        p = po.players[0]
        p.x, p.y = CRYSTAL[0] + 60, CRYSTAL[1] + 20
        self.assertFalse(po.in_dark(p))
        passo(po, inputs, STILL_FRAMES + 5)
        self.assertFalse(po.verse_found)


class ArenaSemFimTest(unittest.TestCase):
    def tearDown(self):
        reset_progress()

    def test_ondas_crescem_e_nao_acabam(self):
        self.assertGreater(sum(c for _, c in wave(30)), sum(c for _, c in wave(0)))
        self.assertTrue(any(k in ("golem", "miliciano_exo") for k, _ in wave(4)))

    def test_portao_leva_para_a_arena_e_tudo_volta_como_estava(self):
        reset_progress(vezes_zerada=1)
        po, _ = _no_porao()
        p = po.players[0]
        p.x, p.y = GATE_SPOT.center
        self.assertTrue(po.gate_near(p))
        po.interact(p)
        while not po.finished:
            po.update()
        arena = po.next_scene().then().match
        self.assertIsInstance(arena, ArenaSemFimMatch)
        run = arena.run
        souls = dict(run.souls)
        continues = arena._saved["continues"]
        self.assertEqual(run.continues, 0)
        arena.start_battle() if arena.state == "ready" else None
        arena._start_wave(0)
        arena._start_wave(1)
        arena._start_wave(2)
        self.assertGreater(len(arena.waves), 3)          # sempre tem a próxima
        for s in run.souls:
            run.souls[s] += 500
        back = arena.next_scene().then().match
        self.assertIsInstance(back, PoraoMatch)
        self.assertEqual(run.souls, souls)
        self.assertEqual(run.continues, continues)

    def test_recorde_so_sobe(self):
        reset_progress()
        self.assertTrue(arena_sem_fim.save_record(7, ["ARYEL"]))
        self.assertFalse(arena_sem_fim.save_record(5, ["BORBA"]))
        self.assertEqual(arena_sem_fim.record()["onda"], 7)


if __name__ == "__main__":
    unittest.main()
