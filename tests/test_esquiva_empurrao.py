"""Esquiva perfeita (duelo e campanha) e empurrão no arremesso do basquete."""
import unittest

from apoio import game, run
from test_basquete import basquete

from soulstrike import config
from soulstrike import basketball as B
from soulstrike.data import CHARACTERS
from soulstrike.entities import Bullet
from soulstrike.matches import BattleMatch
from soulstrike.session import Session, SlotSetup
from soulstrike.training import DummyAI

KEYS = [c.key for c in CHARACTERS]


def duelo(a="guerreiro", b="atirador"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a), cpu=True), SlotSetup(2, char=KEYS.index(b), cpu=True)])
    match = BattleMatch(g, g.session)
    for f in match.fighters:
        match.controllers[f] = DummyAI()
    match.intro = 0
    return match


class EsquivaPerfeitaTest(unittest.TestCase):
    def test_recarga_maior(self):
        self.assertEqual(config.DASH_COOLDOWN, 60)

    def test_desviar_do_tiro_zera_a_recarga_e_carrega_a_habilidade(self):
        match = duelo()
        me, foe = match.fighters
        me.x, me.y = 400, 500
        me.ability_cd = me.ability_cooldown
        self.assertTrue(me.dash((0, 1)))
        match.bullets.append(Bullet(foe, me.x, me.y - 6, -1, 0, 10, 10, (255, 255, 255)))
        match._update_bullets()
        self.assertEqual(me.hp, me.max_hp)
        self.assertEqual(me.dash_cd, 0)
        self.assertLess(me.ability_cd, me.ability_cooldown)
        self.assertTrue(match.bullets)                  # o tiro passou por ele
        cd = me.ability_cd
        match.bullets.append(Bullet(foe, me.x, me.y - 6, -1, 0, 10, 10, (255, 255, 255)))
        me.dash_cd = 50
        match._update_bullets()
        self.assertEqual(me.dash_cd, 50)                # só uma vez por esquiva
        self.assertEqual(me.ability_cd, cd)

    def test_esquiva_a_toa_nao_recarrega(self):
        match = duelo()
        me = match.fighters[0]
        me.dash((1, 0))
        run(match, 20)
        self.assertGreater(me.dash_cd, 0)

    def test_desviar_do_golpe_de_perto(self):
        match = duelo("ninja", "guerreiro")
        me, foe = match.fighters
        me.x, me.y, foe.x, foe.y = 500, 500, 540, 500
        foe.facing = (-1.0, 0.0)
        me.dash((0, 1))
        self.assertFalse(me.take_damage(20, foe.x, foe.y, attacker=foe, match=match))
        self.assertEqual(me.dash_cd, 0)

    def test_imune_nao_conta(self):
        match = duelo()
        me, foe = match.fighters
        me.invulnerable_timer = 60
        me.dash((1, 0))
        me.take_damage(20, attacker=foe, match=match)
        self.assertGreater(me.dash_cd, 0)


class EmpurraoTest(unittest.TestCase):
    def preparar(self):
        match, _ = basquete()
        atk = next(f for f in match.fighters if f.team == 0)
        dfn = next(f for f in match.fighters if f.team == 1)
        atk.x, atk.y, atk.facing = 1000, 600, (1.0, 0.0)
        dfn.x, dfn.y = 1000, 650
        match.ball.reset(atk.x, atk.y)
        match._give(atk)
        match.start_shot(atk)
        self.assertTrue(atk.jump_shot)
        return match, atk, dfn

    def test_empurrao_encolhe_a_faixa_verde(self):
        match, atk, dfn = self.preparar()
        half = atk.shot_half
        match.steal(dfn)
        run(match, 4)
        self.assertAlmostEqual(atk.shot_half, half * B.PUSH_SHRINK)
        self.assertIs(match.holder, atk)               # empurrão não rouba a bola
        self.assertFalse(dfn.stunned)

    def test_quem_protege_segura_e_quem_empurra_fica_parado(self):
        match, atk, dfn = self.preparar()
        atk.protecting = True
        half = atk.shot_half
        match.steal(dfn)
        run(match, 2)
        self.assertEqual(atk.shot_half, half)
        self.assertTrue(dfn.stunned)

    def test_segundo_empurrao_nao_pega(self):
        match, atk, dfn = self.preparar()
        match.steal(dfn)
        run(match, 2)
        half = atk.shot_half
        dfn.steal_cd = 0
        dfn.stun_timer = 0
        match._push(dfn, atk)
        self.assertEqual(atk.shot_half, half)
        self.assertTrue(dfn.stunned)


if __name__ == "__main__":
    unittest.main()
