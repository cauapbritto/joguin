"""Mascotes da Casa (adotar, um dono por bicho, seguir nas fases) e a luz das janelas pela hora."""
import unittest

import pygame
from test_casa import casa_da_turma, passo, reset_progress

from soulstrike import luz_casa, mascotes
from soulstrike.mascotes import Pet


def _pet(match, key):
    return next(p for p in match.pets if p.pet == key)


def _perto(f, pet):
    f.x, f.y = pet.home[0], pet.home[1] + 20


class MascotesTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_tres_bichos_em_casa_sem_dono(self):
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        self.assertEqual({p.pet for p in match.pets}, {"gato", "cachorro", "papagaio"})
        self.assertTrue(all(p.target is None for p in match.pets))

    def test_adotar_segue_e_fica_salvo(self):
        match, inputs = casa_da_turma(("guerreiro", "atirador"))
        p1 = match.players[0]
        gato = _pet(match, "gato")
        _perto(p1, gato)
        self.assertEqual(mascotes.prompt(match, p1), "ATACAR: ADOTAR O GATO")
        self.assertTrue(mascotes.interact(match, p1))
        self.assertIs(gato.target, p1)
        self.assertEqual(mascotes.owners(), {"gato": p1.slot})
        p1.x += 300
        passo(match, inputs, 90)
        self.assertLess(abs(gato.x - p1.x), 80)

    def test_um_dono_por_bicho(self):
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        p1, p2 = match.players[:2]
        cao = _pet(match, "cachorro")
        _perto(p1, cao)
        mascotes.interact(match, p1)
        cao.x, cao.y = cao.home                    # o bicho segue o P1, mas o P2 chega no cantinho
        _perto(p2, cao)
        self.assertFalse(mascotes.interact(match, p2))
        self.assertIs(cao.target, p1)

    def test_um_pet_por_jogador(self):
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        p1 = match.players[0]
        gato, cao = _pet(match, "gato"), _pet(match, "cachorro")
        _perto(p1, gato)
        mascotes.interact(match, p1)
        _perto(p1, cao)
        self.assertTrue(mascotes.interact(match, p1))        # adotar outro devolve o gato
        self.assertIs(cao.target, p1)
        self.assertIsNone(gato.target)
        self.assertEqual(mascotes.owners(), {"cachorro": p1.slot})

    def test_bicho_da_casa_tira_o_pet_da_loja_e_vice_versa(self):
        from soulstrike import cacos
        cacos.give_pet("capivara")
        cacos.set_pet(1, "capivara")
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        p1 = match.players[0]
        gato = _pet(match, "gato")
        _perto(p1, gato)
        mascotes.interact(match, p1)
        self.assertIsNone(cacos.pet_of(1))
        shop = [p for p in match.props if isinstance(p, Pet) and p.shop]
        self.assertEqual(shop, [])
        cacos.set_pet(1, "capivara")                          # o armário faz isso e chama send_home
        mascotes.send_home(match, 1)
        self.assertIsNone(gato.target)
        self.assertEqual(mascotes.owners(), {})

    def test_save_antigo_com_varios_fica_com_um(self):
        reset_progress(mascotes={"gato": 1, "cachorro": 1, "papagaio": 2})
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        self.assertEqual(mascotes.owners(), {"gato": 1, "papagaio": 2})
        self.assertIsNone(_pet(match, "cachorro").target)

    def test_deixar_em_casa(self):
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        p1 = match.players[0]
        louro = _pet(match, "papagaio")
        _perto(p1, louro)
        mascotes.interact(match, p1)
        self.assertEqual(mascotes.prompt(match, p1), "ATACAR: DEIXAR O PAPAGAIO EM CASA")
        mascotes.interact(match, p1)
        self.assertIsNone(louro.target)
        self.assertEqual(mascotes.owners(), {})

    def test_dono_volta_com_o_bicho_atras(self):
        reset_progress(mascotes={"cachorro": 1})
        match, _ = casa_da_turma(("guerreiro", "atirador"))
        self.assertIs(_pet(match, "cachorro").target, match.players[0])

    def test_vem_junto_nas_fases(self):
        reset_progress(mascotes={"gato": 2})
        from test_fase_mapa import fase
        match, _ = fase(0)
        pets = [p for p in match.props if isinstance(p, Pet)]
        self.assertEqual([(p.pet, p.target) for p in pets], [("gato", match.players[1])])


class LuzTest(unittest.TestCase):
    def test_periodos(self):
        self.assertEqual(luz_casa.period(8)[0], "manhã")
        self.assertEqual(luz_casa.period(12)[0], "dia")
        self.assertEqual(luz_casa.period(17)[0], "tarde")
        self.assertEqual(luz_casa.period(23)[0], "noite")
        self.assertEqual(luz_casa.period(3)[0], "noite")

    def test_noite_escurece_o_vidro(self):
        class Cam:
            x = y = 0
        for hour, dark in ((12, False), (22, True)):
            surf = pygame.Surface((300, 300))
            surf.fill((120, 170, 210))
            luz_casa.CasaLight([(50, 20, 120, 52)], hour=hour).draw(surf, Cam())
            r, g, b, _ = surf.get_at((100, 40))
            self.assertEqual(b < 120, dark, hour)
