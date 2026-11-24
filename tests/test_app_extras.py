"""Lado do jogo das novidades do app (v1.60.0): apelido na TV, reações rápidas, resumo da partida,
MAPA e Caderno de Segredos no celular."""
import json
import time
import unittest
from types import SimpleNamespace

import pygame

from apoio import game

from soulstrike import config, reacoes, resumo
from soulstrike.campaign import CampaignRun
from soulstrike.casa import HubMatch
from soulstrike.data import CHARACTERS
from soulstrike.fase import PhaseMatch
from soulstrike.net import rapido, server
from soulstrike.net.remote import NICK_CHARS, NICK_LETTERS, REACTION_GAP, REACTIONS, clean_nick, hub
from soulstrike.session import Session, SlotSetup

TOKEN = "app-extras"
SLOT = 4


def _claim(slot=SLOT, token=TOKEN):
    hub._slots[slot].token = None                      # vaga limpa, mesmo que outro teste tenha usado
    hub._slots[slot].nick = hub._slots[slot].reaction = None
    assert hub.join(slot, token)


def _free(slot=SLOT, token=TOKEN):
    hub.leave(slot, token)
    hub.set_phase("menu", mode="battle")
    hub.set_map(None)
    hub.reactions()


class ApelidoTest(unittest.TestCase):
    def setUp(self):
        _claim()
        self.client = server.app.test_client()

    def tearDown(self):
        _free()

    def test_limpa_o_apelido(self):
        self.assertEqual(clean_nick("cauã"), "CAUÃ")
        self.assertEqual(clean_nick("  joão   pedro  "), "JOÃO PEDRO")
        self.assertEqual(clean_nick("😀 borba 🔥"), "BORBA")                  # emoji some
        self.assertEqual(len(clean_nick("x" * 40)), NICK_CHARS)
        self.assertIsNone(clean_nick("   "))
        self.assertIsNone(clean_nick("😀😀"))
        self.assertIsNone(clean_nick(None))
        self.assertIsNone(clean_nick(12))
        self.assertTrue(set(clean_nick("ação! é? ü-ç.")) <= NICK_LETTERS)

    def test_api_nick_e_status(self):
        r = self.client.post("/api/nick", json={"slot": SLOT, "token": TOKEN, "nick": "Cauã"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(hub.nick(SLOT), "CAUÃ")
        self.assertEqual(hub.status(SLOT, TOKEN)["me"]["nick"], "CAUÃ")
        r = self.client.post("/api/nick", json={"slot": SLOT, "token": "outro", "nick": "INTRUSO"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(hub.nick(SLOT), "CAUÃ")
        self.client.post("/api/nick", json={"slot": SLOT, "token": TOKEN, "nick": ""})
        self.assertIsNone(hub.nick(SLOT))                                    # vazio volta ao P4

    def test_apelido_sai_com_o_celular(self):
        hub.set_nick(SLOT, TOKEN, "ARYEL")
        self.assertTrue(hub.join(SLOT, TOKEN))                               # o mesmo celular volta: fica
        self.assertEqual(hub.nick(SLOT), "ARYEL")
        hub.leave(SLOT, TOKEN)
        self.assertIsNone(hub.nick(SLOT))
        _claim()
        hub.set_nick(SLOT, TOKEN, "ARYEL")
        hub._slots[SLOT].token = None                                         # vaga liberada pelo tempo
        self.assertTrue(hub.join(SLOT, "outro-celular"))
        self.assertIsNone(hub.nick(SLOT))                                    # outro celular: sem o apelido
        hub.leave(SLOT, "outro-celular")
        _claim()

    def test_etiqueta_do_boneco(self):
        hub.set_nick(SLOT, TOKEN, "CAUÃ")
        human = SimpleNamespace(is_cpu=False, slot=SLOT, label=f"P{SLOT}")
        cpu = SimpleNamespace(is_cpu=True, slot=SLOT, label="CPU")
        from soulstrike.fighter import Fighter
        self.assertEqual(Fighter.tag_text(human), "CAUÃ")
        self.assertEqual(Fighter.tag_text(cpu), "CPU")
        hub.set_nick(SLOT, TOKEN, None)
        self.assertEqual(Fighter.tag_text(human), f"P{SLOT}")

    def test_numero_do_status_muda_com_o_apelido(self):
        n = rapido.status_number(hub.status(SLOT, TOKEN))
        hub.set_nick(SLOT, TOKEN, "NOVO")
        self.assertNotEqual(rapido.status_number(hub.status(SLOT, TOKEN)), n)   # o app busca o status


class ReacoesTest(unittest.TestCase):
    def setUp(self):
        _claim()
        hub.reactions()
        self.client = server.app.test_client()

    def tearDown(self):
        _free()

    def test_uma_por_segundo(self):
        self.assertTrue(hub.react(SLOT, TOKEN, 0))
        self.assertIsNone(hub.react(SLOT, TOKEN, 1))                         # cedo demais
        self.assertFalse(hub.react(SLOT, "outro", 1))                        # token errado
        self.assertEqual(hub.reactions(), [(SLOT, 0)])
        self.assertEqual(hub.reactions(), [])                                # a fila esvazia
        kind, age = hub.reaction(SLOT)
        self.assertEqual(kind, 0)
        self.assertLess(age, 1.0)
        hub._slots[SLOT].reaction = (0, time.monotonic() - REACTION_GAP - 0.01)
        self.assertTrue(hub.react(SLOT, TOKEN, 3))
        self.assertEqual(hub.reaction(SLOT)[0], 3)
        hub._slots[SLOT].reaction = (3, time.monotonic() - 10)
        self.assertIsNone(hub.reaction(SLOT))                                # o balão já sumiu

    def test_tipo_invalido(self):
        for kind in (-1, len(REACTIONS), "x", None, True, 1.5):
            self.assertIsNone(hub.react(SLOT, TOKEN, kind), kind)
        self.assertEqual(hub.reactions(), [])

    def test_api_reacao(self):
        r = self.client.post("/api/reacao", json={"slot": SLOT, "token": TOKEN, "kind": "kkk"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(hub.reaction(SLOT)[0], REACTIONS.index("kkk"))
        r = self.client.post("/api/reacao", json={"slot": SLOT, "token": TOKEN, "kind": 0})
        self.assertEqual(r.status_code, 429)
        r = self.client.post("/api/reacao", json={"slot": SLOT, "token": "outro", "kind": 0})
        self.assertEqual(r.status_code, 403)
        r = self.client.post("/api/reacao", data="nao e json", content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_balao_desenha_em_qualquer_ponto(self):
        g = game()
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        for kind in range(len(REACTIONS)):
            for age in (0.0, 0.05, 0.5, 1.7, 5.0):
                for x, y in ((0, 0), (config.SCREEN_W, 40), (config.SCREEN_W // 2, config.SCREEN_H)):
                    reacoes.draw(screen, g.ui, kind, age, x, y)
            reacoes.play(g.assets, kind)
        reacoes.draw(screen, g.ui, 99, 0.5, 100, 100)                        # tipo que não existe: nada
        reacoes.play(g.assets, 99)

    def test_icones_do_tamanho_do_app(self):
        for key in REACTIONS:
            rows = reacoes.ICONS[key]
            self.assertLessEqual(len(rows), 16)
            self.assertTrue(all(len(r) == len(rows[0]) <= 16 for r in rows), key)
            self.assertTrue(set("".join(rows)) <= set(reacoes.PALETTE) | {"."}, key)
            self.assertIn(key, reacoes.STYLE)

    def test_boneco_mostra_apelido_e_balao(self):
        g = game()
        g.session = Session("duel", [SlotSetup(SLOT, char=0), SlotSetup(1, char=1, cpu=True)])
        from soulstrike.matches import BattleMatch
        match = BattleMatch(g, g.session)
        me = next(f for f in match.fighters if f.slot == SLOT)
        hub.set_nick(SLOT, TOKEN, "CAUÃ")
        self.assertTrue(hub.react(SLOT, TOKEN, 2))
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        match.draw(screen, g.ui)
        me.hp = 0                                                            # caído também reage
        match.draw(screen, g.ui)

    def test_resultado_mostra_os_baloes(self):
        """Na tela de resultado, quem reage e não está no pódio aparece no alto (sem quebrar)."""
        from soulstrike.matches import Result
        from soulstrike.scenes.play import ResultsScene
        g = game()
        g.session = Session("duel", [SlotSetup(1), SlotSetup(SLOT)])
        try:
            cena = ResultsScene(g, Result("P1 VENCEU", (255, 255, 255), []))
            g.change(cena)
            self.assertTrue(hub.react(SLOT, TOKEN, REACTIONS.index("palmas")))
            screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
            cena.draw(screen)
            self.assertIsNotNone(hub.reaction(SLOT))
        finally:
            g.session = None


class ResumoTest(unittest.TestCase):
    def tearDown(self):
        hub.set_phase("menu", mode="battle")

    @staticmethod
    def _fighter(slot, name, cpu=False, **nums):
        f = SimpleNamespace(slot=slot, is_cpu=cpu, team=None, stats=SimpleNamespace(name=name),
                            goals=0, damage_dealt=0, hits=0, kills=0, points=0, dunks=0, blocks=0, steals=0)
        for k, v in nums.items():
            setattr(f, k, v)
        return f

    def test_futebol(self):
        a = self._fighter(1, "Guerreiro", goals=3, damage_dealt=40)
        b = self._fighter(2, "Atirador", cpu=True, goals=1)
        result = SimpleNamespace(title="P1 VENCEU", color=(10, 200, 30), winners=[a], lines=[("PLACAR", "3 x 1")],
                                 score=(3, 1))
        data = resumo.of_match(SimpleNamespace(fighters=[a, b]), result, SimpleNamespace(mode="soccer1"),
                               ["mais_gols"])
        self.assertEqual(data["score"], "3 x 1")
        self.assertEqual(data["color"], "#0ac81e")
        self.assertEqual(list(data["players"]), ["1"])                     # a CPU não tem celular
        self.assertEqual(data["players"]["1"]["lines"], [["GOLS", "3"]])
        self.assertTrue(data["players"]["1"]["won"])
        self.assertEqual(data["mvp"]["slot"], 1)
        self.assertEqual(data["mvp"]["hero"], "GUERREIRO")
        self.assertTrue(data["records"])
        json.dumps(data)

    def test_basquete_e_apelido(self):
        _claim()
        try:
            hub.set_nick(SLOT, TOKEN, "CAUÃ")
            a = self._fighter(SLOT, "Ninja", points=12, blocks=2, steals=0, dunks=1)
            b = self._fighter(1, "Tanque", points=14)
            result = SimpleNamespace(title="TIME B VENCEU", color=(1, 2, 3), winners=[b], lines=[], score=None)
            data = resumo.of_match(SimpleNamespace(fighters=[a, b]), result, SimpleNamespace(mode="basket2"))
            me = data["players"][str(SLOT)]
            self.assertEqual(me["label"], "CAUÃ")
            self.assertIn(["PONTOS", "12"], me["lines"])
            self.assertIn(["TOCOS", "2"], me["lines"])
            self.assertNotIn(["ROUBOS", "0"], me["lines"])                   # zero não aparece
            self.assertFalse(me["won"])
            self.assertEqual(data["mvp"]["slot"], SLOT)                     # 12 + 2 x 2 de defesa > 14
            self.assertIsNone(data["score"])
        finally:
            _free()

    def test_ninguem_fez_nada_sem_destaque(self):
        a = self._fighter(1, "Guerreiro")
        result = SimpleNamespace(title="EMPATE", color=(1, 2, 3), winners=[], lines=[], score=None)
        data = resumo.of_match(SimpleNamespace(fighters=[a]), result, SimpleNamespace(mode="duel"))
        self.assertIsNone(data["mvp"])
        self.assertIsNone(data["players"]["1"]["won"])

    def test_campanha(self):
        run = SimpleNamespace(frames=config.FPS * 125, slots=[1, 2], kills={1: 4, 2: 9}, damage={1: 300, 2: 100},
                              souls={1: 55})
        data = resumo.of_run(run, "FIM DE JOGO", (200, 0, 0), won=False)
        self.assertEqual(data["lines"], [["TEMPO", "2:05"]])
        self.assertEqual(data["players"]["2"]["lines"][0], ["ABATES", "9"])
        self.assertEqual(data["players"]["2"]["lines"][2], ["ALMAS NA CARTEIRA", "0"])
        self.assertEqual(data["mvp"]["slot"], 2)
        json.dumps(data)

    def test_status_so_na_tela_de_resultado(self):
        _claim()
        try:
            hub.set_phase("results", mode="battle", active=[SLOT])
            hub.set_summary({"title": "X"})
            self.assertEqual(hub.status(SLOT, TOKEN)["summary"], {"title": "X"})
            hub.set_phase("menu", mode="battle")
            self.assertIsNone(hub.status(SLOT, TOKEN)["summary"])
            hub.set_phase("results", mode="battle")
            self.assertIsNone(hub.status(SLOT, TOKEN)["summary"])          # o resumo velho não volta
        finally:
            _free()


class MapaTest(unittest.TestCase):
    def setUp(self):
        _claim()
        self.client = server.app.test_client()

    def tearDown(self):
        _free()

    def _check(self, data):
        raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertLess(len(raw), 8000)
        self.assertTrue(data["title"])
        for b in data["boxes"]:
            self.assertGreaterEqual(b["x"], -0.01)
            self.assertGreaterEqual(b["y"], -0.01)
            self.assertLessEqual(b["x"] + b["w"], data["w"] + 0.01)
            self.assertLessEqual(b["y"] + b["h"], data["h"] + 0.01)
        for p in data["players"]:
            self.assertTrue(0 <= p["x"] <= data["w"] and 0 <= p["y"] <= data["h"], p)
            self.assertTrue(p["color"].startswith("#"))
        for m in data["marks"]:
            self.assertIn(m["kind"], ("dot", "door", "portal"))
            self.assertTrue(m["label"])

    def test_mapa_da_fase(self):
        g = game()
        keys = [c.key for c in CHARACTERS]
        g.session = Session("campaign", [SlotSetup(1, char=keys.index("guerreiro")),
                                         SlotSetup(SLOT, char=keys.index("atirador"))])
        run = CampaignRun(g.session)
        run.begin_phase()
        match = PhaseMatch(g, run)
        data = match.phone_map()
        self._check(data)
        self.assertEqual(len(data["players"]), 2)
        here = [b for b in data["boxes"] if b["label"] == "ABERTURA"]
        self.assertEqual(len(here), 1)
        self.assertEqual(sum(1 for b in data["boxes"] if b["mark"] == "?"), 4)   # as outras 4 salas
        labels = {m["label"] for m in data["marks"]}
        self.assertIn("LOJINHA", labels)
        self.assertNotIn("FERREIRO", labels)                                  # sala de recompensas não vista

    def test_mapa_da_casa(self):
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0), SlotSetup(SLOT, char=1)])
        match = HubMatch(g, CampaignRun(g.session))
        data = match.phone_map()
        self._check(data)
        labels = {m["label"] for m in data["marks"]}
        self.assertIn("GARAGEM", labels)
        self.assertIn("COMPUTADOR", labels)

    def test_api_mapa(self):
        self.assertFalse(hub.status(SLOT, TOKEN)["map"])
        hub.set_map({"title": "T", "w": 1, "h": 1, "boxes": [], "marks": [], "players": []})
        self.assertFalse(hub.status(SLOT, TOKEN)["map"])                     # no menu não tem mapa
        hub.set_phase("playing", mode="campaign", active=[SLOT])
        self.assertTrue(hub.status(SLOT, TOKEN)["map"])
        r = self.client.get(f"/api/mapa?slot={SLOT}&token={TOKEN}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["map"]["title"], "T")
        self.assertEqual(self.client.get(f"/api/mapa?slot={SLOT}&token=outro").status_code, 403)
        hub.set_map(None)
        self.assertIsNone(self.client.get(f"/api/mapa?slot={SLOT}&token={TOKEN}").get_json()["map"])

    def test_api_caderno(self):
        r = self.client.get(f"/api/caderno?slot={SLOT}&token={TOKEN}")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertGreater(data["total"], 0)
        self.assertEqual(sum(len(p["items"]) for p in data["pages"]), data["total"])
        self.assertTrue(all(p["place"] for p in data["pages"]))
        self.assertEqual(self.client.get(f"/api/caderno?slot={SLOT}&token=outro").status_code, 403)

    def test_partida_publica_o_mapa(self):
        """A PlayScene da fase publica o mapa; trocar de cena apaga."""
        from soulstrike.scenes.play import MAP_EVERY, PlayScene
        g = game()
        keys = [c.key for c in CHARACTERS]
        g.session = Session("campaign", [SlotSetup(1, char=keys.index("guerreiro"))])
        run = CampaignRun(g.session)
        run.begin_phase()
        scene = PlayScene(g, PhaseMatch(g, run))
        g.change(scene)
        hub.set_map(None)
        for _ in range(MAP_EVERY + 1):
            scene.update()
        self.assertIsNotNone(hub._map)
        self.assertEqual(hub._map["title"], run.phase.name)


if __name__ == "__main__":
    unittest.main()
