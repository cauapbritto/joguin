"""Mercado da campanha: almas, a loja e o ferreiro.

Cada inimigo derrotado solta almas. Cada jogador tem a sua carteira: quem deu o golpe final leva
a maior parte e os outros vivos ganham um pouco, para ninguém ficar sem nada. Na volta
da Masmorra 1, o acampamento tem duas bancas perto da fogueira: a LOJA (poção, arma sorteada,
trocar as melhorias do fim da fase e continue) e o FERREIRO, que sobe a arma de +1 até +3
(+15% de dano e pente maior a cada nível) e, no +3, põe um encanto: fogo, gelo ou raio.
Perto da banca, ATACAR abre o menu; para cima e para baixo escolhe, ATACAR compra, ESQUIVA fecha.
Com a banca aberta, o celular do jogador mostra a mesma lista (snapshot) e pede a compra pelo id
fixo de cada linha (Entry.key), em CoopMatch.phone_shop.
"""
import math
import random

import pygame

from . import config, theme
from .data import duel_arsenal, rarity_color
from .entities import Entity, Particle, Wall

SOULS = {"comum": 3, "elite": 12, "chefe": 60}      # almas por inimigo derrotado (quem deu o golpe final)
SHARE = {"comum": 1, "elite": 4, "chefe": 60}       # ... e para cada um dos outros vivos
GIFT = 20                                           # DOAR: almas passadas a um companheiro
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
# desafios da campanha: uma maldição opcional por fase, escolhida no altar do acampamento
CURSES = {
    "rapidos": ("INIMIGOS RÁPIDOS", "inimigos 25% mais rápidos"),
    "fortes": ("INIMIGOS FORTES", "inimigos com 30% mais vida"),
    "sem_vida": ("SEM ITENS DE VIDA", "inimigos não deixam cair vida"),
}
CURSE_SPEED = 1.25
CURSE_HP = 1.3
CURSE_COLOR = (190, 90, 230)
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


def soul_tier(kind):
    """comum, elite ou chefe."""
    if kind == "chefe":
        return "chefe"
    if kind.startswith("sombra:"):
        return "elite"
    from .enemies import CREATURES
    creature = CREATURES.get(kind)
    return "elite" if creature is not None and creature.elite else "comum"


def souls_for(kind):
    return SOULS[soul_tier(kind)]


def soul_split(kind, killer, alive):
    """Quanto cada jogador ganha: {slot: almas}. ``killer`` é o slot de quem deu o golpe final
    (None se o inimigo morreu sem dono: aí todo mundo ganha a parte dos outros)."""
    tier = soul_tier(kind)
    out = {slot: SHARE[tier] for slot in alive}
    if killer is not None:
        out[killer] = SOULS[tier]
    return out


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
    NAMES = {"loja": "LOJA", "ferreiro": "FERREIRO", "altar": "ALTAR DAS MALDIÇÕES"}

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
        elif self.kind == "altar" and self.age % 6 == 0:
            match.particles.append(Particle(self.x + random.uniform(-6, 6), self.y - 36, random.uniform(-0.3, 0.3),
                                            random.uniform(-1.2, -0.6), CURSE_COLOR, 20, 3))
        elif self.kind == "loja" and self.age % 60 == 0:
            match.particles.append(Particle(self.x + random.uniform(-20, 20), self.y - 30, 0, -0.5,
                                            SOUL_COLOR, 30, 3))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (10, 8, 12), (sx - 40, sy + 2, 80, 14))
        if self.kind == "altar":
            surf.fill((40, 36, 48), (sx - 26, sy - 26, 52, 28))         # pedra
            surf.fill((80, 74, 92), (sx - 26, sy - 28, 52, 6))
            surf.fill((60, 54, 70), (sx - 18, sy - 22, 36, 2))
            flick = round(2 * math.sin(self.age * 0.3))
            pygame.draw.polygon(surf, (120, 50, 170), [(sx - 8, sy - 28), (sx, sy - 48 - flick), (sx + 8, sy - 28)])
            pygame.draw.polygon(surf, (220, 170, 255), [(sx - 3, sy - 28), (sx, sy - 38 - flick), (sx + 3, sy - 28)])
            return
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
    """Uma linha do menu. ``key`` é o id fixo que o celular usa para pedir a compra."""

    def __init__(self, label, cost, desc, ok, action, color=theme.BONE, key=None):
        self.label, self.cost, self.desc, self.ok, self.action, self.color = label, cost, desc, ok, action, color
        self.key = key or label


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
        if self.stall.kind == "altar":
            return self._altar()
        return self._shop() if self.stall.kind == "loja" else self._forge()

    def _altar(self):
        run = self.run
        out = []
        for key, (name, desc) in CURSES.items():
            label = ("> " if run.curse == key else "") + name
            out.append(Entry(label, 0, desc + " · +1 melhoria no fim", True,
                             lambda key=key: self._curse(key), CURSE_COLOR, f"maldicao:{key}"))
        out.append(Entry(("> " if run.curse is None else "") + "SEM MALDIÇÃO", 0, "a fase normal", True,
                         lambda: self._curse(None), key="maldicao:nenhuma"))
        return out

    def _curse(self, key):
        self.run.curse = key
        self.match.camera.shake(3 if key else 0)
        return CURSES[key][0] if key else "SEM MALDIÇÃO"

    def _shop(self):
        f, run = self.fighter, self.run
        return [
            Entry("POÇÃO DE VIDA", 20, "cura metade da vida", f.hp < f.max_hp, self._potion, key="pocao"),
            Entry("ARMA SORTEADA", 30, "uma arma de outro herói cai no chão", True, self._weapon, key="arma"),
            Entry("TROCAR MELHORIAS", 25, "no fim da fase, TROCAR ARMA sorteia de novo",
                  run.rerolls[f.slot] < MAX_REROLLS, self._reroll, key="trocar"),
            Entry("CONTINUE", 120, "uma vida a mais para o grupo", run.continues < 3, self._continue,
                  key="continue"),
        ] + [Entry(f"DOAR {GIFT} > {m.label}", GIFT, f"passa {GIFT} almas para {m.label}", True,
                   lambda m=m: self._gift(m), m.color, f"doar:{m.slot}")
             for m in self.match.players if m is not f]

    def _forge(self):
        f = self.fighter
        out = []
        for w in f.weapons:
            level, enchant = forge_of(f, w)
            color = rarity_color(w)
            if level >= MAX_LEVEL:
                out.append(Entry(weapon_label(f, w), 0, "no máximo", False, None, color, f"max:{w.name}"))
            elif level == MAX_LEVEL - 1:
                for key, (name, desc, ecolor) in ENCHANTS.items():
                    out.append(Entry(f"{w.name.upper()} +3 {name}", FORGE_COST[level], desc, True,
                                     lambda w=w, key=key: self._upgrade(w, key), ecolor, f"encanto:{w.name}:{key}"))
            else:
                out.append(Entry(f"{weapon_label(f, w)} > +{level + 1}", FORGE_COST[level],
                                 "+15% de dano e pente maior", True, lambda w=w: self._upgrade(w), color,
                                 f"forja:{w.name}:{level + 1}"))
        fusion = self._fusion_entry()
        if fusion is not None:
            out.append(fusion)
        return out

    def _fusion_entry(self):
        """Fusão: as três armas viram uma forjada (uma vez por mercado; a forjada não entra em outra)."""
        from .forged import FORGED, FUSION_COST, discovered, preview_text, recipe
        f, run = self.fighter, self.run
        if f.relic is None or f.relic.forjada:
            return None
        key, level, _ = recipe(f.weapons)
        name, _ = preview_text(key, discovered())
        done = run.fused_phase == run.phase_index
        desc = "só uma fusão por mercado" if done else f"sai: {name}" + (f" +{level}" if level else "")
        return Entry("FUNDIR AS 3 ARMAS", FUSION_COST, desc, not done, self._fuse, rarity_color(FORGED[key]),
                     "fundir")

    def _fuse(self):
        from .forged import FORGED, discover, recipe
        f, run = self.fighter, self.run
        key, level, enchant = recipe(f.weapons)
        weapon = FORGED[key]
        for w in f.base_weapons:
            f.forge.pop(w.name, None)               # as do herói voltam ao +0
        if f.relic is not None:
            f.forge.pop(f.relic.name, None)
        f.give_relic(weapon)
        run.relics[f.slot] = key
        if level:
            f.forge[weapon.name] = [level, enchant]
        run.fused_phase = run.phase_index
        discover(key)
        m = self.match
        for k in range(3):
            m.burst(self.stall.x + 14, self.stall.y - 30, rarity_color(weapon), 24, speed=6 + k)
        m.camera.shake(8)
        m.assets.play("bau", 0.6)
        return weapon_label(f, weapon)

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

    def _gift(self, mate):
        self.run.earn(mate.slot, GIFT)
        self.match.popup(mate.x, mate.y - 80, f"+{GIFT} ALMAS", SOUL_COLOR)
        self.match.assets.play("alma", 0.4)
        return f"DOOU {GIFT} PARA {mate.label}"

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
        if not self.run.spend(self.fighter.slot, e.cost):
            self.match.popup(self.fighter.x, self.fighter.y - 80, "FALTAM ALMAS", theme.BLOOD)
            self.match.assets.play("cancel", 0.3)
            return False
        text = e.action() or e.label
        self.match.popup(self.fighter.x, self.fighter.y - 80, text, e.color)
        self.match.assets.play("compra" if e.cost else "select", 0.5)
        return True

    def pick(self, key):
        """Marca a linha de id ``key`` (pedido do celular). False se ela não está mais no menu."""
        for k, e in enumerate(self.entries()):
            if e.key == key:
                if self.index % max(1, len(self.entries())) != k:
                    self.match.assets.play("click", 0.3)
                self.index = k
                return True
        return False

    def snapshot(self):
        """O menu como o celular mostra: título, saldo, itens e qual está marcado."""
        entries = self.entries()
        wallet = self.run.wallet(self.fighter.slot)
        picked = entries[self.index % len(entries)].key if entries else None
        return {
            "kind": self.stall.kind,
            "title": Stall.NAMES[self.stall.kind],
            "souls": wallet,
            "picked": picked,
            "mates": [{"slot": m.slot, "label": m.label, "name": m.stats.name.upper(),
                       "souls": self.run.wallet(m.slot)}
                      for m in self.match.players if m is not self.fighter],
            "items": [{"id": e.key, "label": e.label, "cost": e.cost, "desc": e.desc,
                       "ok": bool(e.ok and e.action is not None), "afford": wallet >= e.cost,
                       "color": "#%02x%02x%02x" % tuple(e.color[:3])} for e in entries],
        }

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
        ui.text(screen, f"{self.run.wallet(f.slot)} ALMAS", theme.XS, SOUL_COLOR, (rect.right - 10, rect.y + 14),
                anchor="midright")
        for k, e in enumerate(entries):
            r = pygame.Rect(rect.x + 6, rect.y + 28 + k * row, w - 12, row - 2)
            picked = k == self.index % len(entries)
            if picked:
                screen.fill(theme.INK_3, r)
                pygame.draw.rect(screen, f.color, r, 1)
            afford = e.ok and self.run.wallet(f.slot) >= e.cost
            color = e.color if afford else theme.FAINT
            ui.text(screen, e.label, theme.XS, color, (r.x + 6, r.centery), anchor="midleft")
            if e.cost:
                ui.text(screen, str(e.cost), theme.XS, SOUL_COLOR if afford else theme.FAINT,
                        (r.right - 6, r.centery), anchor="midright")
        if entries:
            e = entries[self.index % len(entries)]
            ui.text(screen, e.desc.upper(), theme.XS, theme.MUTED, (rect.centerx, rect.bottom - 26))
        ui.text(screen, "ATACAR: COMPRAR  ESQUIVA: FECHAR", theme.XS, theme.FAINT, (rect.centerx, rect.bottom - 12))
