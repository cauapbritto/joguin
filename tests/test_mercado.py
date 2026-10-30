"""Almas, mercado (loja e ferreiro) e encantos da campanha."""
import json
import unittest

from apoio import FakeInput, game
from test_campanha import campanha, inimigo, passo, pular_intro

from soulstrike import config
from soulstrike import market as M
from soulstrike.campaign import LOBBY_BACK, LOBBY_START, CampaignRun, LobbyMatch
from soulstrike.data import CHARACTERS
from soulstrike.session import Session, SlotSetup
from soulstrike.training import DummyAI

KEYS = [c.key for c in CHARACTERS]


def acampamento(back=True, souls=500):
    g = game()
    g.session = Session("campaign", [SlotSetup(1, char=KEYS.index("guerreiro")),
                                     SlotSetup(2, char=KEYS.index("atirador"))])
    run = CampaignRun(g.session)
    run.begin_phase()
    run.stage = LOBBY_BACK if back else LOBBY_START
    run.souls = {s: souls for s in run.slots}
    match = LobbyMatch(g, run)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = FakeInput()
    return match, inputs


def abrir(match, inp, kind):
    p = match.players[0]
    stall = next(s for s in match.stalls if s.kind == kind)
    p.x, p.y = stall.x, stall.y + 40
    inp.tap("attack")
    match.update()
    inp.end_frame()
    match.update()
    return p, match.menus[p]


def apertar(match, inp, action=None, stick=None):
    if action:
        inp.tap(action)
    if stick is not None:
        inp.stick = stick
    match.update()
    inp.end_frame()
    inp.stick = (0.0, 0.0)
    match.update()


class AlmasTest(unittest.TestCase):
    def test_inimigo_sem_dono_da_a_parte_de_todos(self):
        match, _ = campanha()
        pular_intro(match)
        e = inimigo(match, "esqueleto", 600, 600)
        g = inimigo(match, "golem", 800, 600)
        e.hp = g.hp = 0
        passo(match, 1)
        share = M.SHARE["comum"] + M.SHARE["elite"]
        self.assertEqual(set(match.run.souls.values()), {share})

    def test_golpe_final_leva_mais(self):
        match, _ = campanha()
        pular_intro(match)
        a, b = match.players[0], match.players[1]
        g = inimigo(match, "golem", 800, 600)
        g.take_damage(g.hp + 10, a.x, a.y, attacker=a, match=match)
        passo(match, 6)                                  # passa o congelamento do golpe
        self.assertEqual(match.run.souls[a.slot], M.SOULS["elite"])
        self.assertEqual(match.run.souls[b.slot], M.SHARE["elite"])

    def test_celular_mostra_o_saldo(self):
        from soulstrike.net.remote import hub
        match, _ = campanha()
        pular_intro(match)
        hub.set_phase("playing", mode="campaign")
        match.run.souls[2] = 37
        passo(match, 7)
        self.assertEqual(hub.status(2)["me"]["souls"], 37)
        hub.set_phase("menu", mode="battle")
        self.assertIsNone(hub.status(2)["me"]["souls"])          # fora da campanha não aparece

    def test_chefao_da_igual_para_todos(self):
        self.assertEqual(M.soul_split("chefe", 1, [1, 2]), {1: 60, 2: 60})
        self.assertEqual(M.soul_split("diabrete", 2, [1, 2, 3]), {1: 1, 2: 3, 3: 1})


class MercadoTest(unittest.TestCase):
    def test_so_aparece_na_volta(self):
        self.assertEqual([s.kind for s in acampamento(back=False)[0].stalls], ["altar"])
        self.assertEqual({s.kind for s in acampamento()[0].stalls}, {"loja", "ferreiro"})

    def test_pocao_cura_e_gasta_almas(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        p.hp = 20
        x = p.x
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.hp, 20 + p.max_hp // 2)
        self.assertEqual(match.run.souls, {1: 30, 2: 50})
        self.assertEqual(p.x, x)                         # parado no balcão

    def test_sem_almas_nao_compra(self):
        match, inputs = acampamento(souls=5)
        p, menu = abrir(match, inputs[1], "loja")
        p.hp = 20
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.hp, 20)
        self.assertEqual(match.run.souls[1], 5)

    def test_esquiva_fecha(self):
        match, inputs = acampamento()
        p, _ = abrir(match, inputs[1], "loja")
        apertar(match, inputs[1], "dodge")
        self.assertNotIn(p, match.menus)

    def test_arma_sorteada_e_continue_e_troca(self):
        match, inputs = acampamento(souls=1000)
        match.run.continues = 1
        p, menu = abrir(match, inputs[1], "loja")
        apertar(match, inputs[1], stick=(0.0, 1.0))       # arma sorteada
        apertar(match, inputs[1], "attack")
        self.assertEqual(len(match.ground), 1)
        apertar(match, inputs[1], stick=(0.0, 1.0))       # trocar melhorias
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.rerolls[1], 1)
        apertar(match, inputs[1], stick=(0.0, 1.0))       # continue
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.continues, 2)

    def test_ferreiro_sobe_ate_o_encanto(self):
        match, inputs = acampamento(souls=1000)
        p, menu = abrir(match, inputs[1], "ferreiro")
        arco = p.weapons[0]
        mag = p.mag_of(arco)
        apertar(match, inputs[1], "attack")
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.forge[arco.name], [2, None])
        self.assertAlmostEqual(p.weapon_mult(arco), 1.3)
        self.assertGreater(p.mag_of(arco), mag)
        labels = [e.label for e in menu.entries()]
        self.assertTrue(labels[0].endswith("FOGO") and labels[2].endswith("RAIO"))
        apertar(match, inputs[1], stick=(0.0, 1.0))       # gelo
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.forge[arco.name], [3, "gelo"])
        self.assertEqual(match.run.souls[1], 1000 - sum(M.FORGE_COST))
        self.assertIs(match.run.forge[1], p.forge)       # fica com a campanha

    def test_doar_passa_almas_para_o_companheiro(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        k = next(i for i, e in enumerate(menu.entries()) if e.label.startswith("DOAR"))
        for _ in range(k):
            apertar(match, inputs[1], stick=(0.0, 1.0))
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.souls, {1: 50 - M.GIFT, 2: 50 + M.GIFT})

    def test_save_antigo_divide_as_almas(self):
        match, _ = acampamento(souls=10)
        match.run.begin_phase()
        data = json.loads(json.dumps(match.run.to_save()))
        data["versao"] = 1
        data["estado"]["souls"] = 81
        back = CampaignRun.from_save(data)
        self.assertEqual(back.souls, {1: 40, 2: 40})

    def test_salva_almas_ferreiro_e_trocas(self):
        match, _ = acampamento(souls=77)
        match.run.forge[1]["Arco"] = [3, "raio"]
        match.run.rerolls[2] = 2
        match.run.begin_phase()
        back = CampaignRun.from_save(json.loads(json.dumps(match.run.to_save())))
        self.assertEqual(back.souls, {1: 77, 2: 77})
        self.assertEqual(back.forge[1], {"Arco": [3, "raio"]})
        self.assertEqual(back.rerolls[2], 2)
        data = json.loads(json.dumps(match.run.to_save()))
        data["estado"]["forge"]["1"]["Arco"] = [9, "raio"]
        self.assertIsNone(CampaignRun.from_save(data))


class EncantoTest(unittest.TestCase):
    def preparar(self, enchant):
        match, _ = campanha()
        pular_intro(match)
        p = match.players[0]
        p.forge["Espada"] = [3, enchant]
        p.weapon_index = 1
        p.x, p.y, p.facing = 500, 600, (1.0, 0.0)
        a = inimigo(match, "esqueleto", 540, 600)
        b = inimigo(match, "esqueleto", 640, 600)
        a.hp = b.hp = 999
        p.attack(match, a)
        return match, a, b

    def test_fogo_queima(self):
        match, a, _ = self.preparar("fogo")
        self.assertGreater(a.burn_timer, 0)
        hp = a.hp
        match.controllers[a] = DummyAI()                 # parado, mas atualizando
        passo(match, M.BURN_TICK + 1)
        self.assertLess(a.hp, hp)

    def test_gelo_deixa_lento(self):
        _, a, _ = self.preparar("gelo")
        self.assertGreater(a.slow_timer, 0)

    def test_raio_pula(self):
        _, a, b = self.preparar("raio")
        self.assertLess(b.hp, 999)


if __name__ == "__main__":
    unittest.main()


class LojaNoCelularTest(unittest.TestCase):
    def setUp(self):
        from soulstrike.net.remote import hub
        self.hub = hub
        hub.set_phase("playing", mode="campaign")
        hub.orders()

    def tearDown(self):
        self.hub.set_phase("menu", mode="battle")

    def esperar(self, match, n=4):
        for _ in range(n):
            match.update()

    def test_celular_ve_a_banca_aberta(self):
        match, inputs = acampamento(souls=50)
        self.assertIsNone(self.hub.status(1)["me"]["shop"])
        abrir(match, inputs[1], "loja")
        self.esperar(match)
        shop = self.hub.status(1)["me"]["shop"]
        self.assertEqual(shop["kind"], "loja")
        self.assertEqual(shop["souls"], 50)
        ids = [i["id"] for i in shop["items"]]
        self.assertEqual(ids[:4], ["pocao", "arma", "trocar", "continue"])
        self.assertIn("doar:2", ids)
        self.assertIsNone(self.hub.status(2)["me"]["shop"])      # o outro não abriu nada

    def test_so_compra_com_a_banca_aberta(self):
        match, _ = acampamento(souls=50)
        self.esperar(match)
        self.assertFalse(self.hub.order(1, "arma", True))         # longe da banca: o celular não compra
        self.esperar(match)
        self.assertEqual(match.run.souls[1], 50)

    def test_marcar_e_comprar_pelo_celular(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        self.esperar(match)
        self.assertTrue(self.hub.order(1, "doar:2", False))       # primeiro toque só marca
        self.esperar(match, 1)
        self.assertEqual(self.hub.status(1)["me"]["shop"]["picked"], "doar:2")
        self.assertEqual(match.run.souls, {1: 50, 2: 50})
        self.hub.order(1, "doar:2", True)                          # COMPRAR
        self.esperar(match, 1)
        self.assertEqual(match.run.souls, {1: 50 - M.GIFT, 2: 50 + M.GIFT})

    def test_ferreiro_pelo_id(self):
        match, inputs = acampamento(souls=500)
        p, menu = abrir(match, inputs[1], "ferreiro")
        self.esperar(match)
        w = p.weapons[0]
        self.hub.order(1, f"forja:{w.name}:1", True)
        self.esperar(match, 1)
        self.assertEqual(M.forge_of(p, w)[0], 1)
        self.hub.order(1, f"forja:{w.name}:1", True)               # pedido repetido não sobe de novo
        self.esperar(match, 1)
        self.assertEqual(M.forge_of(p, w)[0], 1)

    def test_fechar_pelo_celular(self):
        match, inputs = acampamento(souls=50)
        p, _ = abrir(match, inputs[1], "loja")
        self.esperar(match)
        self.hub.order(1, "fechar", False)
        self.esperar(match)
        self.assertNotIn(p, match.menus)
        self.assertIsNone(self.hub.status(1)["me"]["shop"])

    def test_rota_pede_o_dono_da_vaga(self):
        from soulstrike.net import server
        client = server.app.test_client()
        self.assertEqual(client.post("/api/shop", json={"slot": 3, "token": "x", "item": "pocao"}).status_code, 403)
        self.hub.join(3, "dono")
        try:
            r = client.post("/api/shop", json={"slot": 3, "token": "dono", "item": "pocao", "buy": True})
            self.assertEqual(r.status_code, 409)                   # nenhuma banca aberta
        finally:
            self.hub.leave(3, "dono")
