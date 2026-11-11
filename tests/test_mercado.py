"""Almas, mercado (loja e ferreiro) e encantos da campanha."""
import json
import unittest

from apoio import FakeInput, game
from test_campanha import campanha, inimigo, passo, pular_intro

from soulstrike import config
from soulstrike import market as M
from soulstrike.campaign import CampaignRun
from soulstrike.fase import PhaseMatch
from soulstrike.data import CHARACTERS
from soulstrike.session import Session, SlotSetup
from soulstrike.training import DummyAI

KEYS = [c.key for c in CHARACTERS]


def acampamento(souls=500):
    """A fase: a lojinha e o altar na abertura, a loja completa e o ferreiro na sala de recompensas."""
    g = game()
    g.session = Session("campaign", [SlotSetup(1, char=KEYS.index("guerreiro")),
                                     SlotSetup(2, char=KEYS.index("atirador"))])
    run = CampaignRun(g.session)
    run.begin_phase()
    run.souls = {s: souls for s in run.slots}
    match = PhaseMatch(g, run)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = FakeInput()
    return match, inputs


def abrir(match, inp, kind):
    p = match.players[0]
    stall = next(s for s in match.stalls if s.kind == kind and not s.mini)
    p.x, p.y = stall.x, stall.y + 40
    inp.tap("attack")
    match.update()
    inp.end_frame()
    match.update()
    return p, match.menus[p]


def abrir_outro(match, inp):
    q = match.players[1]
    stall = next(s for s in match.stalls if s.kind == "loja" and not s.mini)
    q.x, q.y = stall.x + 30, stall.y + 40
    inp.tap("attack")
    match.update()
    inp.end_frame()
    match.update()
    return q, match.menus[q]


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
    def test_lojinha_na_abertura_e_loja_completa_na_recompensa(self):
        match = acampamento()[0]
        where = {(s.kind, s.mini): match.layout.room_at(s.x, s.y).key for s in match.stalls}
        self.assertEqual(where, {("loja", True): "abertura", ("altar", False): "abertura",
                                 ("loja", False): "recompensa", ("ferreiro", False): "recompensa"})

    def test_lojinha_vende_so_o_basico(self):
        from soulstrike.market import MarketMenu
        match, _ = acampamento()
        p = match.players[0]
        lojinha = next(s for s in match.stalls if s.kind == "loja" and s.mini)
        keys = [e.key for e in MarketMenu(match, p, lojinha).entries()]
        self.assertEqual(keys, ["pocao", "energia", "continue", "doar:2"])
        loja = next(s for s in match.stalls if s.kind == "loja" and not s.mini)
        full = [e.key for e in MarketMenu(match, match.players[0], loja).entries()]
        self.assertIn("arma", full)
        self.assertTrue(any(k.startswith("vitrine:") for k in full))

    def test_pocao_cura_e_gasta_almas(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        p.hp = 20
        x = p.x
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.hp, 20 + p.max_hp // 2)
        self.assertEqual(match.run.souls, {1: 30, 2: 50})
        self.assertEqual(p.x, x)                         # parado no balcão

    def test_energia_enche_metade_e_gasta_almas(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        p.energy = 30
        apertar(match, inputs[1], stick=(0.0, 1.0))       # desce da poção para a energia
        self.assertEqual(menu.entries()[menu.index].key, "energia")
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.energy, 30 + M.ENERGY_REFILL)
        self.assertEqual(match.run.souls, {1: 50 - M.ENERGY_COST, 2: 50})

    def test_energia_cheia_nao_vende(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        p.energy = p.energy_max
        menu.pick("energia")
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.souls[1], 50)
        item = next(i for i in menu.snapshot()["items"] if i["id"] == "energia")
        self.assertFalse(item["ok"])
        self.assertEqual(item["info"]["sub"], "ENERGIA CHEIA")

    def test_energia_nao_passa_do_maximo(self):
        match, inputs = acampamento(souls=50)
        p, menu = abrir(match, inputs[1], "loja")
        p.energy = p.energy_max - 10
        menu.pick("energia")
        apertar(match, inputs[1], "attack")
        self.assertEqual(p.energy, p.energy_max)

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
        menu.pick("arma")                                  # arma surpresa (depois da vitrine)
        apertar(match, inputs[1], "attack")
        self.assertEqual(len(match.ground), 1)
        apertar(match, inputs[1], stick=(0.0, 1.0))       # trocar melhorias
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.rerolls[1], 1)
        apertar(match, inputs[1], stick=(0.0, 1.0))       # continue
        apertar(match, inputs[1], "attack")
        self.assertEqual(match.run.continues, 2)

    def test_vitrine_tem_uma_de_tiro_e_uma_de_perto_de_outros_herois(self):
        match, inputs = acampamento(souls=1000)
        p, menu = abrir(match, inputs[1], "loja")
        stock = menu.stock()
        self.assertEqual([w.is_melee for w in stock], [False, True])
        held = {w.name for q in match.players for w in q.weapons}
        self.assertFalse(held & {w.name for w in stock})
        ids = [e.key for e in menu.entries()]
        self.assertEqual(ids[:5], ["pocao", "energia"] + [f"vitrine:{w.name}" for w in stock] + ["arma"])
        q, other = abrir_outro(match, inputs[2])
        self.assertEqual(other.stock(), stock)            # a vitrine é a mesma para o grupo

    def test_arma_da_vitrine_vai_para_a_mao(self):
        match, inputs = acampamento(souls=1000)
        p, menu = abrir(match, inputs[1], "loja")
        perto = menu.stock()[1]
        espada = p.base_weapons[1]
        menu.pick(f"vitrine:{perto.name}")
        apertar(match, inputs[1], "attack")
        self.assertIs(p.weapon, perto)
        self.assertNotIn(espada, p.weapons)
        self.assertEqual(match.ground, [])                # a espada do herói volta para a mochila
        self.assertEqual(match.run.souls[1], 1000 - M.VITRINE_COST)
        e = next(e for e in menu.entries() if e.key == f"vitrine:{perto.name}")
        self.assertFalse(e.ok)                            # vendida: ninguém compra de novo
        self.assertEqual(e.info["sub"], "VENDIDA")

    def test_largar_a_da_vitrine_nao_duplica_arma(self):
        match, inputs = acampamento(souls=1000)
        p, menu = abrir(match, inputs[1], "loja")
        perto = menu.stock()[1]
        espada = p.base_weapons[1]
        menu.pick(f"vitrine:{perto.name}")
        apertar(match, inputs[1], "attack")
        apertar(match, inputs[1], "dodge")                # fecha a loja
        p.weapon_index = p.base_weapons.index(perto)
        apertar(match, inputs[1], "drop")
        self.assertIs(p.base_weapons[1], espada)          # a espada voltou para a mão
        self.assertEqual([g.weapon for g in match.ground], [perto])    # e só a outra ficou no chão

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
        self.assertEqual(ids[:2], ["pocao", "energia"])
        self.assertEqual(ids[4:7], ["arma", "trocar", "continue"])
        vitrine = shop["items"][2]["info"]
        self.assertTrue(vitrine["weapon"]["icon"].endswith(".png"))      # a imagem da arma
        self.assertEqual(vitrine["out"]["name"], "ARCO")                 # o guerreiro troca o arco
        self.assertEqual(vitrine["weapon"]["energy"], 1)                 # arma de tiro de outro: 1 por tiro
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

    def test_ferreiro_mostra_no_que_a_arma_vira(self):
        match, inputs = acampamento(souls=500)
        p, menu = abrir(match, inputs[1], "ferreiro")
        p.forge["Espada"] = [2, None]
        self.esperar(match)
        items = {i["id"]: i for i in self.hub.status(1)["me"]["shop"]["items"]}
        arco = items["forja:Arco:1"]["info"]
        self.assertEqual(arco["weapon"]["icon"], "arco.png")
        self.assertEqual((arco["weapon"]["level"], arco["next"]["level"]), (0, 1))
        self.assertEqual((arco["weapon"]["damage"], arco["next"]["damage"]), (10, 12))
        self.assertGreater(arco["next"]["mag"], arco["weapon"]["mag"])
        fogo = items["encanto:Espada:fogo"]["info"]
        self.assertEqual((fogo["group"], fogo["next"]["level"], fogo["next"]["enchant"]), ("Espada", 3, "FOGO"))
        self.assertEqual(fogo["next"]["damage"], round(22 * 1.45))

    def test_fusao_mostra_a_forjada_ou_a_silhueta(self):
        from soulstrike.data import RARE_WEAPONS
        from unittest import mock
        match, inputs = acampamento(souls=500)
        p, menu = abrir(match, inputs[1], "ferreiro")
        match.give_relic(p, RARE_WEAPONS["besta"])
        with mock.patch("soulstrike.forged.discovered", return_value=set()):
            info = next(e for e in menu.entries() if e.key == "fundir").info
        self.assertEqual([c["name"] for c in info["inputs"]], ["ARCO", "ESPADA", "BESTA"])
        self.assertFalse(info["known"])
        self.assertEqual(info["next"]["name"], "???")
        self.assertEqual(info["next"]["icon"], "arco_das_mil_almas.png")  # o celular mostra a silhueta
        self.assertEqual(info["family"], "FLECHA")
        with mock.patch("soulstrike.forged.discovered", return_value={"arco_mil_almas"}):
            info = next(e for e in menu.entries() if e.key == "fundir").info
        self.assertEqual(info["next"]["name"], "ARCO DAS MIL ALMAS")

    def test_rota_da_imagem_da_arma(self):
        from soulstrike.net import server
        client = server.app.test_client()
        r = client.get("/arma/katana.png")
        self.assertEqual((r.status_code, r.mimetype), (200, "image/png"))
        r.close()
        self.assertEqual(client.get("/arma/grips.json").status_code, 404)
        self.assertEqual(client.get("/arma/..%2Fconfig.py").status_code, 404)

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
