"""Testes do controle pelo celular: rede fora de ordem, atrasos e celular que some."""
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soulstrike.controls import PlayerInput  # noqa: E402
from soulstrike.net import remote  # noqa: E402
from soulstrike.net.remote import RemoteHub  # noqa: E402


class EstadoCompletoTest(unittest.TestCase):
    def test_pedido_atrasado_nao_prende_o_botao(self):
        hub = RemoteHub()
        # o celular apertou (seq 1) e soltou (seq 2), mas o "soltou" chegou primeiro
        hub.apply_input(1, "s", 2, [], {"attack": 1})
        hub.apply_input(1, "s", 1, ["attack"], {"attack": 1})
        held, pressed = hub.poll()
        self.assertIn("p1_attack", pressed)          # o aperto conta
        self.assertNotIn("p1_attack", held)          # mas não fica preso

    def test_toque_rapido_entre_dois_quadros(self):
        hub = RemoteHub()
        hub.apply_input(2, "s", 1, ["special"], {"special": 1})
        hub.apply_input(2, "s", 2, [], {"special": 1})
        held, pressed = hub.poll()
        self.assertIn("p2_special", pressed)
        self.assertEqual(held, frozenset())
        self.assertEqual(hub.poll()[1], frozenset())  # contado uma vez só

    def test_pedido_repetido_nao_aperta_de_novo(self):
        hub = RemoteHub()
        hub.apply_input(1, "s", 1, [], {"dodge": 1})
        hub.poll()
        hub.apply_input(1, "s", 1, [], {"dodge": 1})   # mesmo pedido chegou duas vezes
        hub.apply_input(1, "s", 3, [], {"dodge": 1})   # pulsação sem toque novo
        self.assertEqual(hub.poll()[1], frozenset())

    def test_pagina_recarregada_recomeca_a_contagem(self):
        hub = RemoteHub()
        hub.apply_input(1, "a", 50, [], {"confirm": 5})
        hub.poll()
        hub.apply_input(1, "b", 1, [], {"confirm": 1})   # sessão nova, seq e contagem do zero
        self.assertIn("p1_confirm", hub.poll()[1])

    def test_analogico_atrasado_e_ignorado(self):
        hub = RemoteHub()
        hub.apply_input(1, "s", 5, [], {}, 0.0, 0.0)     # soltou o analógico
        hub.apply_input(1, "s", 4, [], {}, 1.0, 0.0)     # posição antiga chegou depois
        self.assertNotIn(1, hub.axes())

    def test_celular_sumiu_solta_tudo(self):
        hub = RemoteHub()
        hub.apply_input(2, "s", 1, ["attack", "right"], {"attack": 1}, 1.0, 0.0)
        self.assertIn("p2_attack", hub.poll()[0])
        later = remote.time.monotonic() + remote.INPUT_TIMEOUT + 0.1
        with mock.patch.object(remote.time, "monotonic", return_value=later):
            held, _ = hub.poll()
            self.assertEqual(held, frozenset())
            self.assertNotIn(2, hub.axes())

    def test_atraso_curto_mantem_o_comando(self):
        hub = RemoteHub()
        hub.apply_input(2, "s", 1, ["dribble"], {"dribble": 1}, 0.0, -1.0)
        later = remote.time.monotonic() + remote.INPUT_TIMEOUT * 0.7
        with mock.patch.object(remote.time, "monotonic", return_value=later):
            self.assertIn("p2_dribble", hub.poll()[0])
            self.assertEqual(hub.axes()[2], (0.0, -1.0))

    def test_comando_desconhecido_e_ignorado(self):
        hub = RemoteHub()
        hub.apply_input(1, "s", 1, ["hack"], {"hack": 3})
        self.assertEqual(hub.poll(), (frozenset(), frozenset()))

    def test_vagas_independentes(self):
        hub = RemoteHub()
        hub.apply_input(1, "s", 9, ["up"], {"up": 1})
        hub.apply_input(2, "t", 1, ["down"], {"down": 1})   # seq de outra vaga não interfere
        held, _ = hub.poll()
        self.assertEqual(held, {"p1_up", "p2_down"})


class AnalogicoTest(unittest.TestCase):
    def _input(self, held=(), analog=None):
        inp = PlayerInput(2)
        keys = mock.MagicMock()
        keys.__getitem__.return_value = False
        inp.update(keys, set(), {f"p2_{a}" for a in held}, set(), 0, analog)
        return inp

    def test_analogico_do_celular_tem_prioridade_sobre_setas_do_celular(self):
        inp = self._input(held=("right",), analog=(0.5, 0.2))
        self.assertEqual(inp.axis(), (0.5, 0.2))      # 360 graus e meia velocidade

    def test_setas_do_celular_sem_analogico(self):
        inp = self._input(held=("left",))
        self.assertEqual(inp.axis(), (-1.0, 0.0))


class RotaInputTest(unittest.TestCase):
    def test_so_o_dono_da_vaga_controla(self):
        from soulstrike.net import server
        from soulstrike.net.remote import hub
        client = server.app.test_client()
        self.assertTrue(client.post("/api/join", json={"slot": 3, "token": "dono"}).get_json()["ok"])
        r = client.post("/api/input", json={"slot": 3, "token": "intruso", "sid": "x", "seq": 1,
                                            "held": ["attack"], "counts": {"attack": 1}})
        self.assertEqual(r.status_code, 403)
        hub.poll()
        r = client.post("/api/input", json={"slot": 3, "token": "dono", "sid": "x", "seq": 1,
                                            "held": ["attack"], "counts": {"attack": 1}, "x": 0.3, "y": 0})
        self.assertEqual(r.status_code, 204)
        held, pressed = hub.poll()
        self.assertIn("p3_attack", held)
        self.assertIn("p3_attack", pressed)
        self.assertEqual(client.post("/api/input", json={"slot": 3, "token": "dono", "seq": "x"}).status_code, 400)
        client.post("/api/leave", json={"slot": 3, "token": "dono"})
        hub.poll()

    def test_pagina_usa_versao_dos_arquivos(self):
        from soulstrike.net import server
        html = server.app.test_client().get("/").get_data(as_text=True)
        self.assertIn("controller.js?v=", html)


if __name__ == "__main__":
    unittest.main()
