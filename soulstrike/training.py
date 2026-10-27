"""Treino: o jogador contra um boneco parado, com uma lição por vez na tela.

Ninguém perde: quem fica com pouca vida volta a encher, o relógio não anda e os itens só
aparecem quando a lição pede. Cada lição termina quando o jogador faz o que ela diz.
"""
import math

import pygame

from . import config, hud, theme
from .ai import FighterAI, SoccerAI
from .arsenal import ArsenalPick, WeaponRack
from .controls import key_label, move_label
from .entities import Pickup
from .matches import BattleMatch
from .basket_assist import JUMP_FRAMES

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
        return {"attack": "A", "special": "X", "dodge": "B", "switch": "Y", "move": "O ANALÓGICO",
                "soccer_dodge": "B", "mark": "RB", "sprint": "LB"}[row_id]
    if device == "CELULAR":
        return {"attack": "ATACAR", "special": "HABILIDADE", "dodge": "ESQUIVA", "switch": "TROCAR",
                "move": "O ANALÓGICO", "soccer_dodge": "ESQUIVA", "mark": "MARCAR", "sprint": "CORRER"}[row_id]
    if device in ("CONTROLE", "CELULAR"):
        extra = {"soccer_dodge": "ESQUIVA", "mark": "MARCAR", "sprint": "CORRER"}
        if row_id in extra:
            return extra[row_id]
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
    Lesson(lambda m: f"NO ARSENAL, {_keys(m, 'attack')} ESCOLHE QUALQUER ARMA DO JOGO, ATÉ AS FORJADAS",
           lambda m, st: m.arsenal_picks > st["picks"]),
)


class TrainingMatch(BattleMatch):
    """Treino (modo "treino"): P1 e o boneco, sem rounds de verdade."""

    def __init__(self, game, session):
        super().__init__(game, session)
        self.player = next(f for f in self.fighters if not f.is_cpu)
        self.dummy = next(f for f in self.fighters if f.is_cpu)
        self.rack = self._place_rack()
        self.arsenal_picks = 0
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

    def _place_rack(self):
        """O arsenal fica entre os dois, mais para cima (longe do boneco)."""
        p, d = self.player, self.dummy
        x, y = self.arena.free_spot((p.x + d.x) / 2, min(p.y, d.y) - 140, 44)
        return WeaponRack(x, y)

    def world_entities(self):
        return super().world_entities() + [self.rack]

    def _human(self, fighter, inp, target):
        if (inp.pressed("attack") or inp.pressed("confirm")) and self.rack.can_use(fighter):
            fighter.steer(0, 0)
            self.pick = ArsenalPick(self, fighter)
            self.assets.play("confirm", 0.4)
            return
        super()._human(fighter, inp, target)

    def _begin_lesson(self):
        p = self.player
        self.state = {"moved": 0, "dealt": p.damage_dealt, "weapon": p.weapon_index,
                      "ability_cd": p.ability_cd, "picks": self.arsenal_picks}
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
        pick = self.pick
        self.rack.update(self)
        super().step()
        if isinstance(pick, ArsenalPick) and pick.done and pick.chosen is not None:
            self.arsenal_picks += 1
            name = "ARMAS DO HERÓI" if pick.chosen == ArsenalPick.HERO else pick.chosen.name.upper()
            self.popup(self.player.x, self.player.y - 70, name, theme.BRASS)
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
        if self.pick is not None:
            return                                    # a escolha do arsenal cobre a tela
        self.rack.draw_prompt(screen, self.camera, ui, self.frame, self.rack.can_use(self.player))
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


# ─────────────────────────────────────────────
#  Treino do futebol e do basquete
# ─────────────────────────────────────────────
class Standing(SoccerAI):
    """Os outros jogadores do treino: parados no lugar (no futebol e no basquete)."""

    def update(self, me, match):
        me.steer(0, 0)


SOCCER_LESSONS = (
    Lesson(lambda m: f"{_keys(m, 'soccer_dodge')} DÁ UM CORTE: ARRANCADA CURTA PARA ONDE VOCÊ APONTA",
           lambda m, st: m.player.dash_timer > 0),
    Lesson(lambda m: f"CHEGUE NA BOLA E SEGURE {_keys(m, 'attack')}: SOLTE PARA CHUTAR",
           lambda m, st: m.last_touch is m.player and math.hypot(m.ball.vx, m.ball.vy) > 6),
    Lesson(lambda m: f"SEGURE MAIS {_keys(m, 'attack')} PARA O CHUTE ALTO (PASSA POR CIMA)",
           lambda m, st: m.last_touch is m.player and m.ball.z > 24),
    Lesson(lambda m: f"COM O BONECO NA BOLA, SEGURE {_keys(m, 'mark')} PARA MARCAR",
           lambda m, st: st["marked"] >= MOVE_FRAMES, item="dummy_ball"),
    Lesson(lambda m: "AGORA FAÇA UM GOL NO BONECO",
           lambda m, st: m.score[m.player.team] > st["goals"]),
)

BASKET_LESSONS = (
    Lesson(lambda m: f"COM A BOLA, SEGURE {_keys(m, 'attack')} E SOLTE NO TOPO DO PULO (FAIXA VERDE)",
           lambda m, st: st["green"]),
    Lesson(lambda m: f"COM A BOLA, {_keys(m, 'soccer_dodge')} FAZ A FINTA (TROCA DE MÃO)",
           lambda m, st: m.player.feint_timer > 0),
    Lesson(lambda m: f"O BONECO VAI ARREMESSAR: {_keys(m, 'attack')} SEM A BOLA PULA PARA O TOCO",
           lambda m, st: m.player.blocks > st["blocks"], item="dummy_shot"),
    Lesson(lambda m: "AGORA FAÇA UMA CESTA",
           lambda m, st: m.score[m.player.team] > st["goals"]),
)


class _BallTraining:
    """Treino com bola: P1 e bonecos parados, sem placar que acaba, uma lição por vez."""

    lessons = ()

    def _setup_training(self):
        self.player = next(f for f in self.fighters if not f.is_cpu)
        self.dummy = next(f for f in self.fighters if f.team != self.player.team)
        for f in self.fighters:
            if f.is_cpu:
                f.full_name = "BONECO"
                self.controllers[f] = Standing()
        self.lesson = 0
        self.done_timer = 0
        self.script = 0
        self._begin_lesson()

    @property
    def finished_lessons(self):
        return self.lesson >= len(self.lessons)

    def _begin_lesson(self):
        p = self.player
        self.state = {"marked": 0, "goals": self.score[p.team], "blocks": p.blocks if hasattr(p, "blocks") else 0,
                      "green": False}
        self.script = 0
        if not self.finished_lessons and self.lessons[self.lesson].item == "dummy_ball":
            self._give_dummy()

    def _check_lesson(self):
        if self.finished_lessons:
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
        lesson = self.lessons[self.lesson]
        if lesson.done(self, self.state):
            self.done_timer = DONE_FRAMES
            self.assets.play("confirm", 0.5)

    def _finish(self):
        self.finished = False                   # o treino só acaba pela pausa

    def draw_lesson(self, screen, ui):
        W, H = config.SCREEN_W, config.SCREEN_H
        panel = pygame.Rect(0, 0, W - 160, 52)
        panel.midbottom = (W // 2, H - 12)
        ui.panel(screen, panel, fill=theme.INK_2)
        n = len(self.lessons)
        if self.finished_lessons:
            title, text, color = "TREINO COMPLETO!", "CONTINUE TREINANDO OU APERTE ESC E SAIA PARA O MENU", theme.MOSS
        elif self.done_timer:
            title, text, color = "MUITO BEM!", self.lessons[self.lesson].text(self), theme.MOSS
        else:
            title, text, color = f"LIÇÃO {self.lesson + 1} DE {n}", self.lessons[self.lesson].text(self), theme.BRASS
        ui.text(screen, title, theme.XS, color, (panel.x + 16, panel.y + 16), anchor="midleft")
        ui.text(screen, text, theme.XS, theme.BONE, (panel.x + 16, panel.y + 36), anchor="midleft")
        if not self.finished_lessons:
            bar = pygame.Rect(0, 0, 120, 8)
            bar.midright = (panel.right - 16, panel.y + 16)
            ui.bar(screen, bar, (self.lesson + (1 if self.done_timer else 0)) / n, theme.MOSS, ticks=n)


def _soccer_training_class():
    from .matches import SoccerMatch

    class SoccerTrainingMatch(_BallTraining, SoccerMatch):
        """Treino do futebol (corte, chute, chute alto, marcar e gol) contra um boneco parado."""

        lessons = SOCCER_LESSONS

        def __init__(self, game, session):
            super().__init__(game, session)
            self.win_score = None                       # o placar não acaba o treino
            self.clock = 0
            self._setup_training()

        def _give_dummy(self):
            d = self.dummy
            self.ball.x, self.ball.y = d.x + d.facing[0] * 18, d.y + 6
            self.ball.vx = self.ball.vy = 0.0

        def step(self):
            super().step()
            p = self.player
            if not self.finished_lessons and self.lessons[self.lesson].item == "dummy_ball":
                if math.hypot(self.ball.x - self.dummy.x, self.ball.y - self.dummy.y) > 120:
                    self._give_dummy()              # a bola volta para o boneco
                if p.marking and p.distance_to(self.dummy) < 120:
                    self.state["marked"] += 1
            self._check_lesson()

        def draw(self, screen, ui):
            super().draw(screen, ui)
            self.draw_lesson(screen, ui)

    return SoccerTrainingMatch


def _basket_training_class():
    from .basketball import BasketballMatch

    class BasketTrainingMatch(_BallTraining, BasketballMatch):
        """Treino do basquete (barrinha, finta, toco e cesta) com bonecos parados."""

        lessons = BASKET_LESSONS

        def __init__(self, game, session):
            super().__init__(game, session)
            self._setup_training()

        def _give_dummy(self):
            pass

        def release_shot(self, f, timing=None):
            if f is self.player and f.jump_shot:
                t = f.jump / JUMP_FRAMES if timing is None else timing
                if abs(t - 0.5) <= f.shot_half:
                    self.state["green"] = True
            return super().release_shot(f, timing)

        def step(self):
            self.clock = max(self.clock, 60 * config.FPS)      # o relógio não acaba o treino
            self.shot_clock = 0
            super().step()
            if not self.finished_lessons and self.lessons[self.lesson].item == "dummy_shot":
                self._dummy_shot()
            else:
                self._ball_back()
            self._check_lesson()

        def _ball_back(self):
            """Sem o arremesso no ar e a bola longe dele: volta para a mão do jogador."""
            p = self.player
            if self.holder is p or self.shot is not None or p.dunking or self.freeze:
                self.script = 0
                return
            self.script += 1
            if self.script > 45:
                self.script = 0
                self.ball.reset(p.x, p.y)
                self._give(p)

        def _dummy_shot(self):
            """O boneco pega a bola na frente do jogador e arremessa (dá tempo de pular)."""
            self.script -= 1
            d, p = self.dummy, self.player
            if self.script > 0 or self.shot is not None or d.jump:
                return
            hx, hy = self.hoop_pos(self.hoop_of(d.team))
            ux, uy = hx - p.x, hy - p.y
            k = math.hypot(ux, uy) or 1
            d.x, d.y = p.x - ux / k * 50, p.y - uy / k * 50
            self.ball.reset(d.x, d.y)
            self._give(d)
            d.facing = (ux / k, uy / k)
            self.start_shot(d)
            self.script = 150

        def _update_moves(self, f):
            super()._update_moves(f)
            if f is self.dummy and f.jump_shot and f.jump >= JUMP_FRAMES // 2 + 6:
                self.release_shot(f, 0.5)

        def draw(self, screen, ui):
            super().draw(screen, ui)
            self.draw_lesson(screen, ui)

    return BasketTrainingMatch


def create_ball_training(game, session):
    if session.basket:
        return _basket_training_class()(game, session)
    return _soccer_training_class()(game, session)
