"""Lado do jogo do app Android: canal rápido (UDP na porta do controle), descoberta na rede e /api/app."""
import json
import socket
import time
import unittest

from soulstrike import __version__
from soulstrike.net import rapido, server
from soulstrike.net.remote import hub

TOKEN = "app-teste"
SLOT = 3


class CanalRapidoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rapido.stop()
        rapido.start("127.0.0.1", 0)
        cls.port = rapido._sock.getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        rapido.stop()

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)
        hub._slots[SLOT].token = None                        # vaga limpa, mesmo que outro teste tenha usado
        self.assertTrue(hub.join(SLOT, TOKEN))
        hub.poll()

    def tearDown(self):
        self.sock.close()
        hub.leave(SLOT, TOKEN)
        hub.set_phase("menu", mode="battle")
        hub.poll()

    def send(self, data, pad=0):
        raw = json.dumps(data).encode()
        self.sock.sendto(raw + b" " * pad, ("127.0.0.1", self.port))

    def recv(self):
        raw, _ = self.sock.recvfrom(8192)
        return json.loads(raw.decode("utf-8")), len(raw)

    def entrada(self, seq, **extra):
        data = {"t": "in", "slot": SLOT, "token": TOKEN, "sid": "app", "seq": seq, "held": [], "counts": {},
                "x": 0, "y": 0}
        data.update(extra)
        return data

    def test_descoberta_responde_so_pergunta_acolchoada(self):
        self.send({"t": "oi", "v": 1})                       # pequena demais: sem resposta
        with self.assertRaises(socket.timeout):
            self.sock.settimeout(0.6)
            self.recv()
        self.sock.settimeout(2)
        self.send({"t": "oi", "v": 1}, pad=300)
        data, size = self.recv()
        self.assertEqual(data["t"], "jogo")
        self.assertEqual(data["jogo"], "soulstrike")
        self.assertEqual(data["versao"], __version__)
        self.assertEqual(data["v"], rapido.PROTOCOL)
        self.assertTrue(data["nome"])
        self.assertEqual(sorted(data["vagas"]), ["1", "2", "3", "4"])
        self.assertEqual(data["vagas"][str(SLOT)], [True, True])   # a vaga do teste está ocupada e conectada
        self.assertLess(size, rapido.DISCOVERY_MIN)                 # a resposta nunca é maior que a pergunta

    def test_entrada_aplica_e_responde_com_pulso(self):
        self.send(self.entrada(1, held=["attack"], counts={"attack": 1}, x=0.5, tm=1234))
        data, size = self.recv()
        self.assertEqual(data["t"], "p")
        self.assertEqual(data["seq"], 1)
        self.assertEqual(data["tm"], 1234)                   # o app mede o tempo de ida e volta
        self.assertTrue(data["me"]["owner"])
        self.assertIn("buzz", data["me"])
        self.assertIn("stamina", data["me"])
        held, pressed = hub.poll()
        self.assertIn(f"p{SLOT}_attack", held)
        self.assertIn(f"p{SLOT}_attack", pressed)
        self.assertEqual(hub.axes()[SLOT], (0.5, 0.0))
        self.assertLess(size, 600)

    def test_token_errado_nao_mexe(self):
        self.send(self.entrada(5, held=["attack"], token="outro"))
        data, _ = self.recv()
        self.assertEqual(data, {"t": "nao", "code": 403, "seq": 5})
        held, _ = hub.poll()
        self.assertNotIn(f"p{SLOT}_attack", held)

    def test_vibracao_sai_na_hora(self):
        self.send(self.entrada(1))
        first, _ = self.recv()
        before = first["me"]["buzz"][0]
        time.sleep(0.3)                                      # passa o intervalo mínimo entre vibrações
        self.assertTrue(hub.buzz(SLOT, "big_hit"))
        data, _ = self.recv()                                # sem mandar nada: o jogo avisa sozinho
        self.assertEqual(data["me"]["buzz"], [before + 1, "big_hit"])

    def test_numero_do_status_muda_so_com_o_resto(self):
        full = hub.status(SLOT, TOKEN)
        n = rapido.status_number(full)
        antes = full["me"]["char"]                           # a CPU sorteada em outro teste pode ter deixado qualquer um
        hub.publish_slot(SLOT, stamina=0.3, ammo=2)          # campos do pulso: o número fica
        self.assertEqual(rapido.status_number(hub.status(SLOT, TOKEN)), n)
        hub.publish_slot(SLOT, char=(antes or 0) + 1)        # trocou de personagem: o app busca o status
        self.assertNotEqual(rapido.status_number(hub.status(SLOT, TOKEN)), n)
        hub.publish_slot(SLOT, char=antes, stamina=1.0, ammo=0)

    def test_pulso_pequeno_mesmo_com_a_loja_aberta(self):
        hub.set_phase("playing", mode="campaign", active=[SLOT])
        shop = {"title": "LOJA", "items": [{"id": f"item{i}", "name": "ARMA MUITO RARA " * 3, "price": 999,
                                           "desc": "x" * 120} for i in range(30)]}
        hub.publish_slot(SLOT, shop=shop, souls=155, energy=140, emax=200, ecost=2)
        pulse = rapido.pulse(SLOT, TOKEN, 9, 1)
        self.assertLess(len(json.dumps(pulse, separators=(",", ":")).encode()), 600)
        self.assertEqual(pulse["me"]["souls"], 155)
        self.assertNotIn("shop", pulse["me"])
        hub.publish_slot(SLOT, shop=None, souls=None, energy=0, emax=0, ecost=0)

    def test_pacote_estranho_nao_derruba(self):
        self.sock.sendto(b"\xff\xfe nao e json", ("127.0.0.1", self.port))
        self.send({"t": "?"})
        self.send([1, 2, 3])
        self.send({"t": "oi"}, pad=300)
        data, _ = self.recv()
        self.assertEqual(data["t"], "jogo")


class ApiAppTest(unittest.TestCase):
    def test_api_app(self):
        client = server.app.test_client()
        data = client.get("/api/app").get_json()
        self.assertEqual(data["jogo"], "soulstrike")
        self.assertEqual(data["versao"], __version__)
        self.assertEqual(data["protocolo"], rapido.PROTOCOL)
        self.assertIn("udp", data)
        self.assertTrue(data["nome"])

    def test_porta_ocupada_fica_so_no_http(self):
        busy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        busy.bind(("127.0.0.1", 0))
        port = busy.getsockname()[1]
        old = rapido._sock
        try:
            rapido._sock = None
            self.assertIsNone(rapido.start("127.0.0.1", port))
            self.assertFalse(rapido.running())
            self.assertTrue(rapido.start_error)
        finally:
            rapido._sock = old
            rapido.start_error = None
            busy.close()


if __name__ == "__main__":
    unittest.main()
