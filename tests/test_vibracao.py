"""Vibração por evento no celular: o jogo manda [contador, padrão] no status e o celular vibra
quando o contador muda (no máximo uma a cada 250 ms, menos os avisos urgentes)."""
import unittest
from unittest import mock

from apoio import FakeInput, game

from soulstrike import rumble, settings
from soulstrike.campaign import CALL_EVERY, PASSAGE_FRAMES, LobbyMatch, CampaignRun
from soulstrike.data import CHARACTERS
from soulstrike.net import remote
from soulstrike.net.remote import hub
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


class _Input(FakeInput):
    def set_layout(self, name):
        pass


class Celular:
    """Um celular conectado na vaga (sai no fim do teste)."""

    def __init__(self, slot):
        self.slot, self.token = slot, f"vibra{slot}"

    def __enter__(self):
        hub.join(self.slot, self.token)
        hub._slots[self.slot].buzz_at = -1.0       # o limite de 250 ms começa limpo em cada teste
        return self

    def __exit__(self, *exc):
        hub.leave(self.slot, self.token)

    @property
    def buzz(self):
        return hub.status(self.slot, self.token)["me"]["buzz"]


class HubTest(unittest.TestCase):
    def test_contador_e_padrao(self):
        with Celular(3) as cel:
            n = cel.buzz[0]
            self.assertTrue(hub.buzz(3, "hit"))
            self.assertEqual(cel.buzz, [n + 1, "hit"])

    def test_no_maximo_uma_a_cada_250_ms(self):
        base = remote.time.monotonic() + 10
        with Celular(3) as cel, mock.patch.object(remote.time, "monotonic") as clock:
            clock.return_value = base
            hub.join(3, cel.token)
            n = cel.buzz[0]
            self.assertTrue(hub.buzz(3, "hit"))
            clock.return_value = base + 0.1
            self.assertFalse(hub.buzz(3, "hit"))               # cedo demais: ignora
            self.assertTrue(hub.buzz(3, "go", force=True))    # o aviso urgente passa
            clock.return_value = base + 0.4
            self.assertTrue(hub.buzz(3, "hit"))
            self.assertEqual(cel.buzz, [n + 3, "hit"])

    def test_sem_celular_nao_vibra(self):
        self.assertFalse(hub.buzz(4, "hit"))


class RumbleTest(unittest.TestCase):
    def setUp(self):
        game()                                   # registra os controles (nenhum aqui)

    def test_apanhar_vibra_o_celular(self):
        with Celular(2) as cel:
            n = cel.buzz[0]
            self.assertTrue(rumble.buzz(2, rumble.BIG_HIT))
            self.assertEqual(cel.buzz, [n + 1, "big_hit"])

    def test_opcao_desligada_nao_vibra(self):
        with Celular(2) as cel, mock.patch.object(settings, "get", return_value=False):
            n = cel.buzz[0]
            self.assertFalse(rumble.buzz(2, rumble.HIT))
            self.assertEqual(cel.buzz[0], n)

    def test_todo_padrao_tem_nome_para_o_celular(self):
        for kind in (rumble.HIT, rumble.BIG_HIT, rumble.SCORE, rumble.SUPER, rumble.CALL, rumble.TICK, rumble.GO):
            self.assertIn(kind, rumble.PHONE)
        self.assertEqual(len(set(rumble.PHONE.values())), len(rumble.PHONE))


class PassagemTest(unittest.TestCase):
    def _sala(self):
        g = game()
        g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c))
                                         for i, c in enumerate(("guerreiro", "atirador", "ninja"))])
        run = CampaignRun(g.session)
        run.begin_phase()
        match = LobbyMatch(g, run)
        inputs = {}
        for f in match.players:
            inputs[f.slot] = match.controllers[f] = _Input()
        for _ in range(5):
            match.update()
        return match

    def _porta(self, match, who):
        area = match._gate_area()
        for k, p in enumerate(who):
            p.x, p.y = area.centerx - 30 + 40 * (k % 2), area.bottom - 60 + 30 * (k // 2)

    def test_quem_falta_na_porta_e_convocado(self):
        with Celular(3) as cel:
            match = self._sala()
            p1, p2, p3 = match.players
            self._porta(match, (p1, p2))
            p3.x, p3.y = p3.x + 260, p3.y + 120
            n = cel.buzz[0]
            for _ in range(CALL_EVERY + 1):
                match.update()
            self.assertEqual(cel.buzz, [n + 1, "call"])

    def test_contagem_e_ida_vibram(self):
        with Celular(3) as cel:
            match = self._sala()
            self._porta(match, match.players)
            n = cel.buzz[0]
            match.update()
            self.assertEqual(cel.buzz, [n + 1, "tick"])
            for _ in range(PASSAGE_FRAMES + 2):
                match.update()
            self.assertTrue(match.leaving)
            self.assertEqual(cel.buzz[1], "go")


if __name__ == "__main__":
    unittest.main()
