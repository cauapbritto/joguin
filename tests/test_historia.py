"""História costurada: a voz do cristal, a Patrulha Cinza, a Casa (abertura e epílogo) e as falas dos chefes."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from apoio import game  # noqa: E402

from soulstrike.campaign import STORY, VOICE  # noqa: E402
from soulstrike.session import Session, SlotSetup  # noqa: E402


def texto(key):
    return " ".join(text for _, _, text in STORY[key][2])


class HistoriaTest(unittest.TestCase):
    def test_voz_do_cristal_em_todo_capitulo(self):
        for key in ("abertura", "prologo", "cobertura", "clinica_recepcao", "mansao_sede"):
            self.assertIn(VOICE, [p for p, _, _ in STORY[key][2]], key)
        self.assertIn("IARA", texto("mansao_sede"))

    def test_patrulha_cinza_fecha_o_fio(self):
        self.assertIn("PATRULHA CINZA", texto("fim_capitulo1"))
        self.assertIn("MATO GRELHADO", texto("fim_capitulo1"))
        self.assertIn("rescindido", " ".join(t for _, _, t in STORY["fim_capitulo2"][2]))
        self.assertIn("Patrulha Cinza", texto("mansao_sede"))
        self.assertIn("contrato da Patrulha Cinza expira", texto("final"))

    def test_buracos_fechados(self):
        cap2 = texto("fim_capitulo2")
        self.assertIn("Albeguinio e do Cauanzera", cap2)
        self.assertIn("padaria da família", cap2)
        self.assertIn("chamou o TI", texto("fim_capitulo3"))
        self.assertIn("City quebrou de novo", texto("final"))
        self.assertIn("City do João", texto("fim_capitulo1"))

    def test_campanha_comeca_na_abertura_e_termina_no_epilogo(self):
        from soulstrike.scenes.campaign import CINEMA, StoryScene, start_campaign
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        scene = start_campaign(g)
        self.assertIsInstance(scene, StoryScene)
        self.assertTrue(scene.heading.startswith("ABERTURA"))
        self.assertIsInstance(scene.then(), StoryScene)
        self.assertEqual(scene.then().heading, "PRÓLOGO")
        chaves = [k for _, keys in CINEMA for k in keys]
        self.assertEqual(chaves[0], "abertura")
        self.assertIn("epilogo", chaves)

    def test_voz_desenha(self):
        from soulstrike.scenes.campaign import StoryScene
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=0)])
        scene = StoryScene(g, "abertura", lambda: None)
        scene.page = 2
        for _ in range(5):
            scene.update()
        scene.draw(g.screen)

    def test_chefes_falam_tres_vezes(self):
        from soulstrike.boss import AlbeguinioBossAI, BorbaBossAI, BossAI, BossLine, CauanzeraBossAI

        class Alvo:
            x, y = 100, 100

        class Partida:
            def __init__(self):
                self.popups = []

        for cls in (BossAI, BorbaBossAI, AlbeguinioBossAI, CauanzeraBossAI):
            self.assertEqual(len(cls.LINES), 3)
            self.assertTrue(all(len(line) <= 40 for line in cls.LINES), cls.__name__)
            brain, match = cls(), Partida()
            for which in (0, 0, 1, 2, 2):
                brain.say(Alvo(), match, which)
            self.assertEqual([p.text for p in match.popups], list(cls.LINES))
            self.assertTrue(all(isinstance(p, BossLine) for p in match.popups))
            self.assertEqual(match.popups[0].life, 150)


if __name__ == "__main__":
    unittest.main()
