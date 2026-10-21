"""Testes automáticos. Rodam sem abrir janela:  python -m unittest discover tests"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from soulstrike import config  # noqa: E402
from soulstrike.arena import MAPS, Arena  # noqa: E402
from soulstrike.data import CHARACTERS  # noqa: E402
from soulstrike.entities import push_circle_out  # noqa: E402
from soulstrike.matches import BattleMatch, SoccerMatch  # noqa: E402
from soulstrike.net.remote import RemoteHub  # noqa: E402
from soulstrike.session import Session, SlotSetup  # noqa: E402



def game():
    from apoio import game as shared     # uma janela só para todos os testes
    return shared()


class RemoteHubTest(unittest.TestCase):
    def test_toque_rapido_nao_se_perde(self):
        hub = RemoteHub()
        hub.press("p1_attack")
        hub.release("p1_attack")          # soltou antes do jogo ler
        held, pressed = hub.poll()
        self.assertIn("p1_attack", pressed)
        self.assertNotIn("p1_attack", held)
        self.assertEqual(hub.poll()[1], frozenset())

    def test_comando_desconhecido_e_ignorado(self):
        hub = RemoteHub()
        hub.press("p9_hack")
        self.assertEqual(hub.poll(), (frozenset(), frozenset()))

    def test_vaga_e_do_primeiro_celular(self):
        hub = RemoteHub()
        self.assertTrue(hub.join(3, "a"))
        self.assertFalse(hub.join(3, "b"))
        self.assertTrue(hub.join(3, "a"))   # recarregar a página não trava a vaga
        hub.leave(3, "a")
        self.assertTrue(hub.join(3, "b"))

    def test_analogico_do_celular(self):
        hub = RemoteHub()
        hub.set_axis(1, 3.0, 4.0)                 # é normalizado
        x, y = hub.axes()[1]
        self.assertAlmostEqual(x, 0.6)
        self.assertAlmostEqual(y, 0.8)
        hub.release_slot(1)                       # celular saiu: para de andar
        self.assertNotIn(1, hub.axes())

    def test_soltar_vaga_nao_afeta_outros(self):
        hub = RemoteHub()
        hub.press("p1_up")
        hub.press("p2_up")
        hub.release_slot(1)
        held, _ = hub.poll()
        self.assertEqual(held, {"p2_up"})


class ColisaoTest(unittest.TestCase):
    def test_circulo_sai_da_parede(self):
        rect = pygame.Rect(100, 100, 50, 50)
        x, y, nx, ny = push_circle_out(95, 125, 15, rect)
        self.assertAlmostEqual(x, 85)
        self.assertEqual((nx, ny), (-1, 0))
        self.assertIsNone(push_circle_out(60, 125, 15, rect))

    def test_pontos_de_partida_livres(self):
        g = game()
        for cfg in MAPS:
            arena = Arena(cfg, g.assets)
            for x, y in cfg.spawns:
                self.assertTrue(arena.is_free(*arena.free_spot(x, y, config.PLAYER_RADIUS + 2), config.PLAYER_RADIUS),
                                f"{cfg.key} {(x, y)}")


class PartidaTest(unittest.TestCase):
    def test_todos_os_personagens_lutam(self):
        g = game()
        for i, stats in enumerate(CHARACTERS):
            if stats.soccer_only:
                continue                                  # craque do futebol não luta
            g.session = Session("cpu", [SlotSetup(1, char=i, cpu=True), SlotSetup(2, char=(i + 3) % 8, cpu=True)],
                                difficulty="dificil")
            match = BattleMatch(g, g.session)
            fighter = match.fighters[0]
            fighter.use_ability(match, match.fighters[1])
            for _ in range(240):
                match.update()
                if match.finished:
                    break
            match.draw(g.screen, g.ui)
            for f in match.fighters:
                self.assertFalse(any(w.overlaps_circle(f.x, f.y, f.radius - 2) for w in match.arena.walls),
                                 f"{f.stats.name} preso na parede")

    def test_dano_e_contado_uma_vez_so(self):
        g = game()
        g.session = Session("cpu", [SlotSetup(1, char=5, cpu=True), SlotSetup(2, char=2, cpu=True)])
        match = BattleMatch(g, g.session)
        a, b = match.fighters
        b.x, b.y = a.x + 60, a.y
        hp = b.hp
        match.spawn_bullet(a, 1, 0, 6, 12, explosive=True)
        for _ in range(30):
            match._update_bullets()
            for e in match.effects:
                e.update(match)
        self.assertEqual(hp - b.hp, 12)

    def test_gol_da_vitoria_conta_uma_vez(self):
        g = game()
        g.session = Session("soccer1", [SlotSetup(1, cpu=True), SlotSetup(2, cpu=True)])
        match = SoccerMatch(g, g.session)
        match.score = [config.WIN_SCORE - 1, 0]
        ball = match.ball
        for _ in range(400):
            ball.x, ball.y, ball.vx, ball.vy = match.arena.width - 10, match.arena.height / 2, 0, 0
            match.update()
            if match.finished:
                break
        self.assertTrue(match.finished)
        self.assertEqual(match.score, [config.WIN_SCORE, 0])


def _futebol(chars=(4, 2)):
    from soulstrike.ai import SoccerAI

    class Parado(SoccerAI):
        def update(self, me, match):
            me.steer(0, 0)

    g = game()
    slots = [SlotSetup(i + 1, char=c, cpu=True) for i, c in enumerate(chars)]
    g.session = Session("soccer1" if len(chars) == 2 else "soccer2", slots)
    match = SoccerMatch(g, g.session)
    for f in match.fighters:
        match.controllers[f] = Parado()
    return match


class RoundsTest(unittest.TestCase):
    def test_melhor_de_tres(self):
        g = game()
        g.session = Session("cpu", [SlotSetup(1, char=0, cpu=True), SlotSetup(2, char=1, cpu=True)])
        match = BattleMatch(g, g.session)
        a, b = match.fighters
        for _ in range(config.ROUNDS_TO_WIN):
            match.intro = 0
            b.hp = 0
            for _ in range(config.ROUND_END_FRAMES + 60):
                match.update()
                if match.finished or match.intro:
                    break
        self.assertTrue(match.finished)
        self.assertEqual(match.result.score, (config.ROUNDS_TO_WIN, 0))

    def test_novo_round_restaura_vida(self):
        g = game()
        g.session = Session("cpu", [SlotSetup(1, char=0, cpu=True), SlotSetup(2, char=1, cpu=True)])
        match = BattleMatch(g, g.session)
        a, b = match.fighters
        match.intro = 0
        a.hp = 10
        b.hp = 0
        for _ in range(config.ROUND_END_FRAMES * 3):     # inclui a câmera lenta do K.O.
            match.update()
            if match.round_no == 2:
                break
        self.assertEqual(match.round_no, 2)
        self.assertEqual(a.hp, a.stats.max_hp)

    def test_item_de_vida(self):
        from soulstrike.entities import Pickup
        g = game()
        g.session = Session("cpu", [SlotSetup(1, char=0, cpu=True), SlotSetup(2, char=1, cpu=True)])
        match = BattleMatch(g, g.session)
        a = match.fighters[0]
        a.hp = 50
        match.pickups.append(Pickup("vida", a.x, a.y))
        match._update_pickups(active=False)
        self.assertEqual(a.hp, 50 + config.HEAL_AMOUNT)


class FutebolTest(unittest.TestCase):
    def test_chuta_correndo_com_a_bola(self):
        match = _futebol()
        p1 = match.fighters[0]
        p1.x, p1.y = 600, 450
        match.ball.x, match.ball.y = 630, 450
        for _ in range(40):
            p1.steer(1, 0)
            match.update()
        self.assertIs(match.possessor, p1)
        self.assertTrue(match.kick(p1, (1, 0)))
        self.assertGreater(match.ball.vx, 8)

    def test_passe_alto_passa_por_cima(self):
        match = _futebol((4, 2, 0, 7))
        p1, p2, p3, p4 = match.fighters
        p1.x, p1.y, p2.x, p2.y, p3.x, p3.y = 600, 450, 800, 450, 1000, 450
        p4.x, p4.y = 1400, 150
        match.ball.x, match.ball.y = 630, 450
        for _ in range(3):
            match.update()
        self.assertTrue(match.pass_ball(p1, high=True))
        heights = []
        for _ in range(90):
            match.update()
            if abs(match.ball.x - p2.x) < 12:
                heights.append(match.ball.z)
            if match.possessor is not None:
                break
        self.assertTrue(heights and min(heights) > config.BODY_HEIGHT)
        self.assertIs(match.possessor, p3)

    def test_bola_quica(self):
        match = _futebol()
        ball = match.ball
        ball.vx = 6
        ball.lift(6)
        peaks, last_z, rising = [], 0, True
        for _ in range(200):
            ball.update(match)
            if rising and ball.z < last_z:
                peaks.append(last_z)
            rising = ball.z >= last_z
            last_z = ball.z
        self.assertGreaterEqual(len(peaks), 2)
        self.assertGreater(peaks[0], peaks[1])
        self.assertEqual(ball.z, 0)

    def test_todos_os_poderes(self):
        from soulstrike.soccer_powers import SOCCER_POWERS
        for i, stats in enumerate(CHARACTERS):
            match = _futebol((i, 2))
            p1 = match.fighters[0]
            # o gancho do Pirata é para buscar a bola longe; os outros, com a bola no pé
            # (a antecipação do Paredão, com a bola solta longe dele, no próprio campo)
            gap = {"GanchoNaBola": 200, "Antecipacao": 300}.get(SOCCER_POWERS[stats.key].__name__, 25)
            if SOCCER_POWERS[stats.key].__name__ == "Enterrada":
                gx = match.goal_x(1 - p1.team)                # enterrada: perto da área adversária
                p1.x = gx - 400 if gx > p1.x else gx + 400
            match.ball.x, match.ball.y = p1.x + gap, p1.y
            if SOCCER_POWERS[stats.key].__name__ in ("Caneta",):
                p2 = match.fighters[1]
                p2.x, p2.y = p1.x + 110, p1.y            # caneta e cartão precisam de um adversário perto
            for _ in range(2):
                match.update()
            p1.facing = (1.0, 0.0)
            self.assertTrue(match.use_power(p1), SOCCER_POWERS[stats.key].name)
            for _ in range(60):
                match.update()


class ServidorTest(unittest.TestCase):
    def test_rotas(self):
        from soulstrike.net import server
        from soulstrike.net.remote import hub
        client = server.app.test_client()
        self.assertEqual(client.get("/").status_code, 200)
        from soulstrike.data import roster
        self.assertEqual(len(client.get("/api/roster").get_json()), len(CHARACTERS))   # o celular acha pelo índice
        self.assertTrue(client.post("/api/join", json={"slot": 4, "token": "t"}).get_json()["ok"])
        self.assertEqual(client.post("/api/join", json={"slot": 4, "token": "x"}).status_code, 409)
        client.post("/press/p4_attack")
        self.assertIn("p4_attack", hub.poll()[1])
        status = client.get("/api/status?slot=4&token=t").get_json()
        self.assertTrue(status["me"]["owner"])
        client.post("/api/leave", json={"slot": 4, "token": "t"})


if __name__ == "__main__":
    unittest.main()
