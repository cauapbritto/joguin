"""Campanha: times (sem fogo amigo), ondas, levantar companheiro, continues, melhorias, chefão e desbloqueio."""
import os
import unittest

from apoio import FakeInput, game

from soulstrike import progress
from soulstrike.boss import BossAI
from soulstrike.campaign import (DOWN_FRAMES, DUNGEON_1, DUNGEON_2, EXIT_DELAY, GAMEOVER_FRAMES, LEAVE_FRAMES,
                                 PHASE_HEAL, PHASES, REVIVE_FRAMES, CampaignMatch, CampaignRun, elite_hp_scale,
                                 scaled_count)
from soulstrike.data import CHARACTERS, UNLOCKABLE, roster, roster_indices
from soulstrike.entities import Barrier, Bullet, Explosion, ShadowBomb
from soulstrike.session import Session, SlotSetup
from soulstrike.upgrades import UPGRADES, apply_all, choices

KEYS = [c.key for c in CHARACTERS]


def campanha(chars=("guerreiro", "atirador"), phase=0, difficulty="normal", dungeon=0):
    """Uma masmorra da campanha (dungeon 0 = a 1ª da fase, 1 = a 2ª, a do chefão no templo)."""
    g = game()
    slots = [SlotSetup(i + 1, char=KEYS.index(c)) for i, c in enumerate(chars)]
    g.session = Session("campaign", slots, difficulty=difficulty)
    run = CampaignRun(g.session)
    run.phase_index = phase
    run.begin_phase()
    run.stage = DUNGEON_2 if dungeon else DUNGEON_1
    match = CampaignMatch(g, run)
    inputs = {}
    for f in match.players:
        inputs[f.slot] = match.controllers[f] = FakeInput()
    return match, inputs


def pular_intro(match):
    match.state, match.state_timer, match.banner = "fight", 0, None


def passo(match, frames):
    for _ in range(frames):
        match.update()


def inimigo(match, kind, x, y):
    match._spawn(kind, x, y)
    e = match.enemies[-1]
    match.controllers.pop(e)            # parado (sem cérebro)
    return e


class TimesTest(unittest.TestCase):
    def test_tiro_nao_acerta_companheiro_e_acerta_inimigo(self):
        match, _ = campanha()
        pular_intro(match)
        p1, p2 = match.players
        p1.x, p1.y, p2.x, p2.y = 400, 600, 470, 600
        e = inimigo(match, "esqueleto", 560, 600)
        hp2, hpe = p2.hp, e.hp
        match.bullets.append(Bullet(p1, p1.x + 20, p1.y - 6, 1, 0, 9, 10, (255, 255, 255)))
        passo(match, 30)
        self.assertEqual(p2.hp, hp2)
        self.assertLess(e.hp, hpe)

    def test_tiro_do_inimigo_acerta_jogador(self):
        match, _ = campanha()
        pular_intro(match)
        p1 = match.players[0]
        p1.x, p1.y = 400, 600
        e = inimigo(match, "esqueleto", 600, 600)
        hp = p1.hp
        match.bullets.append(Bullet(e, e.x - 20, e.y - 6, -1, 0, 9, 10, (255, 255, 255)))
        passo(match, 30)
        self.assertLess(p1.hp, hp)

    def test_explosao_do_jogador_poupa_o_companheiro(self):
        match, _ = campanha()
        p1, p2 = match.players
        p2.x, p2.y = 500, 600
        e = inimigo(match, "diabrete", 520, 600)
        hp2, hpe = p2.hp, e.hp
        boom = Explosion(p1, 510, 600, 20)
        boom.update(match)
        self.assertEqual(p2.hp, hp2)
        self.assertLess(e.hp, hpe)

    def test_muralha_bloqueia_so_o_tiro_do_inimigo(self):
        match, _ = campanha(chars=("tanque", "atirador"))
        tanque, atirador = match.players
        match.effects.append(Barrier(tanque, 500, 600, 1, 0, 200))
        e = inimigo(match, "esqueleto", 700, 600)
        amigo = Bullet(atirador, 470, 606, 1, 0, 8, 10, (255, 255, 255))
        rival = Bullet(e, 530, 606, -1, 0, 8, 10, (255, 255, 255))
        match.bullets += [amigo, rival]
        for _ in range(4):
            match._update_bullets()
        self.assertTrue(amigo.alive)            # passou pela muralha do companheiro
        self.assertFalse(rival.alive)

    def test_perfurar_atravessa_um_inimigo(self):
        match, _ = campanha()
        pular_intro(match)
        p1 = match.players[0]
        p1.pierce = 1
        p1.x, p1.y = 300, 600
        a = inimigo(match, "diabrete", 420, 600)
        b = inimigo(match, "diabrete", 500, 600)
        ha, hb = a.hp, b.hp
        match.bullets.append(Bullet(p1, 330, 594, 1, 0, 10, 8, (255, 255, 255)))
        for _ in range(30):
            match._update_bullets()
        self.assertLess(a.hp, ha)
        self.assertLess(b.hp, hb)

    def test_golpe_corpo_a_corpo_acerta_varios_na_frente(self):
        match, _ = campanha()
        p1 = match.players[0]
        p1.weapon_index = 1              # espada
        p1.x, p1.y, p1.facing = 400, 600, (1.0, 0.0)
        a = inimigo(match, "diabrete", 450, 585)
        b = inimigo(match, "diabrete", 455, 620)
        atras = inimigo(match, "diabrete", 340, 600)
        ha, hb, hc = a.hp, b.hp, atras.hp
        p1.attack(match, a)
        self.assertLess(a.hp, ha)
        self.assertLess(b.hp, hb)
        self.assertEqual(atras.hp, hc)


class OndasTest(unittest.TestCase):
    def test_mais_jogadores_mais_inimigos(self):
        self.assertEqual(scaled_count("diabrete", 4, 1), 4)
        self.assertEqual(scaled_count("diabrete", 4, 2), 6)
        self.assertEqual(scaled_count("diabrete", 4, 4), 10)
        self.assertEqual(scaled_count("golem", 1, 4), 1)          # os fortes ganham vida em vez de número
        self.assertGreater(elite_hp_scale("golem", 4), 1)
        self.assertGreater(elite_hp_scale("chefe", 4), elite_hp_scale("golem", 4))

    def test_onda_sai_dos_portais_longe_dos_jogadores(self):
        match, _ = campanha()
        pular_intro(match)
        match._start_wave(0)
        self.assertEqual(len(match.portals), scaled_count("diabrete", 5, 2))
        for portal in match.portals:
            near = min(p.distance_to(portal) for p in match.players)
            self.assertGreater(near, 250)
        passo(match, 200)
        self.assertEqual(len(match.alive_enemies), scaled_count("diabrete", 5, 2))
        self.assertTrue(all(e.team == 1 for e in match.enemies))

    def test_limpar_a_masmorra_1_abre_a_porta_de_volta(self):
        from soulstrike.campaign import LobbyMatch
        from soulstrike.dungeon import ExitDoor
        match, _ = campanha()
        pular_intro(match)
        match.wave = len(match.waves) - 1
        p1, p2 = match.players
        p1.hp = 30
        p2.hp = 0                                   # quem caiu levanta quando a sala fica limpa
        passo(match, 2)
        self.assertEqual(match.state, "clear")
        self.assertTrue(p2.alive_in_match)
        passo(match, EXIT_DELAY + 2)
        self.assertEqual(match.state, "exit")
        door = match.exit
        self.assertIsInstance(door, ExitDoor)
        passo(match, 30)
        self.assertFalse(match.finished)            # ninguém foi até a porta ainda
        for p in match.players:
            p.x, p.y = door.x, door.y + 20
        passo(match, LEAVE_FRAMES + 4)
        self.assertTrue(match.finished and match.won)
        self.assertAlmostEqual(match.run.hp_ratio[1], 30 / p1.max_hp, places=3)
        scene = match.next_scene()
        self.assertIsInstance(scene.match, LobbyMatch)
        self.assertTrue(scene.match.back)

    def test_botao_de_teletransporte_leva_para_a_proxima_fase(self):
        from soulstrike.net.remote import hub
        match, inputs = campanha(dungeon=1)
        pular_intro(match)
        match.wave = len(match.waves) - 1
        p1, p2 = match.players
        p1.hp = 30
        hub.join(2, "tele")
        try:
            passo(match, EXIT_DELAY + 4)
            self.assertEqual(match.state, "vote")
            self.assertTrue(match.wants_cursor)
            self.assertEqual(hub.status(2, "tele")["me"]["vote"], 1)     # o celular mostra o botão
            inputs[1].tap("attack")
            passo(match, 2)
            self.assertEqual(match.votes, {p1})
            self.assertEqual(match.state, "vote")      # ainda falta o P2
            inputs[2].tap("confirm")                   # botão no celular
            passo(match, 2)
            self.assertEqual(match.state, "teleport")
            self.assertEqual(hub.status(2, "tele")["me"]["vote"], 0)
        finally:
            hub.leave(2, "tele")
        passo(match, 120)
        self.assertTrue(match.finished and match.won)
        self.assertAlmostEqual(match.run.hp_ratio[1], min(1.0, 30 / p1.max_hp + PHASE_HEAL), places=3)
        from soulstrike.scenes.campaign import UpgradeScene
        self.assertIsInstance(match.next_scene(), UpgradeScene)

    def test_clique_no_botao_confirma_quem_esta_no_teclado(self):
        match, inputs = campanha(dungeon=1)
        pular_intro(match)
        match.wave = len(match.waves) - 1
        passo(match, EXIT_DELAY + 4)
        g = game()
        match.draw(g.screen, g.ui)                     # o botão aparece na tela
        button = match.vote_button
        self.assertIsNotNone(button)
        self.assertFalse(match.click((5, 5)))
        self.assertTrue(match.click(button.center))
        self.assertTrue(match.click(button.center))
        self.assertEqual(match.votes, set(match.players))

    def test_ultima_fase_vai_para_o_final(self):
        match, _ = campanha(phase=len(PHASES) - 1, dungeon=1)
        match.won = True
        from soulstrike.scenes.campaign import StoryScene
        scene = match.next_scene()
        self.assertIsInstance(scene, StoryScene)
        self.assertEqual(scene.heading, "FIM")

    def test_inimigo_morto_some_e_pode_deixar_item(self):
        match, _ = campanha()
        pular_intro(match)
        e = inimigo(match, "golem", 900, 600)
        e.hp = 0
        passo(match, 80)
        self.assertNotIn(e, match.fighters)


class CaidosTest(unittest.TestCase):
    def test_companheiro_perto_levanta_quem_caiu(self):
        match, _ = campanha()
        pular_intro(match)
        inimigo(match, "diabrete", 1800, 1200)       # a onda não acaba
        p1, p2 = match.players
        p1.x, p1.y, p2.x, p2.y = 500, 700, 530, 700
        p1.hp = 0
        passo(match, REVIVE_FRAMES // 2)
        self.assertFalse(p1.alive_in_match)
        passo(match, REVIVE_FRAMES)
        self.assertTrue(p1.alive_in_match)
        self.assertEqual(p1.hp, round(p1.max_hp * 0.4))

    def test_longe_nao_levanta(self):
        match, _ = campanha()
        pular_intro(match)
        inimigo(match, "diabrete", 1800, 1200)
        p1, p2 = match.players
        p1.x, p1.y, p2.x, p2.y = 500, 700, 800, 700
        p1.hp = 0
        passo(match, REVIVE_FRAMES * 2)
        self.assertFalse(p1.alive_in_match)

    def test_todos_caidos_usa_continue(self):
        match, _ = campanha()
        pular_intro(match)
        inimigo(match, "diabrete", 1800, 1200)
        for p in match.players:
            p.hp = 0
        passo(match, DOWN_FRAMES + 5)
        self.assertEqual(match.run.continues, 2)
        self.assertTrue(all(p.alive_in_match for p in match.players))

    def test_sem_continue_e_fim_de_jogo(self):
        match, _ = campanha()
        pular_intro(match)
        inimigo(match, "diabrete", 1800, 1200)
        match.run.continues = 0
        for p in match.players:
            p.hp = 0
        passo(match, DOWN_FRAMES + GAMEOVER_FRAMES + 5)
        self.assertTrue(match.finished)
        self.assertFalse(match.won)
        from soulstrike.scenes.campaign import GameOverScene
        self.assertIsInstance(match.next_scene(), GameOverScene)

    def test_tentar_de_novo_volta_ao_comeco_da_fase(self):
        match, _ = campanha(phase=1)
        run = match.run
        run.continues = 0
        run.upgrades[1].append("vida")         # ganhou depois do começo da fase: não vale
        run.retry_phase()
        self.assertEqual(run.upgrades[1], [])
        self.assertEqual(run.continues, 3)
        self.assertEqual(run.phase_index, 1)

    def test_ninguem_se_afasta_demais(self):
        match, _ = campanha()
        p1, p2 = match.players
        p1.x, p1.y = 200, 700
        p2.x, p2.y = 1900, 700
        match._leash()
        from soulstrike.campaign import LEASH_X
        self.assertLessEqual(abs(p2.x - p1.x), LEASH_X + 1)


class MelhoriasTest(unittest.TestCase):
    def test_tres_opcoes_diferentes(self):
        for _ in range(30):
            opts = choices([])
            self.assertEqual(len(opts), 3)
            self.assertEqual(len(set(opts)), 3)

    def test_melhorias_se_acumulam(self):
        match, _ = campanha()
        f = match.players[0]
        base_hp, base_dmg = f.max_hp, f.damage_mult
        apply_all(f, ["vida", "vida", "dano", "perfurar", "escudo", "recarga"])
        self.assertEqual(f.max_hp, base_hp + 50)
        self.assertAlmostEqual(f.damage_mult, base_dmg * 1.15)
        self.assertEqual(f.pierce, 1)
        self.assertEqual(f.shield, 40)
        self.assertLess(f.ability_cooldown, 600)

    def test_escudo_absorve_dano(self):
        match, _ = campanha()
        f = match.players[0]
        f.shield = 40
        hp = f.hp
        f.take_damage(25, match=match)
        self.assertEqual(f.hp, hp)
        self.assertEqual(f.shield, 15)

    def test_vampirismo_cura(self):
        match, _ = campanha()
        f = match.players[0]
        f.lifesteal = 0.5
        f.hp = 50
        e = inimigo(match, "golem", 900, 600)
        e.take_damage(20, attacker=f, match=match)
        self.assertEqual(f.hp, 60)

    def test_nova_fase_aplica_as_melhorias(self):
        match, _ = campanha()
        run = match.run
        run.add_upgrade(1, "vida")
        run.add_upgrade(2, "velocidade")
        run.advance()
        nova = CampaignMatch(game(), run)
        p1, p2 = nova.players
        self.assertEqual(p1.max_hp, CHARACTERS[KEYS.index("guerreiro")].max_hp + 25)
        self.assertAlmostEqual(p2.speed_mult, 1.1)

    def test_tela_de_melhoria_pelo_celular(self):
        from soulstrike.scenes.campaign import UpgradeScene
        match, _ = campanha()
        g = game()
        done = []
        scene = UpgradeScene(g, match.run, lambda: done.append(True) or scene)
        fake = {s: FakeInput() for s in (1, 2)}
        real = g.inputs
        g.inputs = fake
        try:
            scene.ticks = 30
            fake[1].tap("opt3")
            fake[2].tap("opt1")
            scene.update()
            self.assertEqual(scene.index, {1: 2, 2: 0})
            for inp in fake.values():
                inp.end_frame()
                inp.tap("confirm")
            scene.update()
            self.assertTrue(all(scene.locked.values()))
            for inp in fake.values():
                inp.end_frame()
            for _ in range(50):
                scene.update()
        finally:
            g.inputs = real
        self.assertTrue(done)
        self.assertEqual(len(match.run.upgrades[1]), 1)
        self.assertIn(match.run.upgrades[1][0], UPGRADES)


class ChefaoTest(unittest.TestCase):
    def _chefe(self, players=("guerreiro", "atirador")):
        match, _ = campanha(chars=players, phase=len(PHASES) - 1, dungeon=1)
        pular_intro(match)
        match.wave = len(match.waves) - 1
        match._spawn("chefe", 800, 330)
        return match, match.boss, match.controllers[match.boss]

    def test_chefao_mais_forte_com_mais_jogadores(self):
        _, solo, _ = self._chefe(players=("guerreiro",))
        _, quatro, _ = self._chefe(players=("guerreiro", "atirador", "ninja", "geada"))
        self.assertGreater(quatro.max_hp, solo.max_hp * 2)

    def test_nao_e_atordoado_nem_puxado(self):
        match, boss, _ = self._chefe()
        self.assertFalse(boss.stun(60))
        self.assertFalse(boss.pull(0, 0))

    def test_chama_ajuda_e_fica_furioso(self):
        match, boss, ai = self._chefe()
        self.assertIsInstance(ai, BossAI)
        boss.hp = boss.max_hp // 2 - 1
        passo(match, 2)
        self.assertTrue(ai.summoned)
        self.assertGreater(len(match.portals), 0)
        ai.state, ai.timer = "walk", 50
        boss.hp = boss.max_hp // 5 - 1
        passo(match, 2)
        self.assertTrue(ai.enraged)

    def test_cansado_leva_mais_dano(self):
        match, boss, ai = self._chefe()
        ai.combo = []
        ai._next(boss, match)
        self.assertEqual(ai.state, "tired")
        hp = boss.hp
        boss.take_damage(10, match=match)
        self.assertEqual(hp - boss.hp, 16)

    def test_golpes_do_chefao_rodam_sem_erro(self):
        match, boss, ai = self._chefe()
        for p in match.players:
            p.max_hp = p.hp = 99999                 # ninguém cai durante o teste
        seen = set()
        for _ in range(60 * 40):
            match.update()
            seen.add(ai.state)
        self.assertTrue({"rain", "ring", "air", "tired"} <= seen, seen)

    def test_derrotar_o_chefao_vence_a_fase(self):
        match, boss, ai = self._chefe()
        boss.hp = 0
        passo(match, 400)
        self.assertTrue(match.slain_boss)
        self.assertEqual(match.state, "vote")        # o teletransporte leva para o final


class DesbloqueioTest(unittest.TestCase):
    def setUp(self):
        self.path = progress.path()
        if self.path.exists():
            self.path.unlink()

    tearDown = setUp

    def test_progresso_fica_na_pasta_de_teste(self):
        self.assertIn("soulstrike-", str(self.path))
        self.assertNotIn(os.path.expanduser("~/.soulstrike"), str(self.path))

    def test_zerar_libera_o_aryel_corrompido(self):
        self.assertNotIn(UNLOCKABLE, [c.key for c in roster()])
        record, unlocked = progress.record_campaign(500, "normal", 2)
        self.assertTrue(record and unlocked)
        self.assertIn(UNLOCKABLE, [c.key for c in roster()])
        self.assertEqual(progress.best_time("normal"), 500)
        record, unlocked = progress.record_campaign(600, "normal", 1)
        self.assertFalse(record or unlocked)
        record, _ = progress.record_campaign(400, "normal", 1)
        self.assertTrue(record)
        self.assertEqual(progress.best_time("normal"), 400)

    def test_celular_ve_o_personagem_novo(self):
        # o celular sempre recebe todos (acha o escolhido pelo índice); quem libera é a escolha
        from soulstrike.net import server
        client = server.app.test_client()
        before = client.get("/api/roster").get_json()
        progress.record_campaign(500, "normal", 1)
        after = client.get("/api/roster").get_json()
        self.assertEqual(len(after), len(before))
        i = KEYS.index(UNLOCKABLE)
        self.assertEqual(after[i]["name"], "Aryel Corrompido")
        self.assertEqual(after[i]["soccer_power"], "BOMBA SOMBRIA")
        self.assertIn(i, roster_indices())

    def test_chuva_sombria_no_duelo(self):
        from soulstrike.matches import BattleMatch
        g = game()
        g.session = Session("duel", [SlotSetup(1, char=KEYS.index(UNLOCKABLE)), SlotSetup(2, char=0)])
        match = BattleMatch(g, g.session)
        match.controllers.clear()
        a, b = match.fighters
        a.x, a.y, b.x, b.y = 400, 600, 650, 600
        self.assertTrue(a.use_ability(match, b))
        bombs = [e for e in match.effects if isinstance(e, ShadowBomb)]
        self.assertEqual(len(bombs), 5)
        hp_a, hp_b = a.hp, b.hp
        for _ in range(80):
            for e in list(match.effects):
                e.update(match)
            match.effects = [e for e in match.effects if e.alive]
        self.assertLess(b.hp, hp_b)
        self.assertEqual(a.hp, hp_a)            # a própria bomba não machuca quem jogou
        self.assertIsNotNone(a.aura)            # e ele solta a sombra

    def test_sombras_sao_bem_escuras(self):
        assets = game().assets

        def brilho(img):
            total = n = 0
            for y in range(img.get_height()):
                for x in range(img.get_width()):
                    r, g, b, a = img.get_at((x, y))
                    if a:
                        total += r + g + b
                        n += 1
            return total / n

        for key in ("velocista", "tanque", "ninja", "aryel"):
            normal = brilho(assets.sprites[key].frame("frente", 0))
            sombra = brilho(assets.shadow_sprites(key).frame("frente", 0))
            self.assertLess(sombra, normal * 0.6, key)


class TelasTest(unittest.TestCase):
    def test_lobby_p2_entra_pelo_teclado(self):
        from soulstrike.scenes.select import CharSelectScene, LobbyScene
        g = game()
        g.session = Session("campaign", [SlotSetup(1)])
        lobby = LobbyScene(g)
        self.assertEqual(lobby.joined, {1})
        real = g.inputs
        fake = {s: FakeInput() for s in (1, 2, 3, 4)}
        g.inputs = fake
        try:
            fake[2].tap("confirm")
            lobby.update()
        finally:
            g.inputs = real
        self.assertEqual(lobby.joined, {1, 2})
        lobby._continue()
        self.assertEqual([s.slot for s in g.session.slots], [1, 2])
        self.assertIsInstance(g.scene, CharSelectScene)

    def test_telas_desenham(self):
        from soulstrike.scenes.campaign import CampaignEndScene, GameOverScene, StoryScene, UpgradeScene
        match, _ = campanha()
        g = game()
        run = match.run
        for scene in (StoryScene(g, "prologo", lambda: None), UpgradeScene(g, run, lambda: None),
                      GameOverScene(g, run), CampaignEndScene(g, run)):
            for _ in range(3):
                scene.draw(g.screen)
                scene.ticks += 1
        match.draw(g.screen, g.ui)


if __name__ == "__main__":
    unittest.main()
