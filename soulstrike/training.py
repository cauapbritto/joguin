"""Treino: o jogador contra um boneco parado, com uma lição por vez na tela.

Ninguém perde: quem fica com pouca vida volta a encher, o relógio não anda e os itens só
aparecem quando a lição pede. Cada lição termina quando o jogador faz o que ela diz.
"""
import math

import pygame

from . import config, hud, theme
from .ai import FighterAI
from .controls import key_label, move_label
from .entities import Pickup
from .matches import BattleMatch

REFILL_AT = 0.5             # vida abaixo disso (de qualquer um) enche de novo
MOVE_FRAMES = 40            # andando por tanto tempo = aprendeu a andar
DONE_FRAMES = 70            # "MUITO BEM!" fica na tela antes da próxima lição


class DummyAI(FighterAI):
    """O boneco de treino: fica parado e não ataca."""

    def update(self, me, target, match):
        me.steer(0, 0)


def _keys(match, row_id):
    """Rótulo do botão para o jogador 1 (teclado, controle ou celular)."""
    device = match.game.device_of(1)
    if device == "CONTROLE":
        return {"attack": "A", "special": "X", "dodge": "B", "switch": "Y", "move": "O ANALÓGICO"}[row_id]
    if device == "CELULAR":
        return {"attack": "ATACAR", "special": "HABILIDADE", "dodge": "ESQUIVA", "switch": "TROCAR",
                "move": "O ANALÓGICO"}[row_id]
    return move_label(1) if row_id == "move" else key_label(1, row_id)


class Lesson:
    def __init__(self, text, done, item=False):
        self.text = text            # função (match) -> texto (as teclas podem ter sido trocadas)
        self.done = done            # função (match, progresso) -> bool
        self.item = item            # a lição põe um item na arena


LESSONS = (
    Lesson(lambda m: f"ANDE PELA ARENA COM {_keys(m, 'move')}",
           lambda m, st: st["moved"] >= MOVE_FRAMES),
    Lesson(lambda m: f"SEGURE {_keys(m, 'attack')} PARA ATACAR O BONECO",
           lambda m, st: m.player.damage_dealt > st["dealt"]),
    Lesson(lambda m: f"{_keys(m, 'switch')} TROCA DE ARMA: TIRO OU CORPO A CORPO",
           lambda m, st: m.player.weapon_index != st["weapon"]),
    Lesson(lambda m: "AGORA ACERTE O BONECO COM ESSA ARMA",
           lambda m, st: m.player.damage_dealt > st["dealt"]),
    Lesson(lambda m: f"{_keys(m, 'dodge')} DÁ UMA ESQUIVA (NO TECLADO, TAMBÉM 2 TOQUES NA SETA)",
           lambda m, st: m.player.dash_timer > 0),
    Lesson(lambda m: f"{_keys(m, 'special')} USA A HABILIDADE: {m.player.stats.ability_name.upper()}",
           lambda m, st: m.player.ability_cd > st["ability_cd"]),
    Lesson(lambda m: "PEGUE O ITEM QUE APARECEU NA ARENA",
           lambda m, st: not m.pickups, item=True),
)


class TrainingMatch(BattleMatch):
    """Treino (modo "treino"): P1 e o boneco, sem rounds de verdade."""

    def __init__(self, game, session):
        super().__init__(game, session)
        self.player = next(f for f in self.fighters if not f.is_cpu)
        self.dummy = next(f for f in self.fighters if f.is_cpu)
        self.lesson = 0
        self.done_timer = 0
        self.state = {}
        self._begin_lesson()

    def _add_player(self, setup, pos, team=None, color=None):
        fighter = super()._add_player(setup, pos, team=team, color=color)
        if setup.cpu:
            fighter.full_name = "BONECO DE TREINO"
            self.controllers[fighter] = DummyAI(self.session.difficulty)
        return fighter

    @property
    def finished_lessons(self):
        return self.lesson >= len(LESSONS)

    def _begin_lesson(self):
        p = self.player
        self.state = {"moved": 0, "dealt": p.damage_dealt, "weapon": p.weapon_index,
                      "ability_cd": p.ability_cd}
        if not self.finished_lessons and LESSONS[self.lesson].item:
            self._spawn_pickup()

    def _spawn_pickup(self):
        p = self.player
        for _ in range(30):
            x, y = self.arena.random_free_spot(16)
            d = self.dummy
            if 140 < math.hypot(p.x - x, p.y - y) < 420 and math.hypot(d.x - x, d.y - y) > 80:
                break
        self.pickups.append(Pickup("vida", x, y))
        self.burst(x, y - 10, Pickup.KINDS["vida"][1], 10, speed=2)

    def step(self):
        self.pickup_timer = 10 ** 9                               # itens só quando a lição pede
        for f in self.fighters:
            if f.alive_in_match and f.hp < f.max_hp * REFILL_AT:
                f.hp = f.max_hp
                self.popup(f.x, f.y - 70, "VIDA CHEIA", theme.MOSS)
        super().step()
        self.time_left = config.ROUND_SECONDS * config.FPS       # o relógio não anda
        self._check_lesson()

    def _check_lesson(self):
        if self.finished_lessons or not self.active:
            return
        if self.done_timer:
            self.done_timer -= 1
            if self.done_timer == 0:
                self.lesson += 1
                if not self.finished_lessons:
                    self._begin_lesson()
                else:
                    self.assets.play("victory", 0.5)
            return
        if math.hypot(*self.player.input) > 0.2:
            self.state["moved"] += 1
        if LESSONS[self.lesson].done(self, self.state):
            self.done_timer = DONE_FRAMES
            self.assets.play("confirm", 0.5)

    def _end_round(self, winner, reason):
        """No treino ninguém perde: quem cair levanta na hora."""
        for f in self.fighters:
            if f.hp <= 0:
                f.reset_round(*self.starts[f])

    def draw(self, screen, ui):
        super().draw(screen, ui)
        W, H = config.SCREEN_W, config.SCREEN_H
        panel = pygame.Rect(0, 0, W - 160, 52)
        panel.midbottom = (W // 2, H - 12)
        ui.panel(screen, panel, fill=theme.INK_2)
        if self.finished_lessons:
            title, text, color = "TREINO COMPLETO!", "CONTINUE TREINANDO OU APERTE ESC E SAIA PARA O MENU", theme.MOSS
        elif self.done_timer:
            title, text, color = "MUITO BEM!", LESSONS[self.lesson].text(self), theme.MOSS
        else:
            title = f"LIÇÃO {self.lesson + 1} DE {len(LESSONS)}"
            text, color = LESSONS[self.lesson].text(self), theme.BRASS
        ui.text(screen, title, theme.XS, color, (panel.x + 16, panel.y + 16), anchor="midleft")
        ui.text(screen, text, theme.XS, theme.BONE, (panel.x + 16, panel.y + 36), anchor="midleft")
        if not self.finished_lessons:
            done = self.lesson + (1 if self.done_timer else 0)
            bar = pygame.Rect(0, 0, 120, 8)
            bar.midright = (panel.right - 16, panel.y + 16)
            ui.bar(screen, bar, done / len(LESSONS), theme.MOSS, ticks=len(LESSONS))

    def draw_hud(self, screen, ui):
        hud.draw_battle(screen, ui, self)

    def _finish(self):
        self.finished = False                  # o treino só acaba pela pausa
