"""Munição e armas exclusivas: pente, recarga, item de munição, arco que tensiona e o
projétil próprio de cada arma (flecha, granada, shuriken que ricocheteia, corrente...)."""
import unittest

from apoio import FakeInput, game

from soulstrike import config, projectiles as P
from soulstrike.ai import FighterAI
from soulstrike.data import CHARACTERS, FIGHTERS
from soulstrike.entities import Explosion, Pickup
from soulstrike.fighter import BOW_FULL, IDLE_RELOAD
from soulstrike.matches import BattleMatch
from soulstrike.net.remote import hub
from soulstrike.session import Session, SlotSetup
from soulstrike.upgrades import UPGRADES

KEYS = [c.key for c in CHARACTERS]


def duelo(a="atirador", b="tanque", map_key="arena_classica"):
    g = game()
    g.session = Session("duel", [SlotSetup(1, char=KEYS.index(a)), SlotSetup(2, char=KEYS.index(b))],
                        map_key=map_key)
    match = BattleMatch(g, g.session)
    match.intro = 0
    p1, p2 = match.fighters
    inputs = {}
    for f in match.fighters:
        inputs[f] = match.controllers[f] = FakeInput()
    p1.x, p1.y, p2.x, p2.y = 400, 760, 1000, 760         # linha livre de paredes
    return match, p1, p2, inputs


def passo(match, inputs, frames=1):
    """Avança ``frames`` quadros de jogo (as pausas de impacto não contam)."""
    target = match.frame + frames
    for _ in range(frames * 4):
        if match.frame >= target:
            break
        before = match.frame
        match.update()
        if match.frame != before:
            for inp in inputs.values():
                inp.end_frame()


def atirar(match, f, target, inputs, shots):
    """Segura o ataque até sair ``shots`` tiros (ou acabar a munição)."""
    fired = 0
    for _ in range(400):
        before = f.ammo
        inputs[f].hold("attack")
        passo(match, inputs)
        if f.ammo < before:
            fired += 1
            if fired >= shots:
                break
    inputs[f].release("attack")
    return fired


class PenteTest(unittest.TestCase):
    def test_tiro_gasta_e_pente_vazio_recarrega(self):
        match, p1, p2, inputs = duelo()
        self.assertEqual(p1.ammo, p1.mag)
        self.assertEqual(atirar(match, p1, p2, inputs, p1.mag), p1.mag)
        self.assertEqual(p1.ammo, 0)
        self.assertTrue(p1.reloading)
        # sem munição não sai tiro
        count = len(match.bullets)
        p1.attack_cd = 0
        self.assertFalse(p1.attack(match, p2))
        self.assertEqual(len(match.bullets), count)
        passo(match, inputs, p1.reload_total + 2)
        self.assertFalse(p1.reloading)
        self.assertEqual(p1.ammo, p1.mag)

    def test_recarrega_sozinho_parado(self):
        match, p1, p2, inputs = duelo()
        atirar(match, p1, p2, inputs, 2)
        self.assertEqual(p1.ammo, p1.mag - 2)
        passo(match, inputs, IDLE_RELOAD + 3)
        self.assertTrue(p1.reloading)
        passo(match, inputs, p1.reload_total + 2)
        self.assertEqual(p1.ammo, p1.mag)

    def test_atirar_cancela_a_recarga(self):
        match, p1, p2, inputs = duelo()
        atirar(match, p1, p2, inputs, 3)
        self.assertTrue(p1.start_reload())
        p1.attack_cd = 0
        self.assertTrue(p1.attack(match, p2))
        self.assertFalse(p1.reloading)
        self.assertEqual(p1.ammo, p1.mag - 4)

    def test_item_de_municao_da_pente_extra(self):
        match, p1, p2, inputs = duelo()
        atirar(match, p1, p2, inputs, p1.mag)
        self.assertTrue(p1.reloading)
        Pickup("municao", p1.x, p1.y).apply(p1, match)
        self.assertFalse(p1.reloading)
        self.assertEqual(p1.ammo, p1.mag * config.AMMO_PICKUP_EXTRA)

    def test_novo_round_enche_o_pente(self):
        match, p1, p2, inputs = duelo()
        atirar(match, p1, p2, inputs, 5)
        p2.hp = 0
        passo(match, inputs, config.ROUND_END_FRAMES + 30)
        self.assertEqual(match.round_no, 2)
        self.assertEqual(p1.ammo, p1.mag)

    def test_arma_magica_volta_sozinha(self):
        match, p1, p2, inputs = duelo("fantasma")
        gun = p1.gun
        self.assertGreater(gun.regen, 0)
        atirar(match, p1, p2, inputs, 3)
        self.assertEqual(p1.ammo, p1.mag - 3)
        self.assertFalse(p1.start_reload())               # não recarrega: a carga volta
        passo(match, inputs, gun.regen * 3 + 5)
        self.assertEqual(p1.ammo, p1.mag)

    def test_corpo_a_corpo_nao_gasta(self):
        match, p1, p2, inputs = duelo()
        p1.switch_weapon()
        p1.attack_cd = 0
        p2.x = p1.x + 30
        p1.attack(match, p2)
        self.assertEqual(p1.ammo, p1.mag)

    def test_todos_os_herois_tem_pente(self):
        for c in FIGHTERS:
            gun = next(w for w in c.weapons if not w.is_melee)
            self.assertGreater(gun.mag, 0, c.name)
            self.assertTrue(gun.reload > 0 or gun.regen > 0, c.name)
            self.assertIn(gun.style, P.PROJECTILES, c.name)
            self.assertTrue(gun.note, c.name)


class ArcoTest(unittest.TestCase):
    def test_segurar_tensiona_e_soltar_atira(self):
        match, p1, p2, inputs = duelo("guerreiro")
        inputs[p1].hold("attack")
        passo(match, inputs, 10)
        self.assertGreater(p1.bow_draw, 0)
        self.assertEqual(match.bullets, [])
        self.assertEqual(p1.weapon_art_name(), "Arco Puxado")
        inputs[p1].release("attack")
        passo(match, inputs, 1)
        self.assertEqual(p1.bow_draw, 0)
        arrows = [b for b in match.bullets if isinstance(b, P.Arrow)]
        self.assertEqual(len(arrows), 1)
        self.assertFalse(arrows[0].charged)
        self.assertEqual(p1.ammo, p1.mag - 1)
        self.assertEqual(p1.weapon_art_name(), "Arco Vazio")      # acabou de soltar

    def test_tenso_solta_sozinho_mais_forte_e_atravessa(self):
        match, p1, p2, inputs = duelo("guerreiro")
        inputs[p1].hold("attack")
        passo(match, inputs, BOW_FULL + 2)
        arrows = [b for b in match.bullets if isinstance(b, P.Arrow)]
        self.assertEqual(len(arrows), 1)
        self.assertTrue(arrows[0].charged)
        self.assertEqual(arrows[0].pierce, p1.pierce + 1)
        self.assertGreater(arrows[0].damage, p1.gun.damage)

    def test_tensionando_anda_mais_devagar(self):
        match, p1, p2, inputs = duelo("guerreiro")
        normal = p1.max_speed
        inputs[p1].hold("attack")
        passo(match, inputs, 4)
        self.assertLess(p1.max_speed, normal)

    def test_flecha_finca_na_parede(self):
        match, p1, p2, inputs = duelo("guerreiro")
        wall = match.arena.walls[0]
        p1.x, p1.y = wall.rect.right + 60, wall.rect.centery
        match.spawn_projectile(p1, p1.gun, (-1.0, 0.0), 10, None)
        passo(match, inputs, 20)
        self.assertTrue(any(isinstance(e, P.Stuck) for e in match.effects))


class ProjeteisTest(unittest.TestCase):
    EXPECTED = {"guerreiro": P.Arrow, "atirador": P.Tracer, "tanque": P.Spear, "ninja": P.ShurikenStar,
                "velocista": P.ThrowingStar, "aryel": P.Grenade, "fantasma": P.Orb, "tita": P.ChainBall,
                "pirata": P.LeadBall, "geada": P.IceShard}

    def test_cada_arma_tem_seu_projetil(self):
        match, p1, p2, inputs = duelo()
        for key, cls in self.EXPECTED.items():
            stats = CHARACTERS[KEYS.index(key)]
            proj = match.spawn_projectile(p1, stats.weapons[0], (1.0, 0.0), 10, p2)
            self.assertIsInstance(proj, cls, key)

    def test_granada_passa_por_cima_da_parede_e_explode_onde_cai(self):
        match, p1, p2, inputs = duelo("aryel")
        wall = next(w for w in match.arena.walls if w.visible and w.rect.w <= 60 and w.rect.h >= 60)
        p1.x, p1.y = wall.rect.left - 120, wall.rect.centery
        p2.x, p2.y = wall.rect.right + 120, wall.rect.centery
        proj = match.spawn_projectile(p1, p1.gun, (1.0, 0.0), 12, p2)
        self.assertGreater(proj.end[0], wall.rect.right)
        for _ in range(proj.flight + 2):
            match._update_bullets()
            for e in match.effects:
                e.update(match)
        self.assertTrue(any(isinstance(e, Explosion) for e in match.effects))
        self.assertLess(p2.hp, p2.max_hp)

    def test_shuriken_ricocheteia_uma_vez(self):
        match, p1, p2, inputs = duelo("ninja")
        wall = match.arena.walls[0]
        p1.x, p1.y = wall.rect.right + 60, wall.rect.centery
        proj = match.spawn_projectile(p1, p1.gun, (-1.0, 0.0), 9, None)
        for _ in range(12):
            match._update_bullets()
        self.assertTrue(proj.alive)
        self.assertGreater(proj.vx, 0)                    # voltou
        self.assertEqual(proj.bounces, 0)

    def test_corrente_atordoa_e_volta(self):
        match, p1, p2, inputs = duelo("tita")
        p2.x = p1.x + 120
        ball = match.spawn_projectile(p1, p1.gun, (1.0, 0.0), 12, p2)
        self.assertIsNone(p1.weapon_art_name())             # a bola saiu da mão
        for _ in range(12):
            match._update_bullets()
        self.assertLess(p2.hp, p2.max_hp)
        self.assertTrue(p2.stunned)
        self.assertTrue(ball.returning)
        for _ in range(40):
            match._update_bullets()
        self.assertFalse(ball.alive)
        self.assertEqual(p1.weapon_art_name(), "Corrente")

    def test_cristal_deixa_lento(self):
        match, p1, p2, inputs = duelo("geada")
        p2.x = p1.x + 150
        match.spawn_projectile(p1, p1.gun, (1.0, 0.0), 9, p2)
        for _ in range(20):
            match._update_bullets()
        self.assertGreater(p2.slow_timer, 0)

    def test_estrela_da_embalo(self):
        match, p1, p2, inputs = duelo("velocista")
        p2.x = p1.x + 150
        normal = p1.max_speed
        match.spawn_projectile(p1, p1.gun, (1.0, 0.0), 9, p2)
        for _ in range(20):
            match._update_bullets()
        self.assertGreater(p1.haste_timer, 0)
        self.assertGreater(p1.max_speed, normal)

    def test_orbe_persegue_e_atravessa_parede(self):
        match, p1, p2, inputs = duelo("fantasma")
        wall = next(w for w in match.arena.walls if w.visible and w.rect.w <= 60 and w.rect.h >= 60)
        p1.x, p1.y = wall.rect.left - 80, wall.rect.centery
        p2.x, p2.y = wall.rect.right + 80, wall.rect.centery + 50
        match.spawn_projectile(p1, p1.gun, (1.0, 0.0), 10, p2)
        for _ in range(60):
            match._update_bullets()
        self.assertLess(p2.hp, p2.max_hp)

    def test_lanca_some_da_mao_sem_municao(self):
        match, p1, p2, inputs = duelo("tanque")
        self.assertEqual(p1.weapon_art_name(), "Lança")
        p1.ammo = 0
        self.assertIsNone(p1.weapon_art_name())


class CpuTest(unittest.TestCase):
    def test_cpu_troca_para_perto_sem_municao_e_volta(self):
        match, p1, p2, inputs = duelo("atirador", "tanque")
        ai = FighterAI("dificil")
        match.controllers[p1] = ai
        p1.ammo = 0
        p1.start_reload()
        p2.x = p1.x + 80
        passo(match, inputs, 20)
        self.assertTrue(p1.weapon.is_melee)
        p1.reload_timer = 1
        p2.x, p2.y = p1.x + 500, p1.y
        passo(match, inputs, 30)
        self.assertFalse(p1.weapon.is_melee)

    def test_cpu_quer_municao_quando_esta_acabando(self):
        match, p1, p2, inputs = duelo()
        match.pickups.append(Pickup("municao", p1.x + 100, p1.y))
        p1.ammo = p1.mag
        self.assertIsNone(FighterAI._wanted_pickup(p1, p2, match))
        p1.ammo = 1
        self.assertIsNotNone(FighterAI._wanted_pickup(p1, p2, match))


class OutrosTest(unittest.TestCase):
    def test_melhoria_de_municao(self):
        match, p1, p2, inputs = duelo()
        base = p1.mag
        UPGRADES["municao"].apply(p1)
        self.assertEqual(p1.mag, round(base * 1.5))
        self.assertEqual(p1.ammo, p1.mag)

    def test_celular_recebe_a_municao(self):
        match, p1, p2, inputs = duelo()
        hub.join(1, "pente")
        try:
            atirar(match, p1, p2, inputs, 2)
            passo(match, inputs, 6)
            me = hub.status(1, "pente")["me"]
            self.assertEqual(me["mag"], p1.mag)
            self.assertEqual(me["ammo"], p1.ammo)
        finally:
            hub.leave(1, "pente")


if __name__ == "__main__":
    unittest.main()


class CampanhaTest(unittest.TestCase):
    def test_todas_as_armas_atiram_sem_inimigo_por_perto(self):
        """Na campanha, sem alvo o tiro vai para onde o jogador olha (o alvo é só um ponto)."""
        from test_campanha import campanha, pular_intro
        keys = [c.key for c in FIGHTERS if c.key != "aryel_corrompido"]
        for i in range(0, len(keys), 2):
            match, inputs = campanha(tuple(keys[i:i + 2]))
            pular_intro(match)
            match.enemies.clear()
            for inp in inputs.values():
                inp.hold("attack")
            for _ in range(90):
                match.update()
            for f in match.players:
                self.assertLess(f.ammo, f.mag + 1, f.stats.name)
            self.assertTrue(match.bullets or any(f.reloading for f in match.players))
