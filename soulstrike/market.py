"""Mercado da campanha: almas, a loja e o ferreiro.

Cada inimigo derrotado solta almas, que vão para o grupo todo (ninguém briga por elas). Na volta
da Masmorra 1, o acampamento tem duas bancas perto da fogueira: a LOJA (poção, arma sorteada,
trocar as melhorias do fim da fase e continue) e o FERREIRO, que sobe a arma de +1 até +3
(+15% de dano e pente maior a cada nível) e, no +3, põe um encanto: fogo, gelo ou raio.
Perto da banca, ATACAR abre o menu; para cima e para baixo escolhe, ATACAR compra, ESQUIVA fecha.
"""
import math
import random

import pygame

from . import config, theme
from .data import duel_arsenal, rarity_color
from .entities import Entity, Particle, Wall

SOULS = {"comum": 3, "elite": 12, "chefe": 60}      # almas por inimigo derrotado
FORGE_COST = (40, 80, 140)                          # +1, +2, +3
FORGE_DAMAGE = 0.15                                 # dano a mais por nível
FORGE_MAG = 0.2                                     # pente a mais por nível
MAX_LEVEL = len(FORGE_COST)
MAX_REROLLS = 3
ENCHANTS = {
    "fogo": ("FOGO", "queima aos poucos", (250, 140, 60)),
    "gelo": ("GELO", "deixa lento", (150, 212, 240)),
    "raio": ("RAIO", "pula para outro inimigo", (246, 214, 70)),
}
BURN_FRAMES = 2 * config.FPS
BURN_TICK = 20
CHAIN_RANGE = 220
SOUL_COLOR = (200, 170, 255)
STICK = 0.55


def forge_of(fighter, weapon):
    """(nível, encanto) da arma no ferreiro deste lutador."""
    level, enchant = getattr(fighter, "forge", {}).get(weapon.name, (0, None))
    return level, enchant


def weapon_label(fighter, weapon):
    level, enchant = forge_of(fighter, weapon)
    name = weapon.name.upper()
    if level:
        name += f" +{level}"
    if enchant:
        name += f" {ENCHANTS[enchant][0]}"
    return name


def souls_for(kind):
    if kind == "chefe":
        return SOULS["chefe"]
    if kind.startswith("sombra:"):
        return SOULS["elite"]
    from .enemies import CREATURES
    creature = CREATURES.get(kind)
    return SOULS["elite"] if creature is not None and creature.elite else SOULS["comum"]


# ─────────────────────────────────────────────
#  Encantos (chamado quando a arma acerta)
# ─────────────────────────────────────────────
def enchant_hit(owner, weapon, target, match, damage):
    if weapon is None or not getattr(owner, "forge", None):
        return
    _, enchant = forge_of(owner, weapon)
    if enchant == "fogo":
        target.burn(owner, max(1, round(damage * 0.15)), BURN_FRAMES)
    elif enchant == "gelo":
        target.slow(round(1.2 * config.FPS))
    elif enchant == "raio":
        others = [e for e in match.opponents_of(owner) if e is not target and e.alive_in_match
                  and e.distance_to(target) < CHAIN_RANGE]
        if others:
            other = min(others, key=target.distance_to)
            if other.take_damage(max(1, round(damage * 0.5)), target.x, target.y, attacker=owner, match=match):
                from .projectiles import LightningArc
                match.add_effect(LightningArc([(target.x, target.y - 20), (other.x, other.y - 20)]))


# ─────────────────────────────────────────────
#  Bancas
# ─────────────────────────────────────────────
class Stall(Entity):
    """Banca do mercado (loja ou ferreiro)."""

    REACH = 74
    NAMES = {"loja": "LOJA", "ferreiro": "FERREIRO"}

    def __init__(self, kind, x, y):
        super().__init__(x, y)
        self.kind = kind
        self.age = 0
        self.wall = Wall(round(x) - 34, round(y) - 10, 68, 22, visible=False)

    @property
    def sort_y(self):
        return self.y

    def can_use(self, fighter):
        return fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def update(self, match):
        self.age += 1
        if self.kind == "ferreiro" and self.age % 40 == 0:      # faísca da bigorna
            for _ in range(4):
                match.particles.append(Particle(self.x + 14, self.y - 26, random.uniform(-1.6, 1.6),
                                                random.uniform(-2.4, -0.8), (255, 200, 90), 16, 2, gravity=0.12))
        elif self.kind == "loja" and self.age % 60 == 0:
            match.particles.append(Particle(self.x + random.uniform(-20, 20), self.y - 30, 0, -0.5,
                                            SOUL_COLOR, 30, 3))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (10, 8, 12), (sx - 40, sy + 2, 80, 14))
        # postes e toldo listrado
        stripes = ((70, 140, 90), (220, 214, 196)) if self.kind == "loja" else ((150, 50, 46), (60, 52, 60))
        for px in (sx - 32, sx + 28):
            surf.fill((60, 38, 24), (px, sy - 58, 4, 58))
        for k in range(8):
            surf.fill(stripes[k % 2], (sx - 36 + k * 9, sy - 66, 9, 12))
        surf.fill((40, 24, 18), (sx - 36, sy - 54, 72, 2))
        # balcão
        surf.fill((78, 46, 26), (sx - 34, sy - 22, 68, 24))
        surf.fill((128, 78, 42), (sx - 34, sy - 24, 68, 6))
        surf.fill((160, 104, 58), (sx - 34, sy - 24, 68, 2))
        if self.kind == "loja":
            for k, color in enumerate(((210, 60, 60), (110, 170, 255), (210, 60, 60))):    # poções
                x = sx - 20 + k * 14
                surf.fill((230, 230, 240), (x + 2, sy - 34, 4, 3))
                surf.fill(color, (x, sy - 31, 8, 8))
            pulse = 0.5 + 0.5 * math.sin(self.age * 0.1)
            surf.fill(tuple(round(c * (0.6 + 0.4 * pulse)) for c in SOUL_COLOR), (sx + 20, sy - 33, 6, 8))
        else:
            surf.fill((70, 70, 80), (sx + 2, sy - 34, 24, 6))           # bigorna
            surf.fill((110, 110, 124), (sx + 2, sy - 34, 24, 2))
            surf.fill((70, 70, 80), (sx + 10, sy - 28, 8, 4))
            surf.fill((120, 76, 40), (sx - 22, sy - 32, 14, 3))         # martelo
            surf.fill((90, 90, 100), (sx - 12, sy - 36, 6, 8))

    def draw_prompt(self, screen, camera, ui, frame, near):
        sx, sy = camera.to_screen(self.x, self.y - 82)
        ui.text(screen, self.NAMES[self.kind], theme.XS, theme.BRASS, (round(sx), round(sy)))
        if near:
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: ABRIR", theme.XS, color, (round(sx), round(sy) + 12))


# ─────────────────────────────────────────────
#  Menu da banca (um por jogador)
# ─────────────────────────────────────────────
class Entry:
    def __init__(self, label, cost, desc, ok, action, color=theme.BONE):
        self.label, self.cost, self.desc, self.ok, self.action, self.color = label, cost, desc, ok, action, color


class MarketMenu:
    def __init__(self, match, fighter, stall):
        self.match = match
        self.fighter = fighter
        self.stall = stall
        self.index = 0
        self.age = 0
        self._last = 0

    @property
    def run(self):
        return self.match.run

    def entries(self):
        return self._shop() if self.stall.kind == "loja" else self._forge()

    def _shop(self):
        f, run = self.fighter, self.run
        return [
            Entry("POÇÃO DE VIDA", 20, "cura metade da vida", f.hp < f.max_hp, self._potion),
            Entry("ARMA SORTEADA", 30, "uma arma de outro herói cai no chão", True, self._weapon),
            Entry("TROCAR MELHORIAS", 25, "no fim da fase, TROCAR ARMA sorteia de novo",
                  run.rerolls[f.slot] < MAX_REROLLS, self._reroll),
            Entry("CONTINUE", 120, "uma vida a mais para o grupo", run.continues < 3, self._continue),
        ]

    def _forge(self):
        f = self.fighter
        out = []
        for w in f.weapons:
            level, enchant = forge_of(f, w)
            color = rarity_color(w)
            if level >= MAX_LEVEL:
                out.append(Entry(weapon_label(f, w), 0, "no máximo", False, None, color))
            elif level == MAX_LEVEL - 1:
                for key, (name, desc, ecolor) in ENCHANTS.items():
                    out.append(Entry(f"{w.name.upper()} +3 {name}", FORGE_COST[level], desc, True,
                                     lambda w=w, key=key: self._upgrade(w, key), ecolor))
            else:
                out.append(Entry(f"{weapon_label(f, w)} > +{level + 1}", FORGE_COST[level],
                                 "+15% de dano e pente maior", True, lambda w=w: self._upgrade(w), color))
        return out

    # compras
    def _potion(self):
        f = self.fighter
        f.hp = min(f.max_hp, f.hp + f.max_hp // 2)
        self.match.burst(f.x, f.y - 20, theme.MOSS, 14, speed=3)

    def _weapon(self):
        ranged, melee = duel_arsenal()
        held = {w.name for p in self.match.players for w in p.weapons} | {g.weapon.name for g in self.match.ground}
        pool = [w for w in ranged + melee if w.name not in held] or list(ranged + melee)
        s = self.stall
        self.match.drop_weapon(s, random.choice(pool), at=(s.x, s.y + 56), start=(s.x, s.y - 30))

    def _reroll(self):
        self.run.rerolls[self.fighter.slot] += 1

    def _continue(self):
        self.run.continues += 1

    def _upgrade(self, weapon, enchant=None):
        f = self.fighter
        level, _ = forge_of(f, weapon)
        f.forge[weapon.name] = [level + 1, enchant]
        f.clips.pop(weapon, None)                       # pente cheio, já do tamanho novo
        self.match.burst(self.stall.x + 14, self.stall.y - 30, (255, 200, 90), 20, speed=5)
        self.match.camera.shake(3)
        return weapon_label(f, weapon)

    def buy(self):
        entries = self.entries()
        if not entries:
            return False
        e = entries[self.index % len(entries)]
        if not e.ok or e.action is None:
            self.match.assets.play("cancel", 0.3)
            return False
        if self.run.souls < e.cost:
            self.match.popup(self.fighter.x, self.fighter.y - 80, "FALTAM ALMAS", theme.BLOOD)
            self.match.assets.play("cancel", 0.3)
            return False
        self.run.souls -= e.cost
        text = e.action() or e.label
        self.match.popup(self.fighter.x, self.fighter.y - 80, text, e.color)
        self.match.assets.play("select", 0.5)
        return True

    def handle(self, inp):
        """Controle do jogador com o menu aberto. Devolve False quando ele fecha."""
        self.age += 1
        if self.age <= 1:
            return True                     # o ATACAR que abriu não compra
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            self.match.assets.play("cancel", 0.3)
            return False
        _, y = inp.axis()
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        n = len(self.entries())
        if sy and sy != self._last and n:
            self.index = (self.index + sy) % n
            self.match.assets.play("click", 0.3)
        self._last = sy
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

    def draw(self, screen, ui, anchor):
        entries = self.entries()
        f = self.fighter
        w, row = 300, 26
        h = 50 + row * len(entries) + 24
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(60, min(config.SCREEN_H - h - 70, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        ui.panel(screen, rect, fill=theme.INK_2, accent=f.color)
        ui.text(screen, f"{f.label} · {Stall.NAMES[self.stall.kind]}", theme.XS, theme.BONE,
                (rect.x + 10, rect.y + 14), anchor="midleft")
        ui.text(screen, f"{self.run.souls} ALMAS", theme.XS, SOUL_COLOR, (rect.right - 10, rect.y + 14),
                anchor="midright")
        for k, e in enumerate(entries):
            r = pygame.Rect(rect.x + 6, rect.y + 28 + k * row, w - 12, row - 2)
            picked = k == self.index % len(entries)
            if picked:
                screen.fill(theme.INK_3, r)
                pygame.draw.rect(screen, f.color, r, 1)
            afford = e.ok and self.run.souls >= e.cost
            color = e.color if afford else theme.FAINT
            ui.text(screen, e.label, theme.XS, color, (r.x + 6, r.centery), anchor="midleft")
            if e.cost:
                ui.text(screen, str(e.cost), theme.XS, SOUL_COLOR if afford else theme.FAINT,
                        (r.right - 6, r.centery), anchor="midright")
        if entries:
            e = entries[self.index % len(entries)]
            ui.text(screen, e.desc.upper(), theme.XS, theme.MUTED, (rect.centerx, rect.bottom - 26))
        ui.text(screen, "ATACAR: COMPRAR  ESQUIVA: FECHAR", theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 12))
