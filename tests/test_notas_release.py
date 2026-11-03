"""O texto da Release sai das novidades e a tela de ATUALIZAR mostra o resumo primeiro."""
import importlib.util
import unittest
from pathlib import Path

from soulstrike import __version__, novidades

spec = importlib.util.spec_from_file_location(
    "notas_release", Path(__file__).resolve().parent.parent / "tools" / "notas_release.py")
notas_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notas_release)


class NotasReleaseTest(unittest.TestCase):
    def test_versao_atual_tem_novidades(self):
        self.assertIn(__version__, novidades.NEWS)

    def test_resumo_primeiro_como_a_tela_le(self):
        text = notas_release.notes("v" + __version__)
        shown = [ln.strip().lstrip("-*• ").strip() for ln in text.splitlines()]
        shown = [ln for ln in shown if ln and not ln.startswith("#")]
        self.assertEqual(shown[:len(novidades.summary(novidades.NEWS[__version__]))],
                         novidades.summary(novidades.NEWS[__version__]))

    def test_versao_sem_novidades(self):
        self.assertEqual(notas_release.notes("v0.0.1"), "Soul Strike 0.0.1")
