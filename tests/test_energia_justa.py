"""Energia mais justa: golpe de perto de graça (só o efeito gasta) e energia que volta lutando."""
import unittest

from apoio import FakeInput
from test_armas_raras import campo, inimigo

from soulstrike import energia
from soulstrike.data import RARE_WEAPONS
from soulstrike.upgrades import UPGRADES


def bater(match, p, alvo):
    p.attack_cd = 0
    p.attack(match, alvo)


class GolpeDePertoTest(unittest.TestCase):
    def test_machado_gira_pagando_e_sem_energia_bate_so_para_frente(self):
        match, p = campo("machado")
        frente = inimigo(match, "esqueleto", p.x + 40, p.y)
        atras = inimigo(match, "esqueleto", p.x - 40, p.y)
        for e in (frente, atras):
            e.hp = e.max_hp = 10000
        p.face(frente)
        hp = atras.hp
        bater(match, p, frente)
        self.assertLess(atras.hp, hp)                          # o giro pega o de trás
        self.assertEqual(p.energy, p.energy_max - 2)
        p.energy = 0
        hp_f, hp_a = frente.hp, atras.hp
        bater(match, p, frente)
        self.assertLess(frente.hp, hp_f)                       # sem energia ainda bate (sem coronhada)
        self.assertEqual(atras.hp, hp_a)                       # mas sem o giro
        self.assertEqual(p.energy, 0)

    def test_teclado_so_gasta_no_terceiro_golpe(self):
        match, p = campo("teclado_mecanico", phase=3)
        alvo = inimigo(match, "esqueleto", p.x + 40, p.y)
        alvo.hp = alvo.max_hp = 10000
        full = p.energy
        bater(match, p, alvo)
        bater(match, p, alvo)
        self.assertEqual(p.energy, full)
        bater(match, p, alvo)
        self.assertEqual(p.energy, full - 2)

    def test_foice_do_ceifador_continua_gastando(self):
        self.assertEqual(energia.base_cost(RARE_WEAPONS["foice_ceifador"]), 3)
        self.assertEqual(energia.base_cost(RARE_WEAPONS["lamina_solar"]), 0)
        self.assertEqual(energia.base_cost(RARE_WEAPONS["machado"]), 0)

    def test_hud_mostra_o_custo_do_efeito(self):
        match, p = campo("lamina_solar")
        self.assertEqual(energia.shown_cost(p, p.weapon), 2)
        p.weapon_index = 0
        self.assertEqual(energia.shown_cost(p, p.weapon), 0)  # arma do herói


class EnergiaQueVoltaTest(unittest.TestCase):
    def test_habilidade_da_energia_por_acerto_ate_15(self):
        match, p = campo("besta")
        p.energy = 0
        energia.on_ability(p)
        alvo = inimigo(match, "esqueleto", p.x + 300, p.y)
        alvo.hp = alvo.max_hp = 10000
        for _ in range(10):
            alvo.take_damage(5, attacker=p, match=match)
        self.assertEqual(p.energy, energia.ABILITY_MAX)
        p.ability_energy_timer = 0
        energia.on_ability(p)
        p.ability_energy_timer = 0                             # passou a janela: não ganha mais
        alvo.take_damage(5, attacker=p, match=match)
        self.assertEqual(p.energy, energia.ABILITY_MAX)

    def test_abate_de_perto_e_esquiva_perfeita(self):
        match, p = campo("besta")
        p.weapon_index = 1                                     # espada do guerreiro
        p.energy = 0
        alvo = inimigo(match, "esqueleto", p.x + 40, p.y)
        alvo.hp = 1
        bater(match, p, alvo)
        self.assertEqual(p.energy, energia.MELEE_KILL)
        energia.on_perfect_dodge(p, match)
        self.assertEqual(p.energy, energia.MELEE_KILL + energia.PERFECT_DODGE)

    def test_sifao_vira_energia(self):
        self.assertIn("sifao", UPGRADES)
        match, p = campo("besta")
        UPGRADES["sifao"].apply(p)
        p.energy = 0
        alvo = inimigo(match, "esqueleto", p.x + 300, p.y)
        alvo.hp = alvo.max_hp = 10000
        alvo.take_damage(100, attacker=p, match=match)
        self.assertEqual(p.energy, 4)

    def test_elite_solta_orbe_grande(self):
        match, p = campo("besta")
        e = inimigo(match, "golem", p.x + 300, p.y)
        n = len(match.pickups)
        match._drop_orbs(e)
        big = [o for o in match.pickups[n:] if o.amount == energia.BIG_ORB_ENERGY]
        self.assertEqual(len(big), 1)

    def test_segurar_largar_perto_do_amigo_passa_energia(self):
        match, p = campo("besta")
        q = match.players[1]
        q.x, q.y = p.x + 50, p.y
        q.energy = 0
        inp = match.controllers[p]
        inp.hold("drop")
        for _ in range(energia.PASS_HOLD + 2):
            match.update()
            inp._pressed.clear()
        inp.release("drop")
        match.update()
        self.assertEqual(q.energy, energia.PASS_AMOUNT)
        self.assertEqual(p.energy, p.energy_max - energia.PASS_AMOUNT)
        self.assertEqual(len(p.weapons), 3)                    # não largou a arma

    def test_tocar_largar_perto_do_amigo_ainda_larga(self):
        match, p = campo("besta")
        q = match.players[1]
        q.x, q.y = p.x + 50, p.y
        q.energy = 0
        inp = match.controllers[p]
        inp.hold("drop")
        match.update()
        inp._pressed.clear()
        inp.release("drop")
        match.update()
        self.assertEqual(len(p.weapons), 2)
        self.assertEqual(q.energy, 0)


if __name__ == "__main__":
    unittest.main()
