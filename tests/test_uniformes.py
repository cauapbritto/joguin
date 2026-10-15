"""Uniformes do futebol: cada herói joga com a roupa da cor do time (azul ou vermelho),
na partida, nos cards da seleção e na tela de VS; fora do futebol fica a roupa de sempre."""
import importlib.util
import unittest

import pygame

from apoio import game

from soulstrike import config
from soulstrike.assets import TEAM_KITS
from soulstrike.data import CHARACTERS, SHADOW_CHARACTERS
from soulstrike.matches import BattleMatch, SoccerMatch, TeamBattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
HEROES = [c for c in CHARACTERS if c.key not in SHADOW_CHARACTERS]


def gerador():
    spec = importlib.util.spec_from_file_location("gerar_sprites", config.ROOT / "tools" / "gerar_sprites.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    return gen


def tom(img):
    """Quantos pixels puxam para o azul e quantos para o vermelho (roupa de time é bem saturada)."""
    azul = vermelho = 0
    for y in range(img.get_height()):
        for x in range(img.get_width()):
            r, g, b, a = img.get_at((x, y))
            if a < 200:
                continue
            if b > r + 60 and b > g + 40:
                azul += 1
            elif r > g + 90 and r > b + 90:
                vermelho += 1
    return azul, vermelho


def futebol(chars, mode="soccer2"):
    g = game()
    g.session = Session(mode, [SlotSetup(i + 1, char=KEYS.index(c), cpu=True) for i, c in enumerate(chars)])
    return g, SoccerMatch(g, g.session)


class UniformeTest(unittest.TestCase):
    def test_todo_heroi_tem_os_dois_uniformes(self):
        assets = game().assets
        for stats in HEROES:
            base = assets.sprites[stats.key]
            for team in (0, 1):
                kit = assets.kit_sprites(stats.key, team)
                self.assertIsNot(kit, base, f"{stats.key} sem uniforme {TEAM_KITS[team]}")
                a, b = base.portrait, kit.portrait
                self.assertEqual(a.get_size(), b.get_size(), stats.key)
                # mesma mão da arma e mesmo desenho, só a roupa muda de cor
                self.assertEqual(base.hand("direita", "ataque", 1), kit.hand("direita", "ataque", 1))
                self.assertEqual(pygame.mask.from_surface(a).count(), pygame.mask.from_surface(b).count(), stats.key)

    def test_cor_do_uniforme_e_a_do_time(self):
        assets = game().assets
        for stats in HEROES:
            azul = tom(assets.kit_sprites(stats.key, 0).portrait)
            vermelho = tom(assets.kit_sprites(stats.key, 1).portrait)
            self.assertGreater(azul[0], azul[1] + 15, f"{stats.key} azul {azul}")
            self.assertGreater(vermelho[1], vermelho[0] + 15, f"{stats.key} vermelho {vermelho}")

    def test_partida_de_futebol_veste_cada_time(self):
        g, m = futebol(("pirata", "guerreiro", "velocista", "geada"))
        for f in m.fighters:
            self.assertIs(f.sprites, g.assets.kit_sprites(f.stats.key, f.team))
        # o pirata (casaco vermelho) no time azul fica de azul; o guerreiro (tabardo azul) no vermelho, de vermelho
        pirata = next(f for f in m.fighters if f.stats.key == "pirata")
        guerreiro = next(f for f in m.fighters if f.stats.key == "guerreiro")
        self.assertEqual((pirata.team, guerreiro.team), (0, 1))
        azul, vermelho = tom(pirata.sprites.portrait)
        self.assertGreater(azul, vermelho)
        azul, vermelho = tom(guerreiro.sprites.portrait)
        self.assertGreater(vermelho, azul)

    def test_mesmo_heroi_nos_dois_times(self):
        g, m = futebol(("ninja", "ninja"), mode="soccer1")
        a, b = m.fighters
        self.assertNotEqual(a.team, b.team)
        self.assertIsNot(a.sprites, b.sprites)
        self.assertNotEqual(pygame.image.tobytes(a.sprites.portrait, "RGBA"),
                            pygame.image.tobytes(b.sprites.portrait, "RGBA"))

    def test_fora_do_futebol_roupa_de_sempre(self):
        g = game()
        g.session = Session("duel", [SlotSetup(1, char=KEYS.index("pirata")), SlotSetup(2, char=KEYS.index("guerreiro"))])
        for f in BattleMatch(g, g.session).fighters:
            self.assertIs(f.sprites, g.assets.sprites[f.stats.key])
        g.session = Session("duel2", [SlotSetup(i, char=KEYS.index("ninja"), cpu=True) for i in (1, 2, 3, 4)])
        for f in TeamBattleMatch(g, g.session).fighters:
            self.assertIs(f.sprites, g.assets.sprites[f.stats.key])

    def test_alma_corrompida_fica_sombria(self):
        assets = game().assets
        for key in SHADOW_CHARACTERS:
            self.assertIs(assets.kit_sprites(key, 0), assets.sprites[key])

    def test_desenha_com_uniforme(self):
        g, m = futebol(("tita", "fantasma", "tanque", "aryel"))
        for _ in range(30):
            m.update()
        m.draw(g.screen, g.ui)

    def test_uniforme_igual_ao_gerador(self):
        gen = gerador()
        for team, kit in gen.KITS.items():
            sheet, _ = gen.build_sheet("pirata", kit)
            saved = pygame.image.load(str(config.CHAR_DIR / "uniformes" / f"pirata_{team}.png"))
            self.assertEqual(pygame.image.tobytes(sheet, "RGBA"), pygame.image.tobytes(saved.convert_alpha(), "RGBA"))
        self.assertEqual(tuple(gen.KITS), TEAM_KITS)


class TelasTest(unittest.TestCase):
    def test_selecao_e_versus_do_futebol(self):
        from soulstrike.scenes.play import VersusScene
        from soulstrike.scenes.select import CharSelectScene
        g = game()
        g.session = Session("soccer2", [SlotSetup(s, char=KEYS.index("pirata")) for s in (1, 2, 3, 4)])
        scene = CharSelectScene(g)
        scene.update()
        scene.draw(g.screen)
        g.session = Session("soccer1", [SlotSetup(1, char=KEYS.index("tita")), SlotSetup(2, char=KEYS.index("tita"))])
        vs = VersusScene(g)
        for _ in range(30):
            vs.update()
        vs.draw(g.screen)


if __name__ == "__main__":
    unittest.main()
