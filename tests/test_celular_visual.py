"""Remaster do celular: a fonte só em tamanhos nítidos, os ícones que o HTML pede existem,
quem atende cada banca tem desenho e falinha, e o botão ATACAR recebe a arma da mão."""
import re
import unittest
from pathlib import Path

from soulstrike import market, pecas
from soulstrike.net import remote, server

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "web" / "static" / "controller.css").read_text(encoding="utf-8")
JS = (ROOT / "web" / "static" / "controller.js").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "templates" / "controller.html").read_text(encoding="utf-8")


class FonteNitida(unittest.TestCase):
    def test_css_so_usa_8_16_24(self):
        # a Press Start 2P borra fora dos múltiplos de 8
        sizes = set(re.findall(r"font-size:\s*([^;}\s]+)", CSS))
        self.assertTrue(sizes <= {"0", "8px", "16px", "24px"}, sizes)

    def test_js_so_usa_8_16_24(self):
        sizes = set(re.findall(r"fontSize\s*=\s*[\"'](\d+)px", JS))
        self.assertTrue(sizes <= {"8", "16", "24"}, sizes)


class Icones(unittest.TestCase):
    def test_icones_pedidos_existem(self):
        pedidos = set(re.findall(r"/static/ic/([\w-]+\.png)", HTML + JS + CSS))
        self.assertTrue(pedidos)
        for nome in pedidos:
            self.assertTrue((ROOT / "web" / "static" / "ic" / nome).exists(), nome)

    def test_icones_16x16(self):
        from PIL import Image
        for p in (ROOT / "web" / "static" / "ic").glob("i_*.png"):
            with Image.open(p) as im:
                self.assertEqual(im.size, (16, 16), p.name)


class Vendedor(unittest.TestCase):
    def test_todo_npc_tem_desenho_e_fala(self):
        for name in set(pecas.NPCS.values()):
            self.assertIn(name, market.FALAS, name)
            for i in (0, 1):
                self.assertTrue((ROOT / "assets" / "pecas" / f"npc_{name}_parado{i}.png").exists(), name)

    def test_rota_do_npc(self):
        client = server.app.test_client()
        name = next(iter(pecas.NPCS.values()))
        self.assertEqual(client.get(f"/npc/{name}_0.png").status_code, 200)
        self.assertEqual(client.get("/npc/../segredo_0.png").status_code, 404)
        self.assertEqual(client.get(f"/npc/{name}_7.png").status_code, 404)

    def test_npc_card_por_capitulo(self):
        class Stall:
            def __init__(self, kind, chapter):
                self.kind, self.chapter, self.x, self.y = kind, chapter, 100, 200
        for (kind, chapter), name in pecas.NPCS.items():
            card = market.npc_card(Stall(kind, chapter))
            self.assertEqual(card["name"], name)
            self.assertIn(card["fala"], market.FALAS[name])


class ArmaNaMao(unittest.TestCase):
    def test_hand_card(self):
        self.assertIsNone(remote.hand_card(None))

        class W:
            name = "Espada"
        card = remote.hand_card(W())
        self.assertEqual(card["name"], "ESPADA")
        self.assertTrue(card["icon"])


if __name__ == "__main__":
    unittest.main()
