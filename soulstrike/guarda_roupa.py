"""Os 4 ARMÁRIOS da Casa (um por jogador, P1 a P4): onde se veste a skin.

A loja de CACOS (soulstrike/loja.py) só desbloqueia a skin. Para vestir, cada jogador vai até o
armário com o número dele, aperta ATACAR e escolhe a roupa do herói que está jogando: a de sempre
ou uma das skins que a turma já tem. A skin fica no herói (quem jogar com ele aparece com ela).

Armário piscando = o seu herói tem skin nova esperando para ser vestida.
"""
import math

import pygame

from . import cacos, config, theme
from .entities import Entity, Wall
from .loja import HERO_NAMES, STICK, ShopMenu
from .skins import CACO_COLOR, SKINS, draw_back, draw_caco, draw_front, for_hero

SLOTS = 4
W, H, GAP = 44, 84, 6          # cada armário (px no chão do quintal)
REACH = 46


def _new_for(hero):
    """O herói tem skin que a turma já ganhou e ninguém vestiu ainda?"""
    owned = cacos.owned()
    return cacos.worn(hero) is None and any(s.key in owned for s in for_hero(hero))


class Lockers(Entity):
    """A fileira dos 4 armários de metal, cada um com a faixa da cor do jogador."""

    def __init__(self, x, y):
        super().__init__(x, y)                      # (x, y): meio da fileira, pé no chão
        self.age = 0
        total = SLOTS * W + (SLOTS - 1) * GAP
        self.left = round(x) - total // 2
        self.wall = Wall(self.left, round(y) - 14, total, 16, visible=False)
        self.labels = {}
        self.open = set()                           # armários com o menu aberto (porta aberta)
        self.glow = set()                           # armários de quem tem skin nova esperando
        self.here = set()                           # jogadores ativos (os outros armários ficam apagados)

    def bake_labels(self, ui):
        for slot in range(1, SLOTS + 1):
            img = pygame.Surface((24, 12), pygame.SRCALPHA)
            ui.text(img, f"P{slot}", theme.XS, theme.INK, (12, 6), shadow=False)
            self.labels[slot] = img

    @property
    def sort_y(self):
        return self.y

    def spot(self, slot):
        """Ponto na frente do armário ``slot`` (onde o jogador para)."""
        return self.left + (slot - 1) * (W + GAP) + W // 2, round(self.y) + 22

    def near(self, f):
        """O número do armário na frente de ``f`` (ou None)."""
        if not f.alive_in_match:
            return None
        best = None
        for slot in range(1, SLOTS + 1):
            x, y = self.spot(slot)
            d = math.hypot(f.x - x, f.y - y)
            if d < REACH and (best is None or d < best[0]):
                best = (d, slot)
        return None if best is None else best[1]

    def update(self, match):
        self.age += 1
        self.open = {m.fighter.slot for m in match.menus.values() if isinstance(m, WardrobeMenu)}
        self.here = {p.slot for p in match.players}
        if self.age % 20 == 1:
            self.glow = {p.slot for p in match.players if _new_for(p.stats.key)}

    def draw(self, surf, camera):
        sx0, sy = round(self.left - camera.x), round(self.y - camera.y)
        total = SLOTS * W + (SLOTS - 1) * GAP
        surf.fill((0, 0, 0), (sx0 - 4, sy - 4, total + 8, 8))                 # sombra no chão
        for slot in range(1, SLOTS + 1):
            x = sx0 + (slot - 1) * (W + GAP)
            body = pygame.Rect(x, sy - H, W, H)
            used = slot in self.here
            metal = (96, 110, 134) if used else (70, 76, 92)
            dark = (58, 66, 84) if used else (46, 50, 62)
            surf.fill((24, 26, 34), body.inflate(4, 2))
            surf.fill(metal, body)
            surf.fill(dark, (body.right - 4, body.y, 4, body.height))           # lateral na sombra
            surf.fill((140, 154, 176) if used else (90, 96, 110), (body.x, body.y, body.width, 2))
            color = theme.SLOT_COLORS[slot] if used else theme.SLOT_COLORS_DARK[slot]
            surf.fill(color, (body.x, body.y + 4, body.width, 14))              # faixa com o número
            label = self.labels.get(slot)
            if label is not None:
                surf.blit(label, label.get_rect(center=(body.centerx, body.y + 11)))
            door = pygame.Rect(body.x + 3, body.y + 21, body.width - 8, body.height - 24)
            if slot in self.open:                                               # porta aberta: cabide e roupa
                surf.fill((20, 20, 28), door)
                pygame.draw.line(surf, (200, 200, 210), (door.x + 4, door.y + 8), (door.right - 4, door.y + 8), 1)
                pygame.draw.polygon(surf, color, [(door.centerx - 9, door.y + 12), (door.centerx + 9, door.y + 12),
                                                  (door.centerx + 7, door.y + 38), (door.centerx - 7, door.y + 38)])
                surf.fill(metal, (door.right - 2, door.y, 10, door.height))     # a porta virada para fora
            else:
                pygame.draw.rect(surf, dark, door, 1)
                for k in range(3):                                              # frestas de ventilação
                    surf.fill(dark, (door.x + 8, door.y + 6 + k * 5, door.width - 16, 2))
                surf.fill((210, 214, 224), (door.right - 7, door.centery - 6, 3, 12))   # puxador
            if slot in self.glow and slot not in self.open:                      # skin nova esperando
                if (self.age // 15) % 2:
                    pygame.draw.rect(surf, CACO_COLOR, body.inflate(4, 4), 2)
                draw_caco(surf, body.centerx, body.y - 12 + math.sin(self.age * 0.1) * 2, self.age)


class WardrobeMenu(ShopMenu):
    """O armário aberto: as roupas do herói que o jogador está usando, uma carta por roupa."""

    kind = "armario"

    def __init__(self, match, fighter):
        super().__init__(match, fighter)
        self.page = "skins"
        worn = cacos.worn(self.hero)
        self.index = next((i for i, (k, _) in enumerate(self.entries()) if k == worn), 0)

    def entries(self):
        return [("base", None)] + [(s.key, s) for s in for_hero(self.hero)]

    def current(self):
        rows = self.entries()
        return rows[self.index % len(rows)]

    def state(self, skin):
        """"vestida", "vestir", "comprar" (na loja) ou "cupom"."""
        worn = cacos.worn(self.hero)
        if skin is None:
            return "vestida" if worn is None else "vestir"
        if skin.key in cacos.owned():
            return "vestida" if worn == skin.key else "vestir"
        return "comprar" if skin.price else "cupom"

    def buy(self):
        key, skin = self.current()
        play = self.match.assets.play
        state = self.state(skin)
        if state == "vestida":
            self._say("JÁ ESTÁ VESTIDA", theme.BONE)
            play("click", 0.3)
            return False
        if state in ("comprar", "cupom"):
            self._say("ESSA AINDA NÃO É SUA: " + ("COMPRE NA LOJA DE CACOS" if state == "comprar"
                                                 else "SÓ SAI POR CUPOM, NA LOJA"), theme.BLOOD)
            play("cancel", 0.3)
            return False
        cacos.wear(self.hero, None if skin is None else skin.key)
        self.match.redress()
        name = HERO_NAMES.get(self.hero, "")
        self._say(f"{name} VESTIU!" if skin else "DE VOLTA À ROUPA DE SEMPRE", theme.MOSS)
        f = self.fighter
        self.match.burst(f.x, f.y - 30, skin.color if skin else theme.BONE, 18, speed=2.5)
        play("select", 0.5)
        return True

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                       # o ATACAR que abriu não veste
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            self.match.assets.play("cancel", 0.3)
            return False
        x, _ = inp.axis()
        sx = 1 if x > STICK else -1 if x < -STICK else 0
        moved = sx != self._last[0] and sx
        self._last = (sx, 0)
        if moved:
            self.index = (self.index + sx) % len(self.entries())
            self.match.assets.play("click", 0.3)
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

    def pick(self, key):
        for i, (k, _) in enumerate(self.entries()):
            if k == key:
                if i != self.index:
                    self.match.assets.play("click", 0.3)
                self.index = i
                return True
        return False

    # ── celular ──────────────────────────────
    def snapshot(self):
        key, skin = self.current()
        items = []
        for k, s in self.entries():
            state = self.state(s)
            tag = {"vestida": "VESTIDA", "vestir": "VESTIR", "comprar": "NA LOJA", "cupom": "CUPOM"}[state]
            items.append({
                "id": k, "label": s.name if s else "ROUPA DE SEMPRE", "cost": 0,
                "desc": s.blurb if s else "O " + HERO_NAMES.get(self.hero, "") + " DE SEMPRE",
                "ok": state != "vestida", "afford": state in ("vestir", "vestida"),
                "color": "#%02x%02x%02x" % (s.color if s else theme.BONE),
                "info": {"type": "skin", "img": f"/skin/{s.key if s else 'base_' + self.hero}.png",
                         "hero": HERO_NAMES.get(self.hero, ""), "tier": s.rarity if s else "base",
                         "state": {"vestida": "tirar", "vestir": "vestir"}.get(state, state), "tag": tag,
                         "sub": {"vestida": "VESTIDA", "vestir": "É SUA", "comprar": "COMPRE NA LOJA",
                                 "cupom": "SÓ COM CUPOM"}[state],
                         "rarity": "ROUPA DE SEMPRE" if s is None else ("RARA" if s.rarity == "rara" else "LOJA")},
            })
        state = self.state(skin)
        action = {"vestida": "VESTIDA", "vestir": "VESTIR", "comprar": "NA LOJA", "cupom": "SÓ COM CUPOM"}[state]
        return {"kind": "armario", "title": "ARMÁRIO · " + HERO_NAMES.get(self.hero, ""), "souls": cacos.balance(),
                "unit": "CACOS", "picked": key, "mates": [], "items": items, "action": action}

    # ── TV ───────────────────────────────────
    def draw(self, screen, ui, anchor):
        f = self.fighter
        rows = self.entries()
        cw, ch, gap = 120, 150, 14
        w = max(540, len(rows) * cw + (len(rows) - 1) * gap + 60)
        h = 300
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(52, min(config.SCREEN_H - h - 64, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        color = theme.SLOT_COLORS.get(f.slot, theme.BONE)
        ui.panel(screen, rect, fill=theme.INK_2, accent=color)
        chip = pygame.Rect(rect.x + 12, rect.y + 10, 30, 20)
        screen.fill(color, chip)
        ui.text(screen, f"P{f.slot}", theme.XS, theme.INK, chip.center, shadow=False)
        ui.text(screen, "ARMÁRIO · " + HERO_NAMES.get(self.hero, ""), theme.S, theme.BONE,
                (rect.x + 52, rect.y + 20), anchor="midleft")
        text, note = self.note
        if text:
            ui.text(screen, text, theme.XS, note, (rect.centerx, rect.y + 44))
        cur = self.index % len(rows)
        x0 = rect.centerx - (len(rows) * cw + (len(rows) - 1) * gap) // 2
        for i, (key, skin) in enumerate(rows):
            card = pygame.Rect(x0 + i * (cw + gap), rect.y + 58, cw, ch)
            on = i == cur
            if on:
                card.move_ip(0, -3)
            self._wardrobe_card(screen, ui, card, skin, on)
        key, skin = rows[cur]
        bar = pygame.Rect(rect.x + 12, rect.y + 58 + ch + 12, w - 24, 46)
        screen.fill((16, 14, 24), bar)
        pygame.draw.rect(screen, theme.LINE, bar, 1)
        name = skin.name if skin else "ROUPA DE SEMPRE"
        ui.text(screen, name, theme.S if len(name) <= 22 else theme.XS, skin.color if skin else theme.BONE,
                (bar.x + 10, bar.y + 14), anchor="midleft")
        sub = skin.blurb if skin else "SEM SKIN: O VISUAL ORIGINAL DO HERÓI"
        button = pygame.Rect(bar.right - 130, bar.y + 8, 120, 30)
        room = button.x - bar.x - 20
        while len(sub) > 8 and ui.assets.text(sub, theme.XS, theme.MUTED).get_width() > room:
            sub = sub[:-2].rstrip(" ,·") + "…"
        ui.text(screen, sub, theme.XS, theme.MUTED, (bar.x + 10, bar.y + 32), anchor="midleft")
        state = self.state(skin)
        label, fill, ink = {"vestida": ("VESTIDA", theme.LINE, theme.MUTED), "vestir": ("VESTIR", theme.MOSS, theme.INK),
                            "comprar": ("NA LOJA", theme.LINE, theme.MUTED),
                            "cupom": ("SÓ COM CUPOM", theme.LINE, theme.MUTED)}[state]
        self._button(screen, ui, button, label, fill, ink)
        if len(rows) == 1:
            hint = "ESSE HERÓI AINDA NÃO TEM SKIN · ESQUIVA: FECHAR"
        else:
            hint = "ANALÓGICO: ESCOLHER · ATACAR: VESTIR · ESQUIVA: FECHAR"
        ui.text(screen, hint, theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 10))

    def _wardrobe_card(self, screen, ui, card, skin, on):
        t = self.match.frame
        state = self.state(skin)
        screen.fill((8, 6, 12), card.move(3, 4))
        if skin is None:
            self._gradient(screen, card, (66, 62, 80), (30, 28, 40))
            sprites = self.match.assets.sprites.get(self.hero)
            tint = theme.BONE
        else:
            self._gradient(screen, card, *((92, 46, 130), (180, 116, 48)) if skin.rarity == "rara"
                           else ((44, 70, 128), (22, 30, 62)))
            sprites = self.match.assets.skin_sprites(skin.key)
            tint = skin.color
        halo = pygame.Surface((card.width, card.width), pygame.SRCALPHA)
        for rad, alpha in ((54, 26), (38, 36), (24, 46)):
            pygame.draw.circle(halo, (*tint, alpha), (card.width // 2, card.width // 2), rad)
        screen.blit(halo, (card.x, card.y + 6))
        if sprites is not None:
            img = sprites.frame("frente", t // 8 if on else 0)
            img = pygame.transform.scale(img, (round(img.get_width() * 1.3), round(img.get_height() * 1.3)))
            spot = img.get_rect(midbottom=(card.centerx, card.bottom - 28))
            pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 22, spot.bottom - 5, 44, 10))
            mine = state in ("vestida", "vestir")
            if on and skin is not None and mine:
                draw_back(screen, skin.key, spot, t)
            if not mine:                                       # ainda não é sua: só a silhueta
                img = img.copy()
                img.fill((20, 18, 30, 255), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, spot)
            if on and skin is not None and mine:
                draw_front(screen, skin.key, spot, t)
        strip = pygame.Rect(card.x, card.bottom - 22, card.width, 22)
        if state == "vestida":
            screen.fill(theme.MOSS, strip)
            ui.text(screen, "VESTIDA", theme.XS, theme.INK, (strip.centerx, strip.centery + 1), shadow=False)
        else:
            screen.fill((14, 12, 22), strip)
            label, ink = {"vestir": ("VESTIR", theme.BONE), "comprar": ("NA LOJA", theme.MUTED),
                          "cupom": ("CUPOM", theme.MUTED)}[state]
            if state in ("comprar", "cupom"):
                self._lock(screen, strip.centerx - 30, strip.centery)
                ui.text(screen, label, theme.XS, ink, (strip.centerx - 20, strip.centery + 1), anchor="midleft")
            else:
                ui.text(screen, label, theme.XS, ink, (strip.centerx, strip.centery + 1))
        self._frame(screen, card, tint, on)
