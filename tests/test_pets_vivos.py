"""Pets animados, com falas e ajuda: os 6 estados de cada bicho, o balão com som e o limite de falas,
os momentos que fazem falar (dono caiu, parado, chefe...), a busca de itens e o aviso do chefe."""
import unittest

import pygame
from test_casa import casa_da_turma, passo, reset_progress
from test_fase_mapa import fase

from soulstrike import cacos, config, mascotes, pet_falas, settings
from soulstrike.entities import Pickup
from soulstrike.mascotes import ANIMS, Pet

ALL = ("gato", "cachorro", "papagaio", "capivara", "mico", "tuiuiu", "jabuti", "drone", "caquinho")


def _pet_do(match, slot):
    return next(p for p in match.props if isinstance(p, Pet) and p.target is not None and p.target.slot == slot)


def _fase_com_pet(pet="cachorro"):
    if pet in mascotes.PETS:
        reset_progress(mascotes={pet: 1})
    else:                                                   # pet da loja de CACOS
        reset_progress()
        cacos.give_pet(pet)
        cacos.set_pet(1, pet)
    match, inputs = fase(0)
    match._pet_talk = {"next": 0, "who": None}
    return match, inputs, _pet_do(match, 1)


class FolhasTest(unittest.TestCase):
    def test_seis_estados_para_cada_pet(self):
        for pet in ALL:
            for anim in ANIMS:
                fr = mascotes.frames(pet, anim)
                expected = mascotes.SPECIAL_COUNT.get(pet, 6) if anim == "especial" else mascotes.COUNT[anim]
                self.assertEqual(len(fr), expected, (pet, anim))
                self.assertEqual(len({f.get_size() for f in fr}), 1, (pet, anim))
                self.assertLess(fr[0].get_height(), 70, (pet, anim))       # mesmo tamanho dos pets de sempre

    def test_frases_e_sons_de_todos(self):
        for pet in ALL:
            for moment in pet_falas.MOMENTS:
                lines = pet_falas.LINES[pet][moment]
                self.assertTrue(lines, (pet, moment))
                for line in lines:
                    self.assertLessEqual(len(line), 36, line)             # cabe no balãozinho
            for n in (1, 2):
                self.assertTrue((config.SOUNDS_DIR / f"pet_{pet}_{n}.wav").is_file(), (pet, n))


class FalaTest(unittest.TestCase):
    def setUp(self):
        reset_progress()
        settings.change("falas_pets", "normal")

    def tearDown(self):
        settings.change("falas_pets", "normal")

    def test_uma_fala_a_cada_20_segundos(self):
        match, inputs, pet = _fase_com_pet()
        match.frame = 1000
        self.assertTrue(pet.say(match, "parado"))
        self.assertIsNotNone(pet.bubble)
        match.frame += 19 * 60
        self.assertFalse(pet.say(match, "caiu"))          # nem urgente fura os 20 s do mesmo pet
        match.frame += 60
        self.assertTrue(pet.say(match, "caiu"))

    def test_seis_segundos_entre_pets_e_um_balao_por_vez(self):
        match, inputs, pet = _fase_com_pet()
        outro = Pet("drone", (pet.x, pet.y))
        outro.follow(match.players[1])
        match.frame = 1000
        self.assertTrue(pet.say(match, "busca"))
        self.assertFalse(outro.say(match, "busca"))
        self.assertTrue(outro.say(match, "caiu"))          # urgente passa na frente e tira o outro balão
        self.assertIsNone(pet.bubble)
        self.assertIsNotNone(outro.bubble)

    def test_desligadas_e_poucas(self):
        match, inputs, pet = _fase_com_pet()
        match.frame = 1000
        settings.change("falas_pets", "desligadas")
        self.assertFalse(pet.say(match, "caiu"))
        settings.change("falas_pets", "poucas")
        self.assertTrue(pet.say(match, "caiu"))
        match.frame += 30 * 60
        self.assertFalse(pet.say(match, "caiu"))           # no POUCAS, 40 s

    def test_dono_caiu_fala_e_leva_susto(self):
        match, inputs, pet = _fase_com_pet()
        passo(match, inputs, 3)
        match.players[0].hp = 0
        passo(match, inputs, 2)
        self.assertEqual(pet.anim, "susto")
        self.assertIn(pet.bubble, pet_falas.LINES["cachorro"]["caiu"])

    def test_dono_parado_faz_a_graca_e_fala(self):
        match, inputs, pet = _fase_com_pet()
        for f in match.players:
            f.attack_cd = 0
        passo(match, inputs, mascotes.STILL_TALK - 10)
        pet.next_talk = 0                                   # a fala de entrada na fase já passou
        passo(match, inputs, 12)
        self.assertEqual(pet.anim, "especial")
        self.assertIsNotNone(pet.bubble)

    def test_na_casa_dorme_e_acorda(self):
        reset_progress(mascotes={"gato": 1})
        match, inputs = casa_da_turma(("guerreiro", "atirador"))
        gato = next(p for p in match.pets if p.pet == "gato")
        passo(match, inputs, mascotes.SLEEP_AFTER + 5)
        self.assertEqual(gato.anim, "dormindo")
        match.players[0].x += 40
        passo(match, inputs, 2)
        self.assertNotEqual(gato.anim, "dormindo")

    def test_balao_desenha(self):
        match, inputs, pet = _fase_com_pet()
        match.frame = 1000
        pet.say(match, "parado")
        screen = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
        match.draw(screen, match.game.ui)


class AjudaTest(unittest.TestCase):
    def setUp(self):
        reset_progress()

    def test_busca_item_caido_perto(self):
        match, inputs, pet = _fase_com_pet("jabuti")
        p1 = match.players[0]
        p1.hp = p1.max_hp - 50
        x, y = match.arena.free_spot(p1.x - 90, p1.y + 50, 14)       # longe do P2, que fica à direita
        item = Pickup("vida", x, y)
        match.pickups.append(item)
        passo(match, inputs, mascotes.FETCH_EVERY + 4 * 60)
        self.assertFalse(item.alive)
        self.assertGreater(p1.hp, p1.max_hp - 50)

    def test_nao_busca_o_que_nao_serve(self):
        match, inputs, pet = _fase_com_pet()
        p1 = match.players[0]
        for f in match.players:
            f.hp = f.max_hp                                 # vida cheia: a poção fica no chão
        x, y = match.arena.free_spot(p1.x - 90, p1.y + 50, 14)
        item = Pickup("vida", x, y)
        match.pickups.append(item)
        passo(match, inputs, mascotes.FETCH_EVERY + 120)
        self.assertTrue(item.alive)
        self.assertIsNone(pet.fetching)

    def test_aviso_do_golpe_forte(self):
        match, inputs, pet = _fase_com_pet()
        p1 = match.players[0]

        class Chefe:
            alive_in_match = True
            windup = 0
            windup_total = 60
            x, y = p1.x + 200, p1.y
        match.boss = Chefe()
        passo(match, inputs, 2)
        match.boss.windup = 60
        pet.update(match)
        self.assertGreater(pet.warn, 0)
        self.assertEqual(pet.anim, "susto")


class OpcaoTest(unittest.TestCase):
    def test_opcao_nas_opcoes(self):
        from soulstrike.scenes.menus import OptionsScene
        self.assertIn("falas_pets", [r[0] for r in OptionsScene.ROWS])
        self.assertEqual(settings.DEFAULTS["falas_pets"], "normal")


if __name__ == "__main__":
    unittest.main()
