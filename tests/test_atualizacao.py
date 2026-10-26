"""Botão ATUALIZAR: consulta ao GitHub, troca dos arquivos e volta atrás se der errado.

Nenhum teste usa a internet de verdade: o GitHub é simulado com respostas falsas.
"""
import io
import json
import tempfile
import time
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

import pygame

from apoio import game
from soulstrike import __version__, updater


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def release(tag="v9.0.0", **extra):
    data = {"tag_name": tag, "body": "Novidades\nmais coisas",
            "zipball_url": "https://api.github.com/zip", "html_url": "https://github.com/x/releases/v9"}
    data.update(extra)
    return data


def opener_para(respostas):
    """respostas: url -> bytes, ou exceção para levantar."""
    def opener(url, timeout=None):
        value = respostas[url]
        if isinstance(value, Exception):
            raise value
        return Resposta(value)
    return opener


def zip_de(arquivos, pasta="cauapbritto-joguin-abc123/"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nome, conteudo in arquivos.items():
            zf.writestr(pasta + nome, conteudo)
    return buf.getvalue()


def http_erro(code):
    return urllib.error.HTTPError(updater.API_LATEST, code, "erro", {}, None)


class TestVersao(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(updater.parse_version("2"), (2, 0, 0))
        self.assertEqual(updater.parse_version("1.10-beta"), (1, 10, 0))
        self.assertEqual(updater.parse_version("lixo"), (0, 0, 0))

    def test_compara_numeros_e_nao_texto(self):
        self.assertTrue(updater.is_newer("v1.10.0", "1.9.0"))
        self.assertFalse(updater.is_newer("v1.0.0", "1.0.0"))
        self.assertFalse(updater.is_newer("v0.9.9", "1.0.0"))

    def test_versao_do_jogo_e_valida(self):
        self.assertGreater(updater.parse_version(__version__), (0, 0, 0))


class TestConsulta(unittest.TestCase):
    def consulta(self, value):
        payload = json.dumps(value).encode() if isinstance(value, dict) else value
        return updater.check(opener_para({updater.API_LATEST: payload}))

    def test_versao_nova(self):
        deb = {"name": "soulstrike_9.0.0_amd64.deb", "browser_download_url": "https://x/a.deb"}
        info = self.consulta(release(assets=[deb]))
        self.assertEqual(info.status, "nova")
        self.assertEqual(info.latest, "9.0.0")
        self.assertEqual(info.deb_url, "https://x/a.deb")
        self.assertTrue(info.notes.startswith("Novidades"))

    def test_mesma_versao(self):
        self.assertEqual(self.consulta(release(tag="v" + __version__)).status, "atual")

    def test_sem_internet_nao_levanta(self):
        for erro in (urllib.error.URLError("sem rede"), TimeoutError(), ConnectionResetError(), OSError()):
            self.assertEqual(self.consulta(erro).status, "offline")

    def test_sem_release_e_limite(self):
        self.assertEqual(self.consulta(http_erro(404)).status, "sem_release")
        self.assertEqual(self.consulta(http_erro(403)).status, "erro")
        self.assertEqual(self.consulta(http_erro(500)).status, "erro")

    def test_copia_do_itch_abre_a_pagina_do_itch(self):
        deb = {"name": "soulstrike_9.0.0_amd64.deb", "browser_download_url": "https://x/a.deb"}
        loja = {"loja": "itch", "pagina": "https://fulano.itch.io/soul-strike"}
        with mock.patch.object(updater, "store", return_value=loja):
            info = self.consulta(release(assets=[deb]))
        self.assertEqual(info.status, "nova")
        self.assertEqual(info.page_url, "https://fulano.itch.io/soul-strike")
        self.assertEqual(info.deb_url, "")

    def test_resposta_estranha(self):
        self.assertEqual(self.consulta(b"<html>").status, "erro")
        self.assertEqual(self.consulta(b"[]").status, "erro")
        self.assertEqual(self.consulta({"sem": "tag"}).status, "erro")


class TestAplicar(unittest.TestCase):
    """Pasta falsa no formato da instalação pelo INSTALAR.bat/.sh."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.escrever({
            "main.py": "velho",
            "requirements.txt": "pygame>=2.5\n",
            "soulstrike/__init__.py": "velho",
            "soulstrike/game.py": "velho",
            "assets/sons/a.wav": "som",
            ".venv/lib/pacote.py": "do venv",
            "instalar.log": "log",
            "meu_arquivo.txt": "do jogador",
        })
        self.info = updater.Check("nova", latest="9.0.0", zip_url="https://zip")

    def tearDown(self):
        self._tmp.cleanup()

    def escrever(self, arquivos):
        for nome, conteudo in arquivos.items():
            p = self.root / nome
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(conteudo)

    def ler(self, nome):
        return (self.root / nome).read_text()

    def novo_zip(self, **trocas):
        arquivos = {"main.py": "novo", "requirements.txt": "pygame>=2.5\n",
                    "soulstrike/__init__.py": "novo", "soulstrike/game.py": "novo",
                    "soulstrike/novo_modulo.py": "novo", "assets/sons/a.wav": "som",
                    ".venv/lib/pacote.py": "NÃO COPIAR", "instalar.log": "NÃO COPIAR"}
        arquivos.update(trocas)
        return zip_de(arquivos)

    def aplicar(self, data, pip=None):
        pip = pip or mock.Mock(return_value=True)
        result = updater.apply(self.info, root=self.root, opener=opener_para({"https://zip": data}), pip=pip)
        return result, pip

    def test_troca_arquivos_e_preserva_venv_e_logs(self):
        result, pip = self.aplicar(self.novo_zip())
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.restart)
        self.assertEqual(self.ler("main.py"), "novo")
        self.assertEqual(self.ler("soulstrike/game.py"), "novo")
        self.assertEqual(self.ler("soulstrike/novo_modulo.py"), "novo")
        self.assertEqual(self.ler(".venv/lib/pacote.py"), "do venv")
        self.assertEqual(self.ler("instalar.log"), "log")
        self.assertEqual(self.ler("meu_arquivo.txt"), "do jogador")
        self.assertFalse((self.root / ".backup_atualizacao").exists())
        self.assertNotIn("assets/sons/a.wav", result.changed)      # igual: nem regravado
        pip.assert_not_called()                                    # requirements igual

    def test_bibliotecas_novas_rodam_pip(self):
        result, pip = self.aplicar(self.novo_zip(**{"requirements.txt": "pygame>=2.6\n"}))
        self.assertTrue(result.ok)
        pip.assert_called_once()

    def test_pip_falhou_volta_tudo(self):
        result, _ = self.aplicar(self.novo_zip(**{"requirements.txt": "pygame>=2.6\n"}),
                                 pip=mock.Mock(return_value=False))
        self.assertFalse(result.ok)
        self.assertFalse(result.restart)
        self.assertEqual(self.ler("main.py"), "velho")
        self.assertEqual(self.ler("requirements.txt"), "pygame>=2.5\n")
        self.assertFalse((self.root / "soulstrike/novo_modulo.py").exists())
        self.assertFalse((self.root / ".backup_atualizacao").exists())

    def test_erro_ao_gravar_volta_tudo(self):
        real = updater.os.replace
        calls = []

        def falha_no_terceiro(src, dst):
            calls.append(dst)
            if len(calls) == 3:
                raise PermissionError("arquivo em uso")
            real(src, dst)

        with mock.patch.object(updater.os, "replace", side_effect=falha_no_terceiro):
            result, _ = self.aplicar(self.novo_zip())
        self.assertFalse(result.ok)
        self.assertEqual(self.ler("main.py"), "velho")
        self.assertEqual(self.ler("soulstrike/game.py"), "velho")
        self.assertEqual(self.ler("soulstrike/__init__.py"), "velho")
        self.assertFalse((self.root / "soulstrike/novo_modulo.py").exists())

    def test_download_caiu_nada_muda(self):
        result, _ = self.aplicar(urllib.error.URLError("caiu"))
        self.assertFalse(result.ok)
        self.assertEqual(self.ler("main.py"), "velho")

    def test_zip_corrompido_ou_de_outro_projeto(self):
        for data in (b"isto nao e zip", zip_de({"leia.txt": "oi"})):
            result, _ = self.aplicar(data)
            self.assertFalse(result.ok)
            self.assertEqual(self.ler("main.py"), "velho")

    def test_zip_com_caminho_para_fora_e_recusado(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x/main.py", "novo")
            zf.writestr("x/soulstrike/__init__.py", "novo")
            zf.writestr("../../fora.txt", "mal")
        result, _ = self.aplicar(buf.getvalue())
        self.assertFalse(result.ok)
        self.assertEqual(self.ler("main.py"), "velho")

    def test_clone_do_git_nao_e_sobrescrito(self):
        (self.root / ".git").mkdir()
        result, _ = self.aplicar(self.novo_zip())
        self.assertFalse(result.ok)
        self.assertIn("git pull", result.message)
        self.assertEqual(self.ler("main.py"), "velho")

    def test_executavel_so_avisa(self):
        with mock.patch.object(updater.sys, "frozen", True, create=True):
            self.assertEqual(updater.install_kind(self.root), "executavel")
            result, _ = self.aplicar(self.novo_zip())
        self.assertFalse(result.ok)
        self.assertEqual(self.ler("main.py"), "velho")

    def test_copia_do_itch_so_avisa(self):
        (self.root / updater.STORE_FILE).write_text(
            json.dumps({"loja": "itch", "pagina": "https://fulano.itch.io/soul-strike"}), encoding="utf-8")
        with mock.patch.object(updater.sys, "frozen", True, create=True):
            self.assertEqual(updater.install_kind(self.root), "itch")
            result, _ = self.aplicar(self.novo_zip())
        self.assertFalse(result.ok)
        self.assertEqual(self.ler("main.py"), "velho")
        self.assertEqual(updater.page_url(self.root), "https://fulano.itch.io/soul-strike")

    def test_loja_json_estragado_e_ignorado(self):
        (self.root / updater.STORE_FILE).write_text("{nao e json", encoding="utf-8")
        self.assertEqual(updater.store(self.root), {})
        self.assertEqual(updater.install_kind(self.root), "fonte")
        self.assertEqual(updater.page_url(self.root), updater.RELEASES_PAGE)

    def test_tipo_de_instalacao(self):
        self.assertEqual(updater.install_kind(self.root), "fonte")
        self.assertEqual(updater.install_kind(self.root / "soulstrike"), "somente_leitura")

    def test_progresso_salvo_fica_fora_da_pasta_do_jogo(self):
        from soulstrike import config, progress
        root = Path(config.ROOT).resolve()
        with mock.patch.dict("os.environ", {"SOULSTRIKE_PROGRESS": ""}):
            self.assertNotIn(root, progress.path().resolve().parents)


class TestTela(unittest.TestCase):
    def esperar(self, scene):
        for _ in range(200):
            scene.update()
            if scene.state not in ("checking", "applying"):
                return
            time.sleep(0.01)
        self.fail("a tela ficou presa esperando")

    def tela(self, info, kind="fonte"):
        from soulstrike.scenes.update import UpdateScene
        with mock.patch.object(updater, "install_kind", return_value=kind):
            scene = UpdateScene(game(), start=False)
        with mock.patch.object(updater, "check", return_value=info):
            scene.start_check()
            self.esperar(scene)
        scene.draw(game().screen)
        return scene

    def valores(self, scene):
        return [v for _, v in scene.menu.options]

    def test_item_no_menu_principal(self):
        from soulstrike.scenes.menus import TitleScene
        self.assertIn("update", [v for _, v in TitleScene(game()).menu.options])

    def test_versao_nova_oferece_atualizar(self):
        scene = self.tela(updater.Check("nova", latest="9.0.0", message="Versão 9.0.0 disponível"))
        self.assertEqual(self.valores(scene), ["apply", "back"])

    def test_executavel_oferece_pagina(self):
        scene = self.tela(updater.Check("nova", latest="9.0.0"), kind="executavel")
        self.assertEqual(self.valores(scene), ["page", "back"])

    def test_itch_oferece_pagina_do_itch(self):
        info = updater.Check("nova", latest="9.0.0", page_url="https://fulano.itch.io/soul-strike")
        scene = self.tela(info, kind="itch")
        self.assertEqual(self.valores(scene), ["page", "back"])
        self.assertTrue(any("ITCH.IO" in t for t, _ in scene.lines()))
        with mock.patch("webbrowser.open") as abrir:
            scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        abrir.assert_called_once_with("https://fulano.itch.io/soul-strike")

    def test_sem_internet_oferece_tentar_de_novo(self):
        scene = self.tela(updater.Check("offline", message="Sem conexão com a internet."))
        self.assertEqual(self.valores(scene), ["retry", "back"])
        self.assertTrue(any("SEM CONEXÃO" in t.upper() for t, _ in scene.lines()))

    def test_atualizado(self):
        scene = self.tela(updater.Check("atual", latest=__version__))
        self.assertEqual(self.valores(scene), ["back"])

    def test_aplicar_pela_tela(self):
        scene = self.tela(updater.Check("nova", latest="9.0.0", zip_url="z"))
        ok = updater.Result(True, "Atualizado!", restart=True, changed=["main.py"])
        with mock.patch.object(updater, "apply", return_value=ok) as apply, \
                mock.patch.object(updater, "restart") as restart:
            scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.esperar(scene)
            scene.draw(game().screen)
        apply.assert_called_once()
        restart.assert_not_called()            # jogo dos testes não tem janela: não reabre
        self.assertEqual(scene.state, "done")

    def test_esc_volta_ao_titulo(self):
        from soulstrike.scenes.menus import TitleScene
        g = game()
        scene = self.tela(updater.Check("atual"))
        g.change(scene)
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsInstance(g.scene, TitleScene)


class TestSoAquiUsaInternet(unittest.TestCase):
    def test_jogo_nao_acessa_a_internet_sem_o_botao(self):
        """Abrir o jogo e passear pelos menus não pode chamar a internet."""
        from soulstrike.scenes.menus import ModeScene, TitleScene
        g = game()
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("usou a internet")) as net:
            g.change(TitleScene(g))
            for _ in range(5):
                g.step([])
            g.change(ModeScene(g))
            for _ in range(5):
                g.step([])
        net.assert_not_called()


if __name__ == "__main__":
    unittest.main()
