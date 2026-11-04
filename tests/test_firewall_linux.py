"""Celular no Linux: o firewall (ufw) ligado barra o controle em silêncio.

O menu e a tela de escolha mostram o comando para liberar a porta enquanto nenhum
aparelho da rede chegou ao jogo; o instalador lê o ufw.conf sem pedir senha.
"""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from soulstrike import config
from soulstrike.net import server

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UfwTest(unittest.TestCase):
    def _conf(self, texto):
        f = tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf")
        f.write(texto)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_le_o_ufw_conf(self):
        self.assertTrue(server.ufw_enabled(self._conf("# ufw\nENABLED=yes\nLOGLEVEL=low\n")))
        self.assertTrue(server.ufw_enabled(self._conf("ENABLED='yes'\n")))
        self.assertFalse(server.ufw_enabled(self._conf("ENABLED=no\n")))
        self.assertFalse(server.ufw_enabled("/nao/existe/ufw.conf"))

    def _hint(self, plataforma, ligado, visto=False):
        with mock.patch.object(server.sys, "platform", plataforma), \
                mock.patch.object(server, "_ufw_cache", None), \
                mock.patch.object(server, "remote_seen", visto), \
                mock.patch.object(server, "ufw_enabled", return_value=ligado):
            return server.firewall_hint()

    def test_dica_so_no_linux_com_firewall_e_sem_celular(self):
        self.assertEqual(self._hint("linux", True), f"sudo ufw allow {config.WEB_PORT}/tcp")
        self.assertIsNone(self._hint("linux", False))
        self.assertIsNone(self._hint("win32", True))
        self.assertIsNone(self._hint("linux", True, visto=True))


class AparelhoDaRedeTest(unittest.TestCase):
    def test_pedido_de_fora_marca_que_a_rede_esta_liberada(self):
        h = server._Handler.__new__(server._Handler)
        with mock.patch.object(server, "remote_seen", False), \
                mock.patch("http.server.BaseHTTPRequestHandler.setup"):
            h.client_address = ("127.0.0.1", 1234)
            server._Handler.setup(h)
            self.assertFalse(server.remote_seen)
            h.client_address = ("192.168.1.40", 1234)
            server._Handler.setup(h)
            self.assertTrue(server.remote_seen)


class EnderecoAtualizaTest(unittest.TestCase):
    def test_wifi_que_conecta_depois_troca_o_endereco(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from apoio import game
        g = game()
        with mock.patch.object(server, "local_ip", return_value="127.0.0.1"):
            g._url_at = -10 ** 9
            self.assertIn("127.0.0.1", g.base_url)
        with mock.patch.object(server, "local_ip", return_value="192.168.0.50"):
            self.assertIn("127.0.0.1", g.base_url)          # ainda dentro do intervalo
            g._url_at -= g.URL_REFRESH_MS
            self.assertEqual(g.base_url, f"http://192.168.0.50:{config.WEB_PORT}")


class InstaladorTest(unittest.TestCase):
    def test_instalador_le_o_conf_sem_sudo(self):
        texto = open(os.path.join(RAIZ, "linux", "instalar.sh"), encoding="utf-8").read()
        self.assertNotIn("sudo -n ufw", texto)
        self.assertIn("/etc/ufw/ufw.conf", texto)
        self.assertIn("ufw allow", texto)
        subprocess.run(["bash", "-n", os.path.join(RAIZ, "linux", "instalar.sh")], check=True)


if __name__ == "__main__":
    unittest.main()
