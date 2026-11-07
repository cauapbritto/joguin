"""História costurada: a voz do cristal, a Patrulha Cinza, a Casa (abertura e epílogo) e as falas dos chefes."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from apoio import FakeInput, game  # noqa: E402

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


class CinemaTest(unittest.TestCase):
    def setUp(self):
        from soulstrike.scenes.campaign import CinemaScene
        self.g = game()
        self.g.session = Session("campaign", [SlotSetup(1, char=0)])
        self._inputs = dict(self.g.inputs)
        self.g.inputs.update({slot: FakeInput() for slot in (1, 2, 3, 4)})     # ninguém apertando nada
        self.scene = CinemaScene(self.g)

    def tearDown(self):
        self.g.inputs.update(self._inputs)

    def test_filme_completo_vai_da_abertura_ao_epilogo(self):
        from soulstrike.scenes.cinema_sala import FULL
        label, keys = FULL
        self.assertEqual(keys[0], "abertura")
        self.assertEqual(keys[-2:], ("creditos", "epilogo"))
        self.assertNotIn("reuniao_corrompidos", keys)
        self.assertEqual(self.scene.items[0], FULL)

    def test_sala_entra_apaga_abre_e_passa_sozinho(self):
        s = self.scene
        s._choose("1")                                   # capítulo 1 sozinho
        estados, paginas = [], set()
        for _ in range(900):
            s.update()
            estados.append(s.state)
            if s.film is not None:
                paginas.add((s.film.key, s.film.page))
        for etapa in ("entrada", "apaga", "abre", "filme"):
            self.assertIn(etapa, estados)
        self.assertIn(("abertura", 1), paginas)          # passou de página sem ninguém apertar
        s.draw(self.g.screen)

    def test_plateia_reage_entre_capitulos_e_aplaude_no_fim(self):
        s = self.scene
        s._choose("0")                                   # filme completo
        estados = set()
        for _ in range(20000):
            if s.state == "filme":
                s.film.skip()
            s.update()
            estados.add(s.state)
            if s.state == "menu":
                break
        self.assertIn("plateia", estados)               # fim do capítulo 1 tem reação
        self.assertIn("aplauso", estados)
        self.assertEqual(s.state, "menu")

    def test_segurar_esc_sai(self):
        from soulstrike.scenes.cinema_sala import HOLD_EXIT

        class Segura:
            def held(self, action):
                return action == "pause"

            def pressed(self, action):
                return False
        s = self.scene
        s._choose("0")
        for slot in (1, 2, 3, 4):
            self.g.inputs[slot] = Segura()
        for _ in range(HOLD_EXIT):
            s.update()
        self.assertEqual(s.state, "menu")
        self.assertIsNone(s.film)

    def test_planos_desenham_todas_as_historias(self):
        from soulstrike.scenes.filme import Film
        for key in STORY:
            film = Film(self.g, key)
            film.title_left = 0
            for page in range(len(film.pages)):
                film.page, film.age = page, 30
                film.draw(self.g.screen, self.scene.ui)
