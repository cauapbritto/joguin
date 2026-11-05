"""v1.13.0: armário de armas do acampamento, energia finita da campanha e as cinco dificuldades."""
import unittest

from apoio import FakeInput, game

from soulstrike.armario import RACK_SIZE, token_of, weapon_of
from soulstrike.campaign import LOBBY_BACK, CampaignRun, LobbyMatch
from soulstrike.data import CHARACTERS, RARE_WEAPONS
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def corrida(chars=("guerreiro", "atirador"), phase=0, stage=0, difficulty="normal"):
    g = game()
    g.session = Session("campaign", [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)],
                        difficulty=difficulty)
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = stage
    return g, run


def acampamento(back=False, run=None):
    g, r = corrida(stage=LOBBY_BACK if back else 0)
    run = run or r
    match = LobbyMatch(g, run)
    for f in match.players:
        match.controllers[f] = FakeInput()
    return match


def perto(match, p, thing):
    p.x, p.y = thing.x, thing.y + 40


class ArmarioTest(unittest.TestCase):
    def test_tem_armario_nos_dois_acampamentos(self):
        for back in (False, True):
            self.assertIsNotNone(acampamento(back).armario)

    def test_guardar_e_pegar(self):
        match = acampamento()
        p, q = match.players
        match.give_relic(p, RARE_WEAPONS["besta"])
        perto(match, p, match.armario)
        self.assertTrue(match.interact(p))                      # ATACAR perto: guarda
        self.assertIsNone(p.relic)
        self.assertEqual(match.run.rack, ["rara:besta"])
        perto(match, q, match.armario)
        self.assertTrue(match.interact(q))                      # o amigo pega
        self.assertIs(q.relic, RARE_WEAPONS["besta"])
        self.assertEqual(match.run.rack, [])

    def test_largar_perto_guarda(self):
        match = acampamento()
        p = match.players[0]
        rifle = next(c for c in CHARACTERS if c.key == "atirador").weapons[0]
        match.give_common(p, rifle)
        perto(match, p, match.armario)
        n = len(match.ground)
        inp = match.controllers[p]
        inp.hold("drop")
        match.update()
        inp.release("drop")
        self.assertEqual(match.run.rack, [token_of(rifle)])
        self.assertEqual(len(match.ground), n)

    def test_trocar_com_o_armario(self):
        match = acampamento()
        p = match.players[0]
        match.run.rack = ["rara:canhao"]
        match.give_relic(p, RARE_WEAPONS["besta"])
        match.store_in_rack(p)                               # guarda a besta: fila canhão, besta
        match.take_from_rack(p)                              # pega o canhão
        self.assertIs(p.relic, RARE_WEAPONS["canhao"])
        self.assertEqual(match.run.rack, ["rara:besta"])
        match.take_from_rack(p)                              # pega a besta, o canhão volta para a fila
        self.assertIs(p.relic, RARE_WEAPONS["besta"])
        self.assertEqual(match.run.rack, ["rara:canhao"])

    def test_cheio(self):
        match = acampamento()
        p = match.players[0]
        match.run.rack = ["rara:canhao"] * RACK_SIZE
        match.give_relic(p, RARE_WEAPONS["besta"])
        self.assertFalse(match.store_in_rack(p))
        self.assertIs(p.relic, RARE_WEAPONS["besta"])

    def test_salvo_guarda_o_armario(self):
        _, run = corrida()
        run.rack = ["rara:besta", token_of(CHARACTERS[0].weapons[0])]
        run.begin_phase()
        loaded = CampaignRun.from_save(run.to_save())
        self.assertEqual(loaded.rack, run.rack)
        self.assertTrue(all(weapon_of(t) is not None for t in loaded.rack))


if __name__ == "__main__":
    unittest.main()
