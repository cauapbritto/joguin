"""Pirata e Geada: gancho que puxa, nevasca que deixa lento, poderes do futebol e arquivos."""
import json
import unittest

from apoio import futebol, game, run

from soulstrike import config
from soulstrike.data import CHARACTERS
from soulstrike.entities import FrostNova, Hook
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup

KEYS = [c.key for c in CHARACTERS]


def _duelo(a, b):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))])
    match = BattleMatch(g, g.session)
    for f in match.fighters:
        match.controllers[f] = None
    match.controllers.clear()                  # ninguém se mexe sozinho
    p1, p2 = match.fighters
    p1.x, p1.y, p2.x, p2.y = 400, 450, 760, 450
    return match, p1, p2


def _passo(match, frames):
    for _ in range(frames):
        match.frame += 1
        for f in match.fighters:
            f.update(match)
        match._update_bullets()
        for e in match.effects:
            e.update(match)
        match.effects = [e for e in match.effects if e.alive]


class GanchoTest(unittest.TestCase):
    def test_gancho_puxa_e_atordoa(self):
        match, pirata, alvo = _duelo("pirata", "guerreiro")
        self.assertTrue(pirata.use_ability(match, alvo))
        self.assertTrue(any(isinstance(b, Hook) for b in match.bullets))
        _passo(match, 40)
        self.assertLess(pirata.distance_to(alvo), 80)      # veio para o alcance do sabre
        self.assertLess(alvo.hp, alvo.stats.max_hp)

    def test_gancho_longe_demais_nao_pega(self):
        match, pirata, alvo = _duelo("pirata", "guerreiro")
        alvo.x = 400 + Hook.SPEED * Hook.RANGE_FRAMES + 150
        pirata.use_ability(match, alvo)
        _passo(match, 50)
        self.assertEqual(alvo.hp, alvo.stats.max_hp)

    def test_invulneravel_nao_e_puxado(self):
        match, pirata, alvo = _duelo("pirata", "tita")
        alvo.invulnerable_timer = 120
        x0 = alvo.x
        pirata.use_ability(match, alvo)
        _passo(match, 40)
        self.assertGreater(alvo.x, x0 - 30)


class NevascaTest(unittest.TestCase):
    def test_nevasca_deixa_lento_quem_esta_perto(self):
        match, geada, alvo = _duelo("geada", "velocista")
        alvo.x = geada.x + 120
        normal = alvo.max_speed
        geada.use_ability(match, alvo)
        self.assertTrue(any(isinstance(e, FrostNova) for e in match.effects))
        _passo(match, 2)
        self.assertGreater(alvo.slow_timer, 0)
        self.assertAlmostEqual(alvo.max_speed, normal * config.SLOW_MULT)
        self.assertLess(alvo.hp, alvo.stats.max_hp)

    def test_nevasca_nao_pega_quem_esta_longe(self):
        match, geada, alvo = _duelo("geada", "velocista")
        alvo.x = geada.x + 300
        geada.use_ability(match, alvo)
        _passo(match, 2)
        self.assertEqual(alvo.slow_timer, 0)

    def test_lentidao_passa(self):
        match, geada, alvo = _duelo("geada", "velocista")
        alvo.x = geada.x + 100
        geada.use_ability(match, alvo)
        _passo(match, int(2.5 * config.FPS) + 5)
        self.assertEqual(alvo.slow_timer, 0)


class FutebolNovosTest(unittest.TestCase):
    def test_gancho_tira_a_bola_do_adversario(self):
        match, _ = futebol(chars=(KEYS.index("pirata"), 2))
        pirata, rival = match.fighters
        pirata.x, pirata.y = 600, 450
        rival.x, rival.y = 850, 450
        match.ball.x, match.ball.y = 880, 450
        run(match, 3)
        self.assertIs(match.possessor, rival)
        self.assertTrue(match.use_power(pirata))
        run(match, 40)
        self.assertIs(match.possessor, pirata)

    def test_congelar_deixa_os_adversarios_lentos(self):
        match, _ = futebol(chars=(KEYS.index("geada"), 2))
        geada, rival = match.fighters
        geada.x, geada.y = 600, 450
        rival.x, rival.y = 760, 450
        self.assertTrue(match.use_power(geada))
        self.assertGreater(rival.slow_timer, 0)


class ArquivosTest(unittest.TestCase):
    def test_todo_personagem_tem_sprites_e_armas(self):
        grips = json.loads((config.ASSETS_DIR / "weapons" / "grips.json").read_text(encoding="utf-8"))
        for c in CHARACTERS:
            for d in ("frente", "costas", "direita", "esquerda"):
                self.assertTrue((config.CHAR_DIR / f"{c.sprite}{d}.png").is_file(), (c.name, d))
            for w in c.weapons:
                self.assertIn(w.name, grips, (c.name, w.name))

    def test_celular_recebe_os_dez(self):
        from soulstrike.net import server
        roster = server.app.test_client().get("/api/roster").get_json()
        names = [r["name"] for r in roster]
        self.assertIn("Pirata", names)
        self.assertIn("Geada", names)
        from soulstrike.data import roster as available
        self.assertEqual(len(roster), len(available()))


if __name__ == "__main__":
    unittest.main()
