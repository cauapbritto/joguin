"""Animações e desempenho: paredes prontas, direção do sprite, mira, câmera em degraus,
queda, respiração, QR codes, servidor do celular e o 2x2 com CPU completando o time."""
import json
import threading
import unittest
from fractions import Fraction
from http.client import HTTPConnection

import pygame

from apoio import FakeInput, game, run

from soulstrike import config
from soulstrike.arena import MAPS, MAPS_BY_KEY, Arena
from soulstrike.camera import Camera
from soulstrike.scenery import THEMED_MAPS
from soulstrike.data import CHARACTERS
from soulstrike.fighter import FALL_FRAMES
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def duelo(a="atirador", b="guerreiro"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))])
    match = BattleMatch(g, g.session)
    match.intro = 0
    p1, p2 = match.fighters
    inp = FakeInput()
    match.controllers.clear()
    match.controllers[p1] = inp
    p1.x, p1.y, p2.x, p2.y = 400, 800, 900, 800
    return match, p1, p2, inp


class ParedesTest(unittest.TestCase):
    def test_paredes_ficam_prontas_ao_criar_o_mapa(self):
        g = game()
        for key in ("calabouco", "floresta", "templo_gelado", "campo_futebol"):
            arena = Arena(MAPS_BY_KEY[key], g.assets)
            for wall in arena.walls:
                if wall.visible and wall.image is None:
                    self.assertIsNotNone(wall._drawn, key)
                    self.assertGreaterEqual(wall._drawn.get_height(), wall.rect.h)

    def test_parede_pronta_igual_a_desenhada(self):
        g = game()
        for key in ("campo_futebol",):
            arena = Arena(MAPS_BY_KEY[key], g.assets)
            for wall in arena.walls:
                if not wall.visible or wall.image is not None:
                    continue
                r = wall.rect
                fresh = pygame.Surface((r.w + 20, r.h + 26))
                fresh.fill((1, 2, 3))
                wall.style.draw(fresh, pygame.Rect(10, 10, r.w, r.h))
                cached = pygame.Surface(fresh.get_size())
                cached.fill((1, 2, 3))

                class Cam:
                    x, y = r.x - 10, r.y - 10
                wall.draw(cached, Cam)
                self.assertEqual(pygame.image.tobytes(fresh, "RGB"), pygame.image.tobytes(cached, "RGB"), key)
                break

    def test_parede_fora_da_camera_nao_e_desenhada(self):
        g = game()
        arena = Arena(MAPS_BY_KEY["floresta"], g.assets)
        drawn = []
        for wall in arena.walls:
            wall.draw = (lambda w: (lambda surf, cam: drawn.append(w)))(wall)

        class Cam:
            x, y = 0, 0
        arena.draw_walls(pygame.Surface((400, 300)), Cam)
        self.assertTrue(drawn)
        self.assertLess(len(drawn), len([w for w in arena.walls if w.visible]))
        self.assertTrue(all(w.rect.left < 400 and w.rect.top < 320 for w in drawn))


THEMED = [m.key for m in MAPS if m.scenery in THEMED_MAPS]       # inclusive a Lag Lobby (capítulo 2)


class CenarioTest(unittest.TestCase):
    def test_mapas_com_cenario_proprio(self):
        g = game()
        for key in THEMED:
            arena = Arena(MAPS_BY_KEY[key], g.assets)
            # chão pintado (não é mais o xadrez de duas cores)
            colors = {arena.floor.get_at((x, y))[:3] for x in range(0, arena.width, 37) for y in range(0, arena.height, 41)}
            self.assertGreater(len(colors), 30, key)
            view = pygame.Surface((960, 540))

            class Cam:
                x, y = 300, 300
            for frame in (0, 10, 200):
                arena.draw_ambience(view, Cam, frame, "ground")
                arena.draw_ambience(view, Cam, frame, "air")

    def test_mapa_com_arte_fica_igual(self):
        g = game()
        arena = Arena(MAPS_BY_KEY["arena_classica"], g.assets)
        self.assertEqual(type(arena.ambience).__name__, "Ambience")

    def test_cenario_nao_muda_as_paredes(self):
        g = game()
        for key in THEMED:
            arena = Arena(MAPS_BY_KEY[key], g.assets)
            rects = [tuple(w.rect) for w in arena.walls if w.visible]
            self.assertEqual(rects, [tuple(r) for r in MAPS_BY_KEY[key].walls])


class DirecaoTest(unittest.TestCase):
    def test_diagonal_com_o_polegar_tremendo_nao_pisca(self):
        match, p1, _, _ = duelo()
        flips, last = 0, p1._direction()
        for k in range(120):
            wobble = 0.05 if k % 2 else -0.05
            p1.facing = (0.707 + wobble, 0.707 - wobble)
            d = p1._direction()
            flips += d != last
            last = d
        self.assertLessEqual(flips, 1)

    def test_virada_clara_troca_na_hora(self):
        match, p1, _, _ = duelo()
        p1.facing = (1.0, 0.0)
        self.assertEqual(p1._direction(), "direita")
        p1.facing = (-1.0, 0.0)
        self.assertEqual(p1._direction(), "esquerda")
        p1.facing = (0.2, -0.98)
        self.assertEqual(p1._direction(), "costas")
        p1.facing = (0.0, 1.0)
        self.assertEqual(p1._direction(), "frente")

    def test_andar_e_atirar_continua_olhando_para_o_alvo(self):
        match, p1, p2, inp = duelo()
        inp.stick = (0.0, -1.0)
        inp.hold("attack")
        seen = []
        for _ in range(60):
            match.update()
            inp.end_frame()
            seen.append(p1._direction())
        self.assertEqual(set(seen[1:]), {"direita"})
        inp.release("attack")
        run(match, 60, [inp])
        self.assertEqual(p1._direction(), "costas")      # parou de atirar: volta a olhar para onde anda

    def test_campanha_sem_alvo_atira_para_onde_anda(self):
        from soulstrike.campaign import CampaignMatch, CampaignRun
        g = game()
        g.session = Session("campaign", [SlotSetup(1, char=KEYS.index("atirador"))])
        m = CampaignMatch(g, CampaignRun(g.session))
        f = m.players[0]
        inp = FakeInput()
        m.controllers[f] = inp
        m.state, m.state_timer, m.banner = "fight", 0, None
        f.facing = (1.0, 0.0)
        inp.stick = (0.0, 1.0)
        inp.hold("attack")
        m._human(f, inp)
        self.assertTrue(m.bullets)
        b = m.bullets[-1]
        self.assertGreater(b.vy, abs(b.vx))


class CameraTest(unittest.TestCase):
    def test_zoom_so_em_degraus(self):
        cam = Camera((2000, 1400), 0.6)
        self.assertEqual(cam.levels, [Fraction(1), Fraction(3, 4), Fraction(3, 5)])
        for spread in (100, 500, 900, 1300, 300, 50):
            for _ in range(80):
                cam.focus([(800, 700), (800 + spread, 700)])
            self.assertIn(Fraction(cam.zoom).limit_denominator(10), cam.levels)
            self.assertTrue(cam.settled)

    def test_posicao_encaixa_na_grade_do_zoom(self):
        cam = Camera((2000, 1400), 0.6)
        for _ in range(100):
            cam.focus([(700, 700), (1700, 700)])
        self.assertEqual(cam.level, Fraction(3, 5))
        cam.x, cam.y = 103.7, 211.2
        cam.begin()
        self.assertEqual(cam.x % 5, 0)
        self.assertEqual(cam.y % 5, 0)
        self.assertEqual(cam.view_size, (1600, 900))

    def test_nao_fica_indo_e_voltando_na_fronteira(self):
        cam = Camera((2000, 1400), 0.6)
        changes, last = 0, None
        for k in range(400):
            gap = 620 + (6 if k % 20 < 10 else -6)       # jogadores andando bem na divisa entre dois degraus
            cam.focus([(600, 700), (600 + gap, 700)])
            if cam.level != last:
                changes += 1
                last = cam.level
        self.assertLessEqual(changes, 2)


class QuedaRespiracaoTest(unittest.TestCase):
    def test_queda_animada_e_imagem_guardada(self):
        match, p1, p2, _ = duelo()
        p2.hp = 0
        for _ in range(FALL_FRAMES + 2):
            p2.update(match)
            p2.draw(pygame.Surface((1600, 1200)), match.camera)
        self.assertGreaterEqual(p2.down_age, FALL_FRAMES)
        self.assertTrue(any(k[0] == "caido" for k in p2.sprites.cache))

    def test_inimigo_morto_some_aos_poucos(self):
        from soulstrike.campaign import CORPSE_FADE, CORPSE_FRAMES, CampaignMatch, CampaignRun
        g = game()
        g.session = Session("campaign", [SlotSetup(1)])
        m = CampaignMatch(g, CampaignRun(g.session))
        m.state, m.state_timer, m.banner = "fight", 0, None
        m._spawn("diabrete", 1600, 1200)
        e = m.enemies[-1]
        m.controllers.pop(e)
        m._spawn("diabrete", 1800, 1300)               # para a onda não acabar
        e.hp = 0
        fades = []
        for _ in range(CORPSE_FRAMES - 2):
            m.update()
            fades.append(e.fade)
        self.assertEqual(fades[0], 1.0)
        self.assertLess(fades[-1], 0.2)
        self.assertTrue(all(a >= b for a, b in zip(fades, fades[1:])))
        m.update()
        m.update()
        m.update()
        self.assertNotIn(e, m.fighters)
        self.assertGreater(CORPSE_FADE, 10)

    def test_parado_respira_andando_nao(self):
        match, p1, _, _ = duelo()
        cam = match.camera
        cam.begin()

        def shot():
            surf = pygame.Surface((1600, 1200))
            p1.draw(surf, cam)
            return pygame.image.tobytes(surf, "RGB")
        p1.moving = False
        p1.breath_phase = 0
        p1.age = 1
        a = shot()
        p1.age = 1 + 36
        b = shot()
        self.assertNotEqual(a, b)
        p1.moving = True
        p1.age = 1
        c = shot()
        p1.age = 1 + 36
        self.assertEqual(c, shot())

class CarregamentoTest(unittest.TestCase):
    def test_qr_codes_ficam_prontos_no_carregamento(self):
        from soulstrike.scenes.menus import LoadingScene
        g = game()
        scene = LoadingScene(g)
        for _ in scene._load():
            pass
        for slot in (1, 2, 3, 4):
            self.assertIn((f"{g.base_url}/?player={slot}", 4), g.assets._qr)


class ServidorRapidoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from soulstrike.net import server
        cls.server = server
        cls.srv = server.make_server("127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _req(self, conn, method, path, body=None):
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = conn.getresponse()
        return r.status, r.getheader("Content-Type") or "", r.read()

    def test_controle_inteiro_pela_mesma_conexao(self):
        from soulstrike.net.remote import hub
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        status, ctype, html = self._req(conn, "GET", "/?player=4")
        self.assertEqual(status, 200)
        self.assertIn(b"controller.js?v=", html)
        for path in ("/static/controller.js", "/static/controller.css", "/font.ttf", "/api/roster"):
            self.assertEqual(self._req(conn, "GET", path)[0], 200, path)
        self.assertEqual(self._req(conn, "POST", "/api/join", {"slot": 4, "token": "rapido"})[0], 200)
        hub.poll()
        status, _, _ = self._req(conn, "POST", "/api/input", {"slot": 4, "token": "rapido", "sid": "z", "seq": 1,
                                                              "held": ["attack"], "counts": {"attack": 1}})
        self.assertEqual(status, 204)
        held, pressed = hub.poll()
        self.assertIn("p4_attack", held)
        self.assertIn("p4_attack", pressed)
        status, ctype, body = self._req(conn, "GET", "/api/status?slot=4&token=rapido")
        self.assertEqual(status, 200)
        self.assertIn("json", ctype)
        self.assertTrue(json.loads(body)["me"]["owner"])
        self.assertEqual(self._req(conn, "POST", "/api/input", {"slot": 4, "token": "outro", "seq": 2})[0], 403)
        self.assertEqual(self._req(conn, "POST", "/api/input", {"slot": 4, "token": "rapido", "seq": "x"})[0], 400)
        self.assertEqual(self._req(conn, "GET", "/nao-existe")[0], 404)
        self._req(conn, "POST", "/api/leave", {"slot": 4, "token": "rapido"})
        conn.close()
        hub.poll()

    def test_segundo_jogo_na_mesma_porta_avisa(self):
        server = self.server
        with self.assertRaises(OSError):
            server.make_server("127.0.0.1", self.port)
        old_port, old_error = config.WEB_PORT, server.start_error
        try:
            config.WEB_PORT = self.port
            server.make_server.__defaults__ = ("0.0.0.0", self.port)
            server.start_in_background().join(timeout=5)
            self.assertIn(str(self.port), server.start_error)
        finally:
            config.WEB_PORT = old_port
            server.make_server.__defaults__ = ("0.0.0.0", old_port)
            server.start_error = old_error


class FutebolTrioTest(unittest.TestCase):
    def test_tres_pessoas_e_a_cpu_fecha_o_time(self):
        from soulstrike.scenes.select import CharSelectScene, LobbyScene
        g = game()
        g.session = Session("soccer2", [SlotSetup(1)] + [SlotSetup(s, cpu=True) for s in (2, 3, 4)])
        lobby = LobbyScene(g)
        self.assertEqual(lobby.joined, {1})
        from soulstrike.net.remote import hub
        real = g.inputs
        fake = {s: FakeInput() for s in (1, 2, 3, 4)}
        g.inputs = fake
        hub.join(3, "trio")                     # P3 conectou o celular
        try:
            fake[2].tap("confirm")              # P2 entra pelo teclado
            lobby.update()
            self.assertEqual(lobby.joined, {1, 2, 3})
            lobby._continue()
            self.assertEqual([s.cpu for s in g.session.slots], [False, False, False, True])
            select = g.scene
            self.assertIsInstance(select, CharSelectScene)
            card = {c.slot: c for c in select.cards}
            self.assertTrue(card[4].ready)              # a CPU já vem pronta
            self.assertFalse(card[2].setup.cpu)
        finally:
            g.inputs = real
            hub.leave(3, "trio")

    def test_p2_assume_e_devolve_a_vaga_da_cpu(self):
        from soulstrike.scenes.select import CharSelectScene
        g = game()
        g.session = Session("soccer2", [SlotSetup(1)] + [SlotSetup(s, cpu=True) for s in (2, 3, 4)])
        scene = CharSelectScene(g)
        real = g.inputs
        fake = {s: FakeInput() for s in (1, 2, 3, 4)}
        g.inputs = fake
        try:
            p2 = next(c for c in scene.cards if c.slot == 2)
            fake[2].tap("confirm")
            scene.update()
            self.assertFalse(p2.setup.cpu)
            self.assertFalse(p2.ready)          # o mesmo toque não confirma o personagem
            fake[2].end_frame()
            fake[2].tap("cancel")
            scene.update()
            self.assertTrue(p2.setup.cpu)
            self.assertTrue(p2.ready)
        finally:
            g.inputs = real


if __name__ == "__main__":
    unittest.main()
