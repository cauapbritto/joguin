"""Pacote de áudio: som de cada arma, sons do futebol e da campanha, músicas novas e limite de sons iguais."""
import unittest
from unittest import mock

from apoio import MEIO, futebol, game
from test_campanha import ChefaoTest, campanha, pular_intro
from test_masmorra import acampamento

from soulstrike import config
from soulstrike.assets import MAX_SAME_SOUND, MUSIC_FILES
from soulstrike.data import CHARACTERS, SHOT_SOUNDS, shot_sound
from soulstrike.projectiles import PROJECTILES
from soulstrike.scenes.play import PlayScene


class Gravador:
    """Troca assets.play por uma lista dos sons pedidos."""

    def __init__(self):
        self.sons = []

    def __enter__(self):
        self._patch = mock.patch.object(game().assets, "play", side_effect=lambda name, vol=0.5, at=None: self.sons.append(name))
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()


class ArquivosTest(unittest.TestCase):
    def test_todo_som_de_arma_existe(self):
        for name in set(SHOT_SOUNDS.values()) | {"shoot", "shoot2", "golpe", "chute", "apito", "torcida", "bau",
                                                  "teletransporte", "levantar", "passo_pesado", "alma", "compra", "loja", "pagina"}:
            self.assertTrue((config.SOUNDS_DIR / f"{name}.wav").is_file(), name)
            self.assertIn(name, game().assets.sounds, name)

    def test_sons_da_v17_existem(self):
        from soulstrike.scenes.penalty import CELEBRATIONS
        names = {"cravada", "chute_forte", "assobio", "gol_rede", "replay", "torcida_abafa", "coracao", "vaia",
                 "uuuh", "ooh", "apito_longo"} | {"comemora_" + key for key in CELEBRATIONS}
        for name in names:
            self.assertTrue((config.SOUNDS_DIR / f"{name}.wav").is_file(), name)

    def test_todo_estilo_de_projetil_tem_som(self):
        for style in PROJECTILES:
            if style != "bala":                         # a bala do rifle usa o tiro comum (shoot/shoot2)
                self.assertIn(style, SHOT_SOUNDS, style)

    def test_musicas_existem(self):
        for name, file in MUSIC_FILES.items():
            self.assertTrue((config.SOUNDS_DIR / file).is_file(), name)

    def test_tiro_comum_alterna(self):
        rifle = next(c for c in CHARACTERS if c.key == "atirador").weapons[0]
        self.assertEqual(shot_sound(rifle, 1), SHOT_SOUNDS.get(rifle.style, "shoot"))
        arco = next(c for c in CHARACTERS if c.key == "guerreiro").weapons[0]
        self.assertEqual(shot_sound(arco), "arco")


class MixagemTest(unittest.TestCase):
    def test_limite_de_sons_iguais(self):
        assets = game().assets
        sound = mock.Mock()
        sound.get_num_channels.return_value = MAX_SAME_SOUND
        with mock.patch.dict(assets.sounds, {"teste": sound}):
            assets.play("teste")
        sound.play.assert_not_called()
        sound.get_num_channels.return_value = MAX_SAME_SOUND - 1
        with mock.patch.dict(assets.sounds, {"teste": sound}):
            assets.play("teste")
        sound.play.assert_called_once()

    def test_som_que_nao_existe_e_ignorado(self):
        game().assets.play("nao_existe")


class PausaDaMusicaTest(unittest.TestCase):
    def test_pausa_deixa_a_musica_muda_sem_music_pause(self):
        """music.pause()/unpause() do pygame 2.6 seguram o GIL e podem travar o jogo."""
        g = game()
        match, _ = futebol()
        scene = PlayScene(g, match)
        g.scene = scene
        with mock.patch("pygame.mixer.get_init", return_value=(44100, -16, 2)), \
                mock.patch("pygame.mixer.music") as music:
            scene._set_paused(True)
            self.assertEqual(music.set_volume.call_args[0][0], 0.0)
            g.assets.apply_music_volume()                # mexer no volume nas opções não volta o som
            self.assertEqual(music.set_volume.call_args[0][0], 0.0)
            scene._set_paused(False)
            self.assertGreater(music.set_volume.call_args[0][0], 0.0)
            scene._set_paused(True)
            scene._choose("quit")
            self.assertGreater(music.set_volume.call_args[0][0], 0.0)
            music.pause.assert_not_called()
            music.unpause.assert_not_called()
        self.assertFalse(g.assets.music_paused)


class DueloTest(unittest.TestCase):
    def test_golpe_de_perto_tem_som_de_golpe(self):
        match, _ = campanha()
        pular_intro(match)
        p1 = match.players[0]
        p1.weapon_index = next(i for i, w in enumerate(p1.weapons) if w.is_melee)
        alvo = match.players[1]
        with Gravador() as g:
            p1.attack(match, alvo)
        self.assertIn("golpe", g.sons)
        self.assertNotIn("shoot", g.sons)

    def test_tiro_usa_o_som_da_arma(self):
        match, _ = campanha(chars=("geada", "atirador"))
        pular_intro(match)
        p1 = match.players[0]
        p1.weapon_index = next(i for i, w in enumerate(p1.weapons) if not w.is_melee)
        with Gravador() as g:
            p1.attack(match, match.players[1])
        self.assertIn("gelo", g.sons)


class FutebolTest(unittest.TestCase):
    def test_gol_tem_torcida(self):
        match, _ = futebol()
        with Gravador() as g:
            match._goal(0)
        self.assertIn("torcida", g.sons)

    def test_saida_de_bola_tem_apito(self):
        match, _ = futebol()
        with Gravador() as g:
            match._kickoff()
        self.assertIn("apito", g.sons)

    def test_chute_tem_som_de_chute(self):
        match, _ = futebol()
        p1 = match.fighters[0]
        p1.x, p1.y = 600, MEIO
        match.ball.x, match.ball.y = 630, MEIO
        for _ in range(40):
            p1.steer(1, 0)
            match.update()
        self.assertIs(match.possessor, p1)
        with Gravador() as g:
            self.assertTrue(match.kick(p1, (1, 0)))
        self.assertEqual(g.sons, ["chute"])


class CampanhaTest(unittest.TestCase):
    def test_fase_toca_a_trilha_do_capitulo(self):
        from soulstrike.assets import MUSIC_LAYERS
        from soulstrike.campaign import PHASES, area_music
        match, _ = campanha()
        self.assertEqual(PlayScene(match.game, match).music, area_music(match.phase))
        for phase in PHASES:
            self.assertIn(area_music(phase), MUSIC_LAYERS, phase.key)
        self.assertEqual({area_music(p) for p in PHASES}, {"cap1", "templo", "cap2", "cap3", "cap4"})

    def test_luta_liga_a_camada_de_combate(self):
        match, _ = campanha()
        assets = game().assets
        with mock.patch.object(assets, "music_intensity") as level:
            match.state = "fight"
            match._boss_music()
            level.assert_called_with(1)
            match.state = "clear"
            match._boss_music()
            level.assert_called_with(0)

    def test_chefao_troca_a_musica(self):
        with mock.patch.object(game().assets, "music") as music:
            ChefaoTest._chefe(None)
        music.assert_called_with("boss")                          # Templo Gelado: o chefão do cristal

    def test_levantar_tem_som(self):
        match, _ = campanha()
        pular_intro(match)
        p = match.players[1]
        p.hp = 0
        with Gravador() as g:
            match._revive(p, 0.5)
        self.assertIn("levantar", g.sons)


if __name__ == "__main__":
    unittest.main()


class MotorDeSomTest(unittest.TestCase):
    """Motor de som (soulstrike/som.py): lado da tela, versões, prioridade, música que abaixa e camadas."""

    def setUp(self):
        from soulstrike import som
        self.som = som
        self.mixer = game().assets.mixer
        self.mixer.calm()

    def test_32_canais_e_os_guardados(self):
        import pygame
        if pygame.mixer.get_init():
            self.assertEqual(pygame.mixer.get_num_channels(), self.som.CHANNELS)

    def test_lado_da_tela(self):
        pan = self.som.pan
        self.assertEqual(pan(None, (0, 960)), (1.0, 1.0))
        self.assertEqual(pan(480, (0, 960)), (1.0, 1.0))           # meio: igual nos dois lados
        left, right = pan(0, (0, 960))
        self.assertEqual(left, 1.0)
        self.assertAlmostEqual(right, self.som.PAN_FLOOR)          # canto: o outro lado baixo, não mudo
        left, right = pan(5000, (1000, 960))                        # fora da tela: fica no canto
        self.assertAlmostEqual(left, self.som.PAN_FLOOR)
        self.assertEqual(right, 1.0)

    def test_som_com_lugar_sai_do_lado_certo(self):
        sound, channel = mock.Mock(), mock.Mock()
        sound.get_num_channels.return_value = 0
        sound.play.return_value = channel
        self.mixer.listen(0, 960)
        with mock.patch.dict(self.mixer.sounds, {"teste": sound}):
            game().assets.play("teste", 0.5, at=960)
        left, right = channel.set_volume.call_args[0]
        self.assertLess(left, right)

    def test_versoes_do_mesmo_som(self):
        for name in ("hit", "shoot", "golpe", "chute"):
            self.assertIn(name, self.mixer.variants, name)
            self.assertGreaterEqual(len(self.mixer.variants[name]), 3, name)
        picked = {id(self.mixer.pick("hit")) for _ in range(60)}
        self.assertGreater(len(picked), 1)

    def test_limite_conta_as_versoes_juntas(self):
        a, b = mock.Mock(), mock.Mock()
        a.get_num_channels.return_value = 2
        b.get_num_channels.return_value = 1
        with mock.patch.dict(self.mixer.variants, {"teste": [a, b]}), mock.patch.dict(self.mixer.sounds, {"teste": a}):
            self.assertIsNone(self.mixer.play("teste"))
        a.play.assert_not_called()
        b.play.assert_not_called()

    def test_som_importante_usa_canal_guardado(self):
        sound, channel = mock.Mock(), mock.Mock()
        sound.get_num_channels.return_value = 0
        with mock.patch.dict(self.mixer.sounds, {"gol_rede": sound}), \
                mock.patch.object(self.mixer, "_priority_channel", return_value=channel):
            self.mixer.play("gol_rede")
        channel.play.assert_called_once_with(sound)
        sound.play.assert_not_called()
        self.assertTrue(self.som.is_priority("comemora_ginga"))
        self.assertFalse(self.som.is_priority("shoot"))

    def test_explosao_abaixa_a_musica_e_ela_volta(self):
        full = self.mixer.music_volume()
        sound = mock.Mock()
        sound.get_num_channels.return_value = 0
        with mock.patch.dict(self.mixer.sounds, {"teste_estrondo": sound}), \
                mock.patch.dict(self.som.DUCK, {"teste_estrondo": self.som.DUCK["explosion"]}):
            self.mixer.play("teste_estrondo")
        self.assertLess(self.mixer.music_volume(), full)
        for _ in range(200):
            self.mixer.tick()
        self.assertAlmostEqual(self.mixer.music_volume(), full)

    def test_abaixar_mais_fundo_vence(self):
        self.mixer.duck_music(0.2, 10)
        self.mixer.duck_music(0.6, 5)
        self.assertAlmostEqual(self.mixer.duck, 0.6)
        self.mixer.duck_music(0.1, 40)                               # mais raso não sobe a música
        self.assertAlmostEqual(self.mixer.duck, 0.6)

    def test_camadas_ligam_aos_poucos(self):
        m = self.som.Mixer()
        m.layers = [mock.Mock(), mock.Mock(), mock.Mock()]
        m.layer_level = [1.0, 0.0, 0.0]
        m._layer_fade = 1.0
        m.set_intensity(1)
        m.tick()
        self.assertGreater(m.layer_level[1], 0.0)
        self.assertLess(m.layer_level[1], 1.0)
        for _ in range(200):
            m.tick()
        self.assertEqual(m.layer_level, [1.0, 1.0, 0.0])
        m.set_intensity(9)                                           # passa do topo: fica na última
        self.assertEqual(m.intensity, 2)
        m.set_intensity(0)
        for _ in range(400):
            m.tick()
        self.assertEqual(m.layer_level, [1.0, 0.0, 0.0])

    def test_pausa_cala_as_camadas(self):
        m = self.som.Mixer()
        m.layers = [mock.Mock()]
        m.layer_level = [1.0]
        m._layer_fade = 1.0
        m.paused = True
        self.assertEqual(m.music_volume(), 0.0)

    def test_vinheta_abaixa_a_musica(self):
        sound, channel = mock.Mock(), mock.Mock()
        sound.get_length.return_value = 2.0
        with mock.patch.dict(self.mixer.sounds, {"vinheta_teste": sound}), \
                mock.patch.object(self.mixer, "_priority_channel", return_value=channel):
            game().assets.stinger("vinheta_teste")
        channel.play.assert_called_once_with(sound)
        self.assertGreater(self.mixer.duck, 0.5)
        self.mixer.calm()

    def test_partida_diz_onde_esta_a_tela(self):
        match, _ = futebol()
        self.mixer.ear = None
        match.update()
        self.assertIsNotNone(self.mixer.ear)


class TrilhaTest(unittest.TestCase):
    """Faixas novas (tools/gerar_trilha.py): arquivos, camadas do chefão final e vinhetas."""

    def test_camadas_existem_e_tem_o_mesmo_tamanho(self):
        from soulstrike.assets import MUSIC_LAYERS
        import pygame
        for name, files in MUSIC_LAYERS.items():
            sizes = set()
            for f in files:
                path = config.SOUNDS_DIR / f
                self.assertTrue(path.is_file(), f)
                if pygame.mixer.get_init():
                    sizes.add(round(pygame.mixer.Sound(str(path)).get_length(), 2))
            self.assertLessEqual(len(sizes), 1, name)              # tocam juntas, em sincronia

    def test_vinhetas_carregam(self):
        sounds = game().assets.sounds
        import pygame
        if pygame.mixer.get_init():
            for name in ("vinheta_vitoria", "vinheta_derrota", "vinheta_chefe", "vinheta_fase"):
                self.assertIn(name, sounds, name)

    def test_vinheta_sem_arquivo_toca_o_som_antigo(self):
        assets = game().assets
        with mock.patch.object(assets.mixer, "stinger", return_value=None), Gravador() as g:
            assets.fanfare("vinheta_que_nao_existe", "victory")
        self.assertEqual(g.sons, ["victory"])

    def test_chefe_final_tem_musica_em_camadas_que_cresce(self):
        from test_mansao import masmorra
        from soulstrike.campaign import BOSS_MUSIC
        self.assertEqual(BOSS_MUSIC["cauanzera"], "boss_final")
        match = masmorra("mansao_gabinete", 3)
        assets = game().assets
        with mock.patch.object(assets, "music") as music, mock.patch.object(assets, "music_intensity") as level, \
                mock.patch.object(assets, "stinger") as stinger:
            match._spawn("chefe", 800, 360)
            music.assert_called_with("boss_final")
            stinger.assert_called_with("vinheta_chefe")
            brain = match.controllers[match.boss]
            brain.stage = 2
            match._boss_music()
            level.assert_called_with(1)
            stinger.assert_called_with("vinheta_fase", 0.6)
            brain.stage = 4
            match._boss_music()
            level.assert_called_with(2)

    def test_chefe_comum_cresce_com_a_raiva(self):
        match, boss, ai = ChefaoTest()._chefe()
        assets = game().assets
        with mock.patch.object(assets, "music_intensity") as level, mock.patch.object(assets, "stinger"):
            ai.enraged = True
            match._boss_music()
        level.assert_called_with(1)

    def test_musica_em_camadas_toca_de_verdade(self):
        import pygame
        if not pygame.mixer.get_init():
            self.skipTest("sem áudio")
        assets = game().assets
        assets._music = None
        assets.music("boss_final")
        self.assertEqual(len(assets.mixer.layers), 3)
        self.assertTrue(pygame.mixer.Channel(3).get_busy())
        assets.music_intensity(2)
        self.assertEqual(assets.mixer.intensity, 2)
        assets.stop_music(0)
        assets.mixer.stop_layers(0)
        self.assertEqual(assets.mixer.layers, [])


class TrilhaDasTelasTest(unittest.TestCase):
    """Cada lugar com a sua faixa: arena, futebol, basquete, pênaltis, Casa, garagem, City e plantão."""

    def test_cada_lugar_tem_faixa(self):
        from soulstrike.assets import MUSIC_FILES
        from soulstrike.basketball import BasketballMatch
        from soulstrike.casa import HubMatch
        from soulstrike.garagem import GarageMatch
        from soulstrike.matches import BattleMatch, SoccerMatch
        from soulstrike.scenes.penalty import PenaltyScene
        from soulstrike.scenes.plantao import ArchiveScene, NewsScene
        from soulstrike.scenes.viagem import CarTripScene
        esperado = {BattleMatch: "arena", SoccerMatch: "futebol", BasketballMatch: "basquete", HubMatch: "casa",
                    GarageMatch: "garagem", CarTripScene: "city", NewsScene: "plantao", ArchiveScene: "plantao"}
        for cls, name in esperado.items():
            self.assertEqual(cls.music, name, cls.__name__)
            self.assertIn(name, MUSIC_FILES)
        self.assertEqual(PenaltyScene.music, "penaltis")

    def test_musicas_antigas_sairam(self):
        for old in ("bgm.ogg", "battle_bgm.mp3", "camp_bgm.ogg", "boss_bgm.ogg", "boss_lag_bgm.ogg"):
            self.assertFalse((config.SOUNDS_DIR / old).is_file(), old)

    def test_gol_toca_a_vinheta(self):
        match, _ = futebol()
        with mock.patch.object(game().assets, "fanfare") as fanfare:
            match._goal(0)
        fanfare.assert_called_with("vinheta_gol", "victory")
