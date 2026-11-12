"""Armas novas: as 39 dos baús (5 únicas por fase), a Excalitora e as 7 de tiro de graça."""
import unittest

from test_armas_raras import campo, inimigo, passo

from soulstrike import energia, weapon_art
from soulstrike import tiros_novos as T
from soulstrike.armas_novas import FREE_NAMES
from soulstrike.data import FREE_GUNS, PHASE_RELICS, RARE_WEAPONS, common_weapon

def usar(match, p, alvo, frames=40):
    p.attack_cd = 0
    p.face(alvo)
    if p.weapon.special == "escudo":
        p.attack(match, alvo)
        return
    p.attack(match, alvo)
    passo(match, frames)


class TodasFuncionamTest(unittest.TestCase):
    def test_cada_arma_nova_acerta_alguem(self):
        for key in sorted({k for ks in PHASE_RELICS.values() for k in ks}):
            w = RARE_WEAPONS[key]
            if w.special == "escudo" or w.style == "drone_bolso":
                continue
            match, p = campo(key)
            d = 50 if w.is_melee else 120
            alvo = inimigo(match, "golem", p.x + d, p.y)
            alvo.hp = alvo.max_hp = 100000
            usar(match, p, alvo, 60)
            self.assertLess(alvo.hp, alvo.max_hp, key)
            self.assertIsNotNone(weapon_art.icon(w.name), key)

    def test_de_tiro_de_graca(self):
        self.assertEqual(len(FREE_GUNS), 7)
        match, p = campo("besta")
        for w in FREE_GUNS:
            self.assertIs(common_weapon(w.name), w)
            self.assertFalse(w.rare)
            self.assertEqual(energia.cost(p, w), 0, w.name)
            self.assertIsNotNone(weapon_art.icon(w.name), w.name)
        self.assertEqual(FREE_NAMES, {w.name for w in FREE_GUNS})

    def test_de_tiro_de_graca_cai_dos_inimigos(self):
        match, p = campo("besta")
        names = set()
        for _ in range(80):
            e = inimigo(match, "esqueleto", 900, 600)
            match._drop_hero_weapon(e)
            names |= {g.weapon.name for g in match.ground}
            match.ground.clear()
        self.assertTrue(names & FREE_NAMES)


class EfeitosTest(unittest.TestCase):
    def test_excalitora_alcanca_longe_e_deixa_lento(self):
        match, p = campo("excalitora")
        alvo = inimigo(match, "golem", p.x + 180, p.y)
        alvo.hp = alvo.max_hp = 100000
        usar(match, p, alvo, 1)
        self.assertLess(alvo.hp, alvo.max_hp)
        self.assertEqual(T.speed_mult(p), 0.75)
        self.assertEqual(p.energy, p.energy_max)               # não gasta
        p.weapon_index = 0
        self.assertEqual(T.speed_mult(p), 1.0)

    def test_sino_assusta_todo_mundo_em_volta(self):
        match, p = campo("sino_funebre")
        a = inimigo(match, "esqueleto", p.x + 100, p.y)
        b = inimigo(match, "esqueleto", p.x - 100, p.y)
        for e in (a, b):
            e.hp = e.max_hp = 1000
        usar(match, p, a, 1)
        self.assertTrue(a.hp < 1000 and b.hp < 1000)
        self.assertTrue(a.fear_timer > 0 and b.fear_timer > 0)

    def test_sugador_devolve_energia(self):
        match, p = campo("sugador_almas")
        p.energy = 10
        alvo = inimigo(match, "golem", p.x + 100, p.y)
        alvo.hp = alvo.max_hp = 100000
        usar(match, p, alvo, 20)
        self.assertGreater(p.energy, 10)

    def test_bateria_da_energia_no_abate(self):
        match, p = campo("bateria_portatil")
        p.energy = 0
        alvo = inimigo(match, "esqueleto", p.x + 40, p.y)
        alvo.hp = 1
        usar(match, p, alvo, 1)
        self.assertEqual(p.energy, 6 + energia.MELEE_KILL)

    def test_leque_do_fax_solta_cinco_folhas(self):
        match, p = campo("fax")
        n = len(match.bullets)
        match.spawn_projectile(p, p.weapon, (1.0, 0.0), 7, None)
        self.assertEqual(len(match.bullets) - n, 5)

    def test_tocha_poe_fogo(self):
        match, p = campo("tocha")
        alvo = inimigo(match, "golem", p.x + 40, p.y)
        alvo.hp = alvo.max_hp = 100000
        usar(match, p, alvo, 1)
        self.assertGreater(alvo.burn_timer, 0)

    def test_agua_deixa_lento_e_botox_congela(self):
        for key, attr in (("pistola_agua", "slow_timer"), ("pistola_botox", "frozen_timer")):
            match, p = campo(key)
            alvo = inimigo(match, "golem", p.x + 100, p.y)
            alvo.hp = alvo.max_hp = 100000
            match.spawn_projectile(p, p.weapon, (1.0, 0.0), 5, alvo)
            hit = False
            for _ in range(30):
                passo(match, 1)
                hit = hit or getattr(alvo, attr) > 0
            self.assertTrue(hit, key)


if __name__ == "__main__":
    unittest.main()
