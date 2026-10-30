"""Sprites em pixel art: folhas com poses, mão da arma marcada, pose escolhida em cada
situação, caminhada de 8 quadros e olhos vermelhos nas almas corrompidas."""
import importlib.util
import unittest

import pygame

from apoio import FakeInput, game

from soulstrike import config
from soulstrike.assets import SHEET_POSES, SPORT_POSES, load_sheet
from soulstrike.data import CHARACTERS, SHADOW_CHARACTERS
from soulstrike.enemies import CREATURES, SHADOW_EYES
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]
HEROES = [c for c in CHARACTERS if c.key not in SHADOW_CHARACTERS]


def duelo(a="guerreiro", b="atirador"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))])
    match = BattleMatch(g, g.session)
    match.intro = 0
    p1, p2 = match.fighters
    match.controllers.clear()
    match.controllers[p1] = FakeInput()
    p1.x, p1.y, p2.x, p2.y = 400, 800, 900, 800
    return match, p1, p2


class FolhaTest(unittest.TestCase):
    def test_todos_tem_todas_as_poses(self):
        names = [c.sprite for c in HEROES] + [c.sprite for c in CREATURES.values()]
        for name in names:
            sprites = load_sheet(name)
            self.assertIsNotNone(sprites, name)
            for direction in ("frente", "costas", "direita", "esquerda"):
                for kind, n in SHEET_POSES:
                    frames = sprites.poses[direction][kind]
                    self.assertEqual(len(frames), n, (name, direction, kind))
                    # todos os quadros do mesmo tamanho: o pé fica sempre no mesmo lugar
                    self.assertEqual({f.get_size() for f in frames}, {frames[0].get_size()}, (name, kind))
            self.assertEqual(sprites.walk_len, 8)

    def test_quadros_da_caminhada_sao_diferentes(self):
        sprites = game().assets.sprites["guerreiro"]
        for direction in ("frente", "direita"):
            frames = [pygame.image.tobytes(f, "RGBA") for f in sprites.frames[direction]]
            self.assertGreaterEqual(len(set(frames)), 6, direction)

    def test_mao_da_arma_espelhada_na_esquerda(self):
        sprites = game().assets.sprites["atirador"]
        for kind, n in SHEET_POSES:
            for i in range(n):
                rx, ry = sprites.hand("direita", kind, i)
                lx, ly = sprites.hand("esquerda", kind, i)
                self.assertAlmostEqual(lx, -rx)
                self.assertEqual(ly, ry)
                self.assertGreater(rx, 0)                 # a mão fica à frente do corpo

    def test_golpe_estica_o_braco(self):
        sprites = game().assets.sprites["guerreiro"]
        rest = sprites.hand("direita", "parado", 0)
        hit = sprites.hand("direita", "ataque", 1)
        self.assertGreater(hit[0], rest[0] + 3)

    def test_folha_igual_ao_gerador(self):
        spec = importlib.util.spec_from_file_location("gerar_sprites", config.ROOT / "tools" / "gerar_sprites.py")
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        sheet, info = gen.build_sheet("aryel")
        saved = pygame.image.load(str(config.CHAR_DIR / "aryel.png"))
        self.assertEqual(sheet.get_size(), saved.get_size())
        self.assertEqual(pygame.image.tobytes(sheet, "RGBA"), pygame.image.tobytes(saved.convert_alpha(), "RGBA"))


class PoseTest(unittest.TestCase):
    def test_pose_de_cada_situacao(self):
        match, p1, _ = duelo()
        self.assertEqual(p1._pose()[0], "parado")
        p1.moving = True
        self.assertEqual(p1._pose()[0], "andar")
        p1.shoot_flash = 5
        self.assertEqual(p1._pose()[0], "andar")           # andando e atirando, as pernas continuam
        p1.moving = False
        self.assertEqual(p1._pose(), ("ataque", 1))
        p1.shoot_flash = 0
        p1.melee_flash = 12
        self.assertEqual(p1._pose(), ("ataque", 0))
        p1.melee_flash = 6
        self.assertEqual(p1._pose(), ("ataque", 1))
        p1.melee_flash = 2
        self.assertEqual(p1._pose(), ("ataque", 2))
        p1.hit_flash = 4
        self.assertEqual(p1._pose()[0], "dano")
        p1.dash_timer = 5
        self.assertEqual(p1._pose()[0], "esquiva")

    def test_caminhada_passa_pelos_oito_quadros(self):
        match, p1, _ = duelo()
        seen = set()
        for _ in range(60):
            p1.steer(1, 0)
            p1.update(match)
            seen.add(p1.anim_frame)
        self.assertEqual(seen, set(range(8)))

    def test_arma_acompanha_o_braco_no_golpe(self):
        match, p1, p2 = duelo()
        p1.weapon_index = 1                               # espada
        p1.facing, p1._dir = (1.0, 0.0), "direita"
        surf = pygame.Surface((1600, 1200))
        cam = match.camera
        cam.begin()
        p1.draw(surf, cam)
        p1.melee_flash = 6
        p1.draw(surf, cam)                                # não quebra com a pose de ataque

    def test_desenha_todas_as_poses_e_direcoes(self):
        match, p1, _ = duelo("pirata")
        surf = pygame.Surface((1600, 1200))
        cam = match.camera
        cam.begin()
        for facing, d in (((0, 1), "frente"), ((0, -1), "costas"), ((1, 0), "direita"), ((-1, 0), "esquerda")):
            p1.facing, p1._dir = facing, d
            for setup in ({}, {"moving": True}, {"melee_flash": 6}, {"hit_flash": 2}, {"dash_timer": 4},
                          {"stun_timer": 10}, {"giant_timer": 30}):
                for k, v in setup.items():
                    setattr(p1, k, v)
                p1.draw(surf, cam)
                for k in setup:
                    setattr(p1, k, 0 if k != "moving" else False)


class SombraTest(unittest.TestCase):
    def test_olhos_vermelhos_so_na_cabeca(self):
        assets = game().assets
        for c in HEROES:
            if c.soccer_only:
                continue                                  # craque do futebol não vira alma corrompida
            img = assets.shadow_sprites(c.sprite).pose("frente", "parado", 0)
            w, h = img.get_size()
            red = [(x, y) for y in range(h) for x in range(w) if tuple(img.get_at((x, y)))[:3] == SHADOW_EYES]
            self.assertTrue(red, c.key)
            self.assertLess(max(y for _, y in red), h // 2, c.key)

    def test_sombra_tem_as_mesmas_poses(self):
        assets = game().assets
        normal, shadow = assets.sprites["ninja"], assets.shadow_sprites("ninja")
        for d in normal.poses:
            self.assertEqual(set(normal.poses[d]), set(shadow.poses[d]))
        self.assertEqual(shadow.hand("direita", "ataque", 1), normal.hand("direita", "ataque", 1))


    def test_herois_tem_as_poses_do_esporte(self):
        assets = game().assets
        for c in CHARACTERS:
            sprites = assets.sprites[c.sprite]
            for kind, n in SPORT_POSES:
                self.assertEqual(len(sprites.poses["direita"][kind]), n, (c.key, kind))
                self.assertIsNotNone(sprites.hand("direita", kind, 0), (c.key, kind))

    def test_pose_que_falta_cai_no_parado(self):
        sprites = game().assets.sprites["diabrete"]
        self.assertNotIn("chute", sprites.poses["frente"])
        self.assertIs(sprites.pose("frente", "chute", 1), sprites.pose("frente", "parado", 0))


if __name__ == "__main__":
    unittest.main()
