"""Os 4 ARMÁRIOS da Casa (um por jogador, P1 a P4): onde se veste a skin e se escolhe o pet.

A loja de CACOS (soulstrike/loja.py) só desbloqueia. Para vestir, cada jogador vai até o armário com
o número dele, aperta ATACAR e escolhe a roupa do herói que está jogando (a de sempre ou uma skin que
a turma já tem) e o pet que vai junto. A skin fica no herói (quem jogar com ele aparece com ela); o
pet fica no jogador (P1 a P4), na Casa e nas fases.

Armário piscando = tem skin nova do seu herói ou pet que ninguém levou esperando.
"""
import math

import pygame

from . import cacos, config, theme
from .entities import Entity, Wall
from .loja import HERO_NAMES, STICK, ShopMenu, pet_image
from .skins import CACO_COLOR, PETS, draw_back, draw_caco, draw_front, for_hero

SLOTS = 4
W, H, GAP = 44, 84, 6          # cada armário (px no chão do quintal)
REACH = 46


def _new_for(hero, slot):
    """Tem coisa nova esperando no armário: skin do herói que ninguém vestiu ou pet que ninguém levou?"""
    owned = cacos.owned()
    if cacos.worn(hero) is None and any(s.key in owned for s in for_hero(hero)):
        return True
    taken = {cacos.pet_of(k) for k in range(1, SLOTS + 1)}
    return cacos.pet_of(slot) is None and bool(cacos.owned_pets() - taken)


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
            self.glow = {p.slot for p in match.players if _new_for(p.stats.key, p.slot)}

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
    """O armário aberto: em cima as roupas do herói que o jogador está usando, embaixo o pet que vai
    junto. Uma carta por opção; o analógico troca de linha (cima/baixo) e de carta (lados)."""

    kind = "armario"
    ROWS = ("ROUPA", "PET")

    def __init__(self, match, fighter):
        self.marks = [0, 0]                   # carta marcada em cada linha
        self.row = 0
        super().__init__(match, fighter)
        self.page = "skins"
        worn = cacos.worn(self.hero)
        self.marks[0] = next((i for i, (k, _) in enumerate(self.line(0)) if k == worn), 0)
        pet = cacos.pet_of(self._slot())
        self.marks[1] = next((i for i, (k, _) in enumerate(self.line(1)) if k == "pet:" + str(pet)), 0)

    # a carta marcada na linha de agora (o ShopMenu chama de index)
    @property
    def index(self):
        return self.marks[self.row] if hasattr(self, "marks") else 0

    @index.setter
    def index(self, value):
        if hasattr(self, "marks"):
            self.marks[self.row] = value

    def line(self, row):
        if row == 0:
            return [("base", None)] + [(s.key, s) for s in for_hero(self.hero)]
        return [("pet:none", None)] + [("pet:" + p.key, p) for p in PETS.values()]

    def entries(self):
        return self.line(self.row)

    def current(self):
        rows = self.entries()
        return rows[self.index % len(rows)]

    def state(self, item, row=None):
        """"vestida", "vestir", "comprar" (na loja) ou "cupom"."""
        row = self.row if row is None else row
        if row == 1:
            pet = cacos.pet_of(self._slot())
            if item is None:
                return "vestida" if pet is None else "vestir"
            if item.key in cacos.owned_pets():
                return "vestida" if pet == item.key else "vestir"
            return "comprar"
        worn = cacos.worn(self.hero)
        if item is None:
            return "vestida" if worn is None else "vestir"
        if item.key in cacos.owned():
            return "vestida" if worn == item.key else "vestir"
        return "comprar" if item.price else "cupom"

    def buy(self):
        key, item = self.current()
        play = self.match.assets.play
        state = self.state(item)
        pet_row = self.row == 1
        if state == "vestida":
            self._say("JÁ ESTÁ COM VOCÊ" if pet_row else "JÁ ESTÁ VESTIDA", theme.BONE)
            play("click", 0.3)
            return False
        if state in ("comprar", "cupom"):
            what = "ESSE AINDA NÃO É SEU" if pet_row else "ESSA AINDA NÃO É SUA"
            self._say(what + ": " + ("COMPRE NA LOJA DE CACOS" if state == "comprar"
                                     else "SÓ SAI POR CUPOM, NA LOJA"), theme.BLOOD)
            play("cancel", 0.3)
            return False
        f = self.fighter
        if pet_row:
            cacos.set_pet(self._slot(), None if item is None else item.key)
            if item is not None:                    # um pet por jogador: o bicho da Casa volta
                from . import mascotes
                mascotes.send_home(self.match, self._slot())
            self.match.refresh_pets()
            self._say(f"O {item.name} VAI COM VOCÊ!" if item else "SEM PET POR ENQUANTO", theme.MOSS)
            self.match.burst(f.x - 30, f.y - 10, item.color if item else theme.BONE, 14, speed=2.5)
        else:
            cacos.wear(self.hero, None if item is None else item.key)
            self.match.redress()
            self._say(f"{HERO_NAMES.get(self.hero, '')} VESTIU!" if item else "DE VOLTA À ROUPA DE SEMPRE", theme.MOSS)
            self.match.burst(f.x, f.y - 30, item.color if item else theme.BONE, 18, speed=2.5)
        play("select", 0.5)
        return True

    def handle(self, inp):
        self.age += 1
        if self.age <= 1:
            return True                       # o ATACAR que abriu não veste
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            self.match.assets.play("cancel", 0.3)
            return False
        x, y = inp.axis()
        sx = 1 if x > STICK else -1 if x < -STICK else 0
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        moved = (sx, sy) != self._last and (sx or sy)
        self._last = (sx, sy)
        if moved:
            if sy:
                self.row = max(0, min(1, self.row + sy))
            elif sx:
                self.index = (self.index + sx) % len(self.entries())
            self.note = ("", theme.BONE)
            self.match.assets.play("click", 0.3)
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

    def pick(self, key):
        for row in (0, 1):
            for i, (k, _) in enumerate(self.line(row)):
                if k == key:
                    if (row, i) != (self.row, self.index):
                        self.match.assets.play("click", 0.3)
                    self.row = row
                    self.index = i
                    return True
        return False

    # ── celular ──────────────────────────────
    def snapshot(self):
        key, item = self.current()
        items = []
        for row in (0, 1):
            for k, s in self.line(row):
                state = self.state(s, row)
                pet = row == 1
                if pet:
                    img = f"/pet/{s.key}.png" if s else None
                    label = s.name if s else "SEM PET"
                    tier = "pet" if s else "base"
                else:
                    img = f"/skin/{s.key if s else 'base_' + self.hero}.png"
                    label = s.name if s else "ROUPA DE SEMPRE"
                    tier = s.rarity if s else "base"
                tag = {"vestida": "COM VOCÊ" if pet else "VESTIDA", "vestir": "PEGAR" if pet else "VESTIR",
                       "comprar": "NA LOJA", "cupom": "CUPOM"}[state]
                info = {"type": "skin" if img else "nada", "hero": "PET" if pet else HERO_NAMES.get(self.hero, ""),
                        "tier": tier, "state": {"vestida": "tirar", "vestir": "vestir"}.get(state, state), "tag": tag,
                        "sub": {"vestida": tag, "vestir": "É SEU" if pet else "É SUA", "comprar": "COMPRE NA LOJA",
                                "cupom": "SÓ COM CUPOM"}[state],
                        "rarity": "PET" if pet else ("ROUPA DE SEMPRE" if s is None
                                                     else ("RARA" if s.rarity == "rara" else "LOJA"))}
                if img:
                    info["img"] = img
                items.append({
                    "id": k, "label": label, "cost": 0,
                    "desc": s.blurb if s else ("SÓ VOCÊ, SEM BICHINHO" if pet
                                               else "O " + HERO_NAMES.get(self.hero, "") + " DE SEMPRE"),
                    "ok": state != "vestida", "afford": state in ("vestir", "vestida"),
                    "color": "#%02x%02x%02x" % (s.color if s else theme.BONE), "info": info,
                })
        state = self.state(item)
        action = {"vestida": "COM VOCÊ" if self.row else "VESTIDA", "vestir": "PEGAR" if self.row else "VESTIR",
                  "comprar": "NA LOJA", "cupom": "SÓ COM CUPOM"}[state]
        return {"kind": "armario", "title": "ARMÁRIO · " + HERO_NAMES.get(self.hero, ""), "souls": cacos.balance(),
                "unit": "CACOS", "picked": key, "mates": [], "items": items, "action": action}

    # ── TV ───────────────────────────────────
    def draw(self, screen, ui, anchor):
        f = self.fighter
        sizes = ((96, 116), (80, 84))
        gap = 10
        widest = max(len(self.line(r)) * sizes[r][0] + (len(self.line(r)) - 1) * gap for r in (0, 1))
        w = max(560, widest + 120)
        h = 380
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
            ui.text(screen, text, theme.XS, note, (rect.centerx, rect.y + 42))
        top = rect.y + 54
        for row in (0, 1):
            cw, ch = sizes[row]
            items = self.line(row)
            here = row == self.row
            ui.text(screen, self.ROWS[row], theme.XS, theme.BONE if here else theme.FAINT,
                    (rect.x + 16, top + ch // 2), anchor="midleft")
            x0 = rect.x + 70 + (w - 86 - (len(items) * cw + (len(items) - 1) * gap)) // 2
            for i, (key, item) in enumerate(items):
                card = pygame.Rect(x0 + i * (cw + gap), top, cw, ch)
                on = here and i == self.marks[row] % len(items)
                if on:
                    card.move_ip(0, -3)
                self._wardrobe_card(screen, ui, card, item, on, row)
            top += ch + 14
        key, item = self.current()
        bar = pygame.Rect(rect.x + 12, top, w - 24, 46)
        screen.fill((16, 14, 24), bar)
        pygame.draw.rect(screen, theme.LINE, bar, 1)
        pet = self.row == 1
        name = item.name if item else ("SEM PET" if pet else "ROUPA DE SEMPRE")
        ui.text(screen, name, theme.S if len(name) <= 22 else theme.XS, item.color if item else theme.BONE,
                (bar.x + 10, bar.y + 14), anchor="midleft")
        sub = item.blurb if item else ("NINGUÉM TE SEGUINDO" if pet else "SEM SKIN: O VISUAL ORIGINAL DO HERÓI")
        button = pygame.Rect(bar.right - 130, bar.y + 8, 120, 30)
        room = button.x - bar.x - 20
        while len(sub) > 8 and ui.assets.text(sub, theme.XS, theme.MUTED).get_width() > room:
            sub = sub[:-2].rstrip(" ,·") + "…"
        ui.text(screen, sub, theme.XS, theme.MUTED, (bar.x + 10, bar.y + 32), anchor="midleft")
        state = self.state(item)
        label, fill, ink = {"vestida": ("COM VOCÊ" if pet else "VESTIDA", theme.LINE, theme.MUTED),
                            "vestir": ("PEGAR" if pet else "VESTIR", theme.MOSS, theme.INK),
                            "comprar": ("NA LOJA", theme.LINE, theme.MUTED),
                            "cupom": ("SÓ COM CUPOM", theme.LINE, theme.MUTED)}[state]
        self._button(screen, ui, button, label, fill, ink)
        hint = "LADOS: ESCOLHER · CIMA/BAIXO: ROUPA OU PET · ATACAR: " + ("PEGAR" if pet else "VESTIR")
        ui.text(screen, hint + " · ESQUIVA: FECHAR", theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 10))

    def _wardrobe_card(self, screen, ui, card, item, on, row):
        t = self.match.frame
        state = self.state(item, row)
        mine = state in ("vestida", "vestir")
        screen.fill((8, 6, 12), card.move(3, 4))
        if item is None:
            self._gradient(screen, card, (66, 62, 80), (30, 28, 40))
            tint = theme.BONE
        elif row == 1:
            self._gradient(screen, card, (36, 96, 70), (20, 44, 40))
            tint = item.color
        else:
            self._gradient(screen, card, *((92, 46, 130), (180, 116, 48)) if item.rarity == "rara"
                           else ((44, 70, 128), (22, 30, 62)))
            tint = item.color
        halo = pygame.Surface((card.width, card.width), pygame.SRCALPHA)
        for rad, alpha in ((card.width * 0.45, 26), (card.width * 0.32, 36), (card.width * 0.2, 46)):
            pygame.draw.circle(halo, (*tint, alpha), (card.width // 2, card.width // 2), round(rad))
        screen.blit(halo, (card.x, card.y + 4))
        img = None
        if row == 0:
            sprites = (self.match.assets.sprites.get(self.hero) if item is None
                       else self.match.assets.skin_sprites(item.key))
            if sprites is not None:
                img = sprites.frame("frente", t // 8 if on else 0)
                img = pygame.transform.scale(img, (round(img.get_width() * 1.1), round(img.get_height() * 1.1)))
        elif item is not None:
            img = pet_image(item.key, on and (t // 20) % 2)
            if img is not None:
                img = pygame.transform.scale(img, (round(img.get_width() * 1.2), round(img.get_height() * 1.2)))
        else:                                                   # SEM PET: um X apagado
            c = card.centerx, card.y + card.height // 2 - 10
            pygame.draw.line(screen, theme.FAINT, (c[0] - 10, c[1] - 10), (c[0] + 10, c[1] + 10), 3)
            pygame.draw.line(screen, theme.FAINT, (c[0] + 10, c[1] - 10), (c[0] - 10, c[1] + 10), 3)
        if img is not None:
            spot = img.get_rect(midbottom=(card.centerx, card.bottom - 26))
            pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 18, spot.bottom - 4, 36, 8))
            fx = on and row == 0 and item is not None and mine
            if fx:
                draw_back(screen, item.key, spot, t)
            if not mine:                                        # ainda não é seu: só a silhueta
                img = img.copy()
                img.fill((20, 18, 30, 255), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, spot)
            if fx:
                draw_front(screen, item.key, spot, t)
        strip = pygame.Rect(card.x, card.bottom - 20, card.width, 20)
        if state == "vestida":
            screen.fill(theme.MOSS, strip)
            ui.text(screen, "COM VOCÊ" if row else "VESTIDA", theme.XS, theme.INK,
                    (strip.centerx, strip.centery + 1), shadow=False)
        else:
            screen.fill((14, 12, 22), strip)
            if state in ("comprar", "cupom"):
                label = ("LOJA" if row else "NA LOJA") if state == "comprar" else "CUPOM"
                half = (ui.assets.text(label, theme.XS, theme.MUTED).get_width() + 12) // 2
                self._lock(screen, strip.centerx - half + 3, strip.centery)
                ui.text(screen, label, theme.XS, theme.MUTED, (strip.centerx - half + 12, strip.centery + 1),
                        anchor="midleft")
            else:
                ui.text(screen, "PEGAR" if row else "VESTIR", theme.XS, theme.BONE, (strip.centerx, strip.centery + 1))
        self._frame(screen, card, tint, on)
