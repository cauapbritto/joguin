"""Todo módulo do jogo importa sozinho, antes de abrir janela.

Pega o erro de import (nome que sumiu de outro módulo, merge mal resolvido) como uma falha só e
com o nome do módulo, em vez de deixar o Game() quebrar no meio e derrubar centenas de testes.
"""
import importlib
import os
import pkgutil
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import soulstrike  # noqa: E402


class ImportsTest(unittest.TestCase):
    def test_todos_os_modulos_importam(self):
        nomes = [m.name for m in pkgutil.walk_packages(soulstrike.__path__, "soulstrike.")]
        self.assertIn("soulstrike.scenes.menus", nomes)
        for nome in nomes:
            with self.subTest(modulo=nome):
                importlib.import_module(nome)


if __name__ == "__main__":
    unittest.main()
