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
        self._patch = mock.patch.object(game().assets, "play", side_effect=lambda name, vol=0.5: self.sons.append(name))
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()


class ArquivosTest(unittest.TestCase):
    def test_todo_som_de_arma_existe(self):
        for name in set(SHOT_SOUNDS.values()) | {"shoot", "shoot2", "golpe", "chute", "apito", "torcida", "bau",
                                                  "teletransporte", "levantar", "passo_pesado"}:
            self.assertTrue((config.SOUNDS_DIR / f"{name}.wav").is_file(), name)
            self.assertIn(name, game().assets.sounds, name)

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
    def test_acampamento_tem_musica_calma(self):
        match, _ = acampamento()
        self.assertEqual(PlayScene(match.game, match).music, "camp")

    def test_masmorra_tem_musica_de_batalha(self):
        match, _ = campanha()
        self.assertEqual(PlayScene(match.game, match).music, "battle")

    def test_chefao_troca_a_musica(self):
        with mock.patch.object(game().assets, "music") as music:
            ChefaoTest._chefe(None)
        music.assert_called_with("boss")

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
