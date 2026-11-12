"""A LOJINHA DA TURMA no quintal da Casa: a loja de CACOS (soulstrike/cacos.py).

Vende só skins (soulstrike/skins.py). As raras saem por cupom: o cupom dá os cacos e a skin do
personagem dele. Quem já tem a skin veste ou tira por aqui (vale para qualquer jogador que escolher
aquele herói, na campanha, no duelo e na Casa).

ATACAR perto do balcão abre, numa janela pequena (ver janelas.py). Na TV: analógico escolhe, ATACAR
compra, ESQUIVA fecha. INSERIR CUPOM abre um teclado na janela (no celular, o cupom é digitado no
teclado do celular).
"""
import math
import random

import pygame

from . import cacos, config, pecas, theme
from .data import CHARACTERS
from .entities import Entity, Particle, Wall
from .skins import CACO_COLOR, PETS, SKINS, ShopPet, draw_caco

STICK = 0.5
REACH = 80
KEY_ROWS = ("ABCDEFGHI", "JKLMNOPQR", "STUVWXYZ0", "123456789")
KEY_ACTIONS = ("APAGAR", "LIMPAR", "USAR")
MAX_CODE = 20
HERO_NAMES = {c.key: c.name.upper() for c in CHARACTERS}
ORDER = sorted(SKINS.values(), key=lambda s: (s.rarity != "rara", s.name))
ROWS = 2                      # a grade da TV: 2 linhas de cartas, rolando para o lado
COLS = 5                      # colunas que cabem de uma vez
CARD_W, CARD_H, GAP = 54, 66, 6   # cartas da janela pequena (ver janelas.py)
RARE_BG = ((92, 46, 130), (180, 116, 48))     # carta rara: roxo que vira dourado
SHOP_BG = ((44, 70, 128), (22, 30, 62))       # carta da loja: azul da noite
PAPER = (240, 228, 196)
SECTIONS = (("skins", "SKINS"), ("pets", "PETS"))


def state_of(skin):
    """O que dá para fazer com a skin (ou o pet) agora: "tirar", "vestir", "comprar" ou "cupom"."""
    if isinstance(skin, ShopPet):
        return "vestir" if skin.key in cacos.owned_pets() else "comprar"
    if skin.key in cacos.owned():
        return "tirar" if cacos.worn(skin.hero) == skin.key else "vestir"
    return "comprar" if skin.price else "cupom"


def pet_image(pet, walking=False):
    """A figura do pet da loja (sentado ou andando, virado para a direita)."""
    return pecas.image(f"mascote_{pet}_{'andando' if walking else 'sentado'}")


ACTION_LABEL = {"tirar": "NO ARMÁRIO", "vestir": "NO ARMÁRIO", "comprar": "COMPRAR", "cupom": "SÓ COM CUPOM"}


class ShopStand(Entity):
    """O balcão da lojinha: a banca da feira com o ourives (quem entende de cristal) atendendo, a
    placa e um caco grande girando em cima."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.age = 0
        self.wall = Wall(round(x) - 52, round(y) - 12, 104, 22, visible=False)
        self.rect = pygame.Rect(round(x) - 64, round(y) - 30, 128, 50)
        self.label = None                     # "LOJA DE CACOS" já escrito (feito com a ui da casa)

    def bake_label(self, ui):
        label = pygame.Surface((104, 16), pygame.SRCALPHA)
        ui.text(label, "LOJA DE CACOS", theme.XS, (40, 60, 120), (52, 8), shadow=False)
        self.label = label

    @property
    def sort_y(self):
        return self.y

    def near(self, f):
        return f.alive_in_match and math.hypot(f.x - self.x, f.y - (self.y + 20)) < REACH

    def update(self, match):
        self.age += 1
        if self.age % 50 == 0:
            match.particles.append(Particle(self.x + random.uniform(-30, 30), self.y - 90, 0, -0.4,
                                            CACO_COLOR, 34, 2))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        back, front = pecas.image("banca_loja_1_tras"), pecas.image("banca_loja_1_frente")
        surf.blit(pecas.shadow(116, 22), (sx - 58, sy - 6))
        if back and front:
            ox, oy = sx - back.get_width() // 2, sy + 6 - back.get_height()
            surf.blit(back, (ox, oy))
            npc = pecas.image(f"npc_ourives_parado{(self.age // 30) % 2}")
            if npc:
                surf.blit(npc, (sx - npc.get_width() // 2, oy + 82 - npc.get_height()))
            surf.blit(front, (ox, oy))
            top = oy
        else:
            surf.fill((90, 60, 40), (sx - 50, sy - 40, 100, 44))
            top = sy - 60
        # placa pendurada
        sign = pygame.Rect(sx - 54, top - 26, 108, 20)
        pygame.draw.line(surf, (60, 44, 30), (sign.x + 12, sign.bottom), (sign.x + 12, top + 6), 2)
        pygame.draw.line(surf, (60, 44, 30), (sign.right - 12, sign.bottom), (sign.right - 12, top + 6), 2)
        surf.fill((36, 30, 44), sign.inflate(4, 4))
        surf.fill((246, 236, 210), sign)
        surf.fill((120, 200, 255), (sign.x, sign.bottom - 3, sign.width, 3))
        if self.label is not None:
            surf.blit(self.label, self.label.get_rect(center=(sign.centerx, sign.centery - 1)))
        # o caco grande girando em cima da placa
        bob = math.sin(self.age * 0.06) * 3
        draw_caco(surf, sx, top - 42 + bob, self.age, size=9)


class ShopMenu:
    """O menu da loja aberto por um jogador."""

    kind = "cacos"

    def __init__(self, match, fighter):
        self.match = match
        self.fighter = fighter
        self.index = 0
        self.age = 0
        self._last = (0, 0)
        self.typing = False                   # teclado do cupom aberto na TV
        self.code = ""
        self.key = (0, 0)                     # tecla marcada (linha, coluna)
        self.note = ("", theme.BONE)
        self.errors = 0
        self.wait = 0
        self.page = "home"                    # "home" (os cards das seções) ou "skins"
        self.section = 0                      # card marcado na tela inicial
        self.coupon = False                   # botão INSERIR CUPOM (no topo) marcado
        self.scroll = 0
        stats = getattr(fighter, "stats", None)
        self.hero = getattr(stats, "key", None)   # as skins do herói de quem abriu vêm primeiro
        self.order = sorted(ORDER, key=lambda s: s.hero != self.hero)

    # ── linhas ───────────────────────────────
    def entries(self):
        if self.page == "pets":
            return [(p.key, p) for p in PETS.values()]
        return [(s.key, s) for s in self.order]

    def current(self):
        """O que está marcado: ("cupom", None), ("secao:<nome>", None) ou (skin, Skin)."""
        if self.coupon:
            return "cupom", None
        if self.page == "home":
            return "secao:" + SECTIONS[self.section][0], None
        rows = self.entries()
        return rows[self.index % len(rows)]

    # ── ações ────────────────────────────────
    def buy(self):
        key, skin = self.current()
        play = self.match.assets.play
        if key == "cupom":
            self.typing = True
            self.key = (0, 0)
            play("select", 0.4)
            return True
        if skin is None:                      # tela inicial: entra na seção
            name = SECTIONS[self.section][0]
            self.page, self.index, self.scroll = name, 0, 0
            self.index = self._my_first()
            self.note = ("", theme.BONE)
            play("select", 0.4)
            return True
        return self.act(skin)

    def _my_first(self):
        """Ao entrar nas skins, já marca a do herói de quem abriu (a vestida, senão a primeira dele)."""
        if self.page != "skins":
            return 0
        rows = self.entries()
        worn = cacos.worn(self.hero) if self.hero else None
        for want in (lambda s: s.key == worn, lambda s: s.hero == self.hero):
            for i, (_, s) in enumerate(rows):
                if want(s):
                    return i
        return 0

    def act(self, skin):
        state = state_of(skin)
        play = self.match.assets.play
        if state == "cupom":                  # rara: leva direto para o botão do cupom
            self._say("ESSA SÓ VEM POR CUPOM: ATACAR AQUI EM CIMA PARA DIGITAR", CACO_COLOR)
            self.coupon = True
            play("select", 0.3)
            return False
        if state == "comprar":
            if not cacos.spend(skin.price):
                self._say(f"FALTAM {skin.price - cacos.balance()} CACOS", theme.BLOOD)
                play("cancel", 0.3)
                return False
            if isinstance(skin, ShopPet):
                cacos.give_pet(skin.key)
                self._say(f"É SEU! ESCOLHA ELE NO ARMÁRIO P{self._slot()}, AQUI DO LADO", theme.MOSS)
            else:
                cacos.give_skin(skin.key)
                self._say(f"É SUA! VISTA NO ARMÁRIO P{self._slot()}, AQUI DO LADO", theme.MOSS)
            self._celebrate(skin)
            play("compra", 0.5)
            return True
        self._say(f"JÁ É {'SEU' if isinstance(skin, ShopPet) else 'SUA'}: PEGUE NO ARMÁRIO P{self._slot()}, AQUI DO LADO",
                  theme.BONE)
        play("click", 0.3)
        return False

    def _slot(self):
        return getattr(self.fighter, "slot", 1)

    def redeem(self, code):
        """Tenta o cupom. Errou 5 vezes seguidas: espera 30 segundos para tentar de novo."""
        play = self.match.assets.play
        if self.wait > 0:
            self._say(f"ESPERE {self.wait // config.FPS + 1} S PARA TENTAR DE NOVO", theme.BLOOD)
            play("cancel", 0.3)
            return False
        status, amount, skin = cacos.redeem(code)
        if status == "ok":
            self.errors = 0
            name = SKINS[skin].name if skin in SKINS else ""
            self._say(f"+{amount} CACOS" + (f" E {name}! VISTA NO ARMÁRIO" if name else "!"), CACO_COLOR)
            if skin in SKINS:
                self.page, self.coupon = "skins", False
                self.index = next(i for i, (k, _) in enumerate(self.entries()) if k == skin)
                self._celebrate(SKINS[skin])
            self.match.popup(self.fighter.x, self.fighter.y - 80, f"+{amount} CACOS", CACO_COLOR)
            play("compra", 0.6)
            self.typing = False
            self.code = ""
            return True
        self.errors += 1
        if self.errors >= cacos.MAX_TRIES:
            self.errors = 0
            self.wait = cacos.WAIT_FRAMES
        self._say("CUPOM JÁ USADO NESTE SAVE" if status == "usado" else "CUPOM INVÁLIDO", theme.BLOOD)
        play("cancel", 0.35)
        return False

    def _say(self, text, color):
        self.note = (text, color)

    def _celebrate(self, skin):
        f = self.fighter
        self.match.burst(f.x, f.y - 30, skin.color, 26, speed=3)
        self.match.camera.shake(2)

    # ── controle ─────────────────────────────
    def handle(self, inp):
        self.age += 1
        self.wait = max(0, self.wait - 1)
        if self.age <= 1:
            return True                       # o ATACAR que abriu não compra
        if inp.pressed("dodge") or inp.pressed("special") or inp.pressed("cancel"):
            self.match.assets.play("cancel", 0.3)
            if self.typing:
                self.typing = False
                return True
            if self.coupon:
                self.coupon = False
                return True
            if self.page != "home":           # ESQUIVA dentro da seção volta para os cards
                self.page = "home"
                self.note = ("", theme.BONE)
                return True
            return False
        x, y = inp.axis()
        sx = 1 if x > STICK else -1 if x < -STICK else 0
        sy = 1 if y > STICK else -1 if y < -STICK else 0
        moved = (sx, sy) != self._last and (sx or sy)
        self._last = (sx, sy)
        if self.typing:
            if moved:
                self._move_key(sx, sy)
            if inp.pressed("attack") or inp.pressed("confirm"):
                self._press_key()
            return True
        if moved:
            if self.coupon:
                if sy > 0:
                    self.coupon = False
                    self.match.assets.play("click", 0.3)
            elif self.page == "home":
                if sy < 0:
                    self.coupon = True
                elif sx:
                    self.section = max(0, min(len(SECTIONS) - 1, self.section + sx))
                self.match.assets.play("click", 0.3)
            else:
                self._move_card(sx, sy)
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

    def _move_card(self, sx, sy):
        """Grade de cartas em 2 linhas que rola para o lado: o analógico anda nas duas direções."""
        n = len(self.entries())
        cols = (n + ROWS - 1) // ROWS
        col, row = divmod(self.index % n, ROWS)
        if row + sy < 0:                      # subiu da primeira linha: vai para o botão do cupom
            self.coupon = True
            self.match.assets.play("click", 0.3)
            return
        col = (col + sx) % cols
        row = max(0, min(ROWS - 1, row + sy))
        self.index = min(n - 1, col * ROWS + row)
        self.match.assets.play("click", 0.3)

    def _keys(self):
        return [list(r) for r in KEY_ROWS] + [list(KEY_ACTIONS)]

    def _move_key(self, sx, sy):
        rows = self._keys()
        r, c = self.key
        r = (r + sy) % len(rows)
        c = min(c, len(rows[r]) - 1) if sy else (c + sx) % len(rows[r])
        self.key = (r, c)
        self.match.assets.play("click", 0.25)

    def _press_key(self):
        rows = self._keys()
        r, c = self.key
        k = rows[r][min(c, len(rows[r]) - 1)]
        if k == "APAGAR":
            self.code = self.code[:-1]
        elif k == "LIMPAR":
            self.code = ""
        elif k == "USAR":
            self.redeem(self.code)
            return
        elif len(self.code) < MAX_CODE:
            self.code += k
        self.match.assets.play("click", 0.3)

    def pick(self, key):
        """Pedido do celular: marca a linha ``key`` ou usa ``cupom:<código>``."""
        if key.startswith("cupom:"):
            self.redeem(key[6:][:40])
            return False
        if key == "cupom":
            self.coupon = True
            return True
        page = "pets" if key.startswith("pet:") else "skins"
        key = key[4:] if page == "pets" else key
        rows = [(p.key, p) for p in PETS.values()] if page == "pets" else [(s.key, s) for s in self.order]
        for i, (k, _) in enumerate(rows):
            if k == key:
                if i != self.index % len(rows) or self.page != page:
                    self.match.assets.play("click", 0.3)
                self.index, self.page, self.coupon = i, page, False
                self.typing = False
                return True
        return False

    # ── celular ──────────────────────────────
    def snapshot(self):
        key, skin = self.current()
        balance = cacos.balance()
        items = [{"id": "cupom", "label": "INSERIR CUPOM", "cost": 0, "desc": "digite o cupom para ganhar cacos",
                  "ok": True, "afford": True, "color": "#78c8ff",
                  "info": {"type": "cupom", "sub": "CACOS E SKIN RARA", "note": self.note[0],
                           "tier": "cupom", "tag": "INSERIR", "state": "cupom"}}]
        for s in self.order:
            state = state_of(s)
            items.append({
                "id": s.key, "label": s.name, "cost": s.price if state == "comprar" else 0,
                "desc": s.blurb, "ok": state != "cupom", "afford": state != "comprar" or balance >= s.price,
                "color": "#%02x%02x%02x" % s.color,
                "info": {"type": "skin", "img": f"/skin/{s.key}.png", "hero": HERO_NAMES.get(s.hero, ""),
                         "sub": {"tirar": "VESTIDA", "vestir": "É SUA", "comprar": f"{s.price} CACOS",
                                 "cupom": "SÓ COM CUPOM"}[state],
                         "rarity": "RARA · CUPOM" if s.rarity == "rara" else "LOJA",
                         "tier": s.rarity, "state": state, "mine": s.hero == self.hero,
                         "tag": {"tirar": "VESTIDA", "vestir": "É SUA", "comprar": str(s.price),
                                 "cupom": "CUPOM"}[state], "section": "skins"},
            })
        for pet in PETS.values():
            state = state_of(pet)
            items.append({
                "id": "pet:" + pet.key, "label": pet.name, "cost": pet.price if state == "comprar" else 0,
                "desc": pet.blurb, "ok": True, "afford": state != "comprar" or balance >= pet.price,
                "color": "#%02x%02x%02x" % pet.color,
                "info": {"type": "skin", "img": f"/pet/{pet.key}.png", "hero": "PET", "tier": "pet",
                         "sub": "É SEU" if state == "vestir" else f"{pet.price} CACOS", "rarity": "PET",
                         "state": state, "tag": "É SEU" if state == "vestir" else str(pet.price),
                         "section": "pets"},
            })
        if skin is None:
            key = "cupom"
        elif isinstance(skin, ShopPet):
            key = "pet:" + key
        action = "USAR CUPOM" if skin is None else ACTION_LABEL[state_of(skin)]
        return {"kind": "cacos", "title": "LOJA DE CACOS", "souls": balance, "unit": "CACOS",
                "picked": key, "mates": [], "items": items, "action": action}

    # ── TV ───────────────────────────────────
    W, H = 330, 230

    def size(self, ui):
        return self.W, self.H

    def draw(self, screen, ui, cam, rect=None):
        from . import janelas
        f = self.fighter
        if rect is None:
            rect = janelas.default_rect(self.size(ui), cam, f)
        t = self.match.frame
        title = "LOJA DE CACOS" if self.page == "home" else "LOJA › " + dict(SECTIONS).get(self.page, "")
        janelas.panel(screen, ui, rect, f, title, accent=CACO_COLOR)
        balance = str(cacos.balance())
        ui.text(screen, balance, theme.XS, CACO_COLOR, (rect.right - 10, rect.y + 13), anchor="midright")
        draw_caco(screen, rect.right - 18 - ui.assets.text_width(balance, theme.XS), rect.y + 13, t, size=5)
        body = pygame.Rect(rect.x + 8, rect.y + 24, rect.w - 16, rect.h - 40)
        chip = pygame.Rect(body.x, body.y, 116, 15)              # o botão do cupom, no topo
        on = self.coupon or self.typing
        screen.fill(PAPER if on else (44, 42, 58), chip)
        if on:
            pygame.draw.rect(screen, (250, 248, 240), chip.inflate(2, 2), 1)
        ui.text(screen, "INSERIR CUPOM", theme.XS, (20, 40, 80) if on else theme.BONE, chip.center, shadow=False)
        area = pygame.Rect(body.x, chip.bottom + 2, body.w, ROWS * CARD_H + GAP + 10)
        if self.typing:
            self._draw_coupon(screen, ui, area)
            hint = "ATACAR: TECLA · ESQUIVA: VOLTAR"
            name, sub, color = "CUPOM", "DIGITE O CÓDIGO (OU NO CELULAR)", CACO_COLOR
        elif self.page == "home":
            self._draw_home(screen, ui, area)
            hint = "ATACAR: ABRIR · ESQUIVA: FECHAR"
            name, sub, color = (("INSERIR CUPOM", "DÁ CACOS E, ÀS VEZES, UMA RARA", CACO_COLOR) if self.coupon
                                else ("ESCOLHA UMA SEÇÃO", "CIMA: CUPOM", theme.BONE))
        else:
            self._draw_grid(screen, ui, area, self.entries())
            key, skin = self.current()
            if skin is None:
                name, sub, color = "INSERIR CUPOM", "DÁ CACOS E, ÀS VEZES, UMA RARA", CACO_COLOR
                hint = "ATACAR: DIGITAR · ESQUIVA: VOLTAR"
            else:
                state = state_of(skin)
                name, color = skin.name, skin.color
                sub = ("PET" if isinstance(skin, ShopPet) else HERO_NAMES.get(skin.hero, "")) + " · " + skin.blurb
                action = (f"COMPRAR {skin.price}" if state == "comprar"
                          else "NO ARMÁRIO" if state in ("vestir", "tirar") else "SÓ COM CUPOM")
                hint = f"ATACAR: {action} · ESQUIVA: VOLTAR"
        text, note = self.note
        if text:
            sub, sub_color = text, note
        else:
            sub_color = theme.MUTED
        y = area.bottom + 6
        ui.text(screen, _fit(ui, name, body.w), theme.XS, color, (body.x + 2, y), anchor="midleft")
        ui.text(screen, _fit(ui, sub, body.w), theme.XS, sub_color, (body.x + 2, y + 12), anchor="midleft")
        ui.text(screen, hint, theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 9))

    # a tela inicial: um card por seção
    def _draw_home(self, screen, ui, body):
        t = self.match.frame
        gap = 10
        cw = (body.w - gap) // 2
        for k, (name, title) in enumerate(SECTIONS):
            card = pygame.Rect(body.x + k * (cw + gap), body.y + 4, cw, body.h - 6)
            on = k == self.section and not self.coupon
            screen.fill((8, 6, 12), card.move(2, 3))
            if name == "skins":
                self._gradient(screen, card, (70, 44, 120), (28, 36, 80))
                skin = self.order[(t // 120) % len(self.order)]
                sprites = self.match.assets.skin_sprites(skin.key)
                img = sprites.frame("frente", t // 8 if on else 0) if sprites is not None else None
                owned = len([s for s in SKINS if s in cacos.owned()])
                lines = (f"{len(SKINS)} ROUPAS", "NENHUMA SUA" if not owned else f"{owned} SUA" + ("S" if owned > 1 else ""))
                color = (200, 160, 255)
            else:
                self._gradient(screen, card, (36, 96, 70), (20, 44, 40))
                pets = list(PETS.values())
                pet = pets[(t // 120) % len(pets)]
                img = pet_image(pet.key, on and (t // 20) % 2)
                if img is not None:
                    img = pygame.transform.scale(img, (img.get_width() * 3 // 2, img.get_height() * 3 // 2))
                owned = len(cacos.owned_pets())
                lines = (f"{len(PETS)} BICHINHOS", "NENHUM SEU" if not owned else f"{owned} SEU" + ("S" if owned > 1 else ""))
                color = (140, 230, 170)
            strip = pygame.Rect(card.x, card.bottom - 40, card.w, 40)
            if img is not None:
                spot = img.get_rect(midbottom=(card.centerx, strip.y - 4))
                pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 16, spot.bottom - 4, 32, 8))
                screen.blit(img, spot)
            screen.fill((14, 12, 22), strip)
            ui.text(screen, title, theme.XS, color, (strip.centerx, strip.y + 9))
            ui.text(screen, lines[0], theme.XS, theme.MUTED, (strip.centerx, strip.y + 21))
            ui.text(screen, lines[1], theme.XS, theme.MUTED, (strip.centerx, strip.y + 32))
            if name == "pets" and not cacos.owned_pets():
                tag = pygame.Rect(card.right - 40, card.y + 4, 36, 12)
                screen.fill((250, 210, 90), tag)
                ui.text(screen, "NOVO", theme.XS, (70, 40, 20), tag.center, shadow=False)
            self._frame(screen, card, color, on)

    def _draw_grid(self, screen, ui, area, rows):
        n = len(rows)
        cols = (n + ROWS - 1) // ROWS
        cur = self.index % n
        col = cur // ROWS
        first = getattr(self, "scroll", 0)
        first = max(min(first, col), col - COLS + 1, 0)
        first = min(first, max(0, cols - COLS))
        self.scroll = first
        vis = min(COLS, cols)
        grid_w = vis * CARD_W + (vis - 1) * GAP
        gx = area.centerx - grid_w // 2
        clip = screen.get_clip()
        screen.set_clip(area.inflate(0, 8))
        for i, (key, skin) in enumerate(rows):
            c, r = divmod(i, ROWS)
            if not first <= c < first + COLS:
                continue
            card = pygame.Rect(gx + (c - first) * (CARD_W + GAP), area.y + 6 + r * (CARD_H + GAP), CARD_W, CARD_H)
            on = i == cur
            if on:
                card.move_ip(0, -3)
            if skin is None:
                self._draw_ticket(screen, ui, card, on)
            else:
                self._draw_card(screen, ui, card, skin, on)
        screen.set_clip(clip)
        # setinhas de rolar
        blink = (self.match.frame // 20) % 2
        for side, show in ((-1, first > 0), (1, first + COLS < cols)):
            if not show:
                continue
            ax = gx - 14 if side < 0 else gx + grid_w + 14
            ay = area.centery + (1 if blink else 0)
            pts = [(ax + side * 6, ay), (ax - side * 4, ay - 9), (ax - side * 4, ay + 9)]
            pygame.draw.polygon(screen, CACO_COLOR, pts)
        if cols > COLS:                                 # bolinhas de página
            for k in range(cols - COLS + 1):
                cx = area.centerx + (k - (cols - COLS) / 2) * 10
                pygame.draw.circle(screen, CACO_COLOR if k == first else theme.FAINT,
                                   (round(cx), area.bottom + 1), 2)

    def _gradient(self, screen, rect, top, bottom):
        for k in range(rect.height):
            a = k / max(1, rect.height - 1)
            color = tuple(round(top[j] + (bottom[j] - top[j]) * a) for j in range(3))
            screen.fill(color, (rect.x, rect.y + k, rect.width, 1))

    def _frame(self, screen, card, color, on):
        if on:
            glow = pygame.Surface((card.width + 12, card.height + 12), pygame.SRCALPHA)
            pulse = 70 + round(40 * math.sin(self.match.frame * 0.15))
            pygame.draw.rect(glow, (*color, pulse), glow.get_rect(), border_radius=6)
            screen.blit(glow, (card.x - 6, card.y - 6))
            pygame.draw.rect(screen, (250, 248, 240), card.inflate(4, 4), 2)
            pygame.draw.rect(screen, color, card, 2)
        else:
            pygame.draw.rect(screen, (12, 10, 18), card.inflate(4, 4), 2)
            pygame.draw.rect(screen, theme.LINE, card, 1)

    def _draw_card(self, screen, ui, card, skin, on):
        t = self.match.frame
        state = state_of(skin)
        screen.fill((8, 6, 12), card.move(2, 3))                          # sombra da carta
        self._gradient(screen, card, *(RARE_BG if skin.rarity == "rara" else SHOP_BG))
        halo = pygame.Surface((card.width, card.width), pygame.SRCALPHA)   # brilho na cor da skin
        for rad, alpha in ((24, 30), (17, 40), (10, 50)):
            pygame.draw.circle(halo, (*skin.color, alpha), (card.width // 2, card.width // 2), rad)
        screen.blit(halo, (card.x, card.y + 2))
        strip = pygame.Rect(card.x, card.bottom - 13, card.width, 13)
        if isinstance(skin, ShopPet):
            img = pet_image(skin.key, on and (t // 20) % 2)
            if img is not None:
                bob = round(math.sin(t * 0.12) * 2) if skin.flies else 0
                spot = img.get_rect(midbottom=(card.centerx, strip.y - 3 + bob - (5 if skin.flies else 0)))
                screen.blit(img, spot)
        else:
            sprites = self.match.assets.skin_sprites(skin.key)
            if sprites is not None:
                img = sprites.frame("frente", t // 8 if on else 0)
                img = pygame.transform.scale(img, (img.get_width() * 3 // 4, img.get_height() * 3 // 4))
                spot = img.get_rect(midbottom=(card.centerx, strip.y - 1))
                pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 12, spot.bottom - 3, 24, 6))
                screen.blit(img, spot)
        if skin.rarity == "rara":                                          # selo de raridade
            tag = pygame.Rect(card.x + 2, card.y + 2, 10, 10)
            screen.fill((250, 210, 90), tag)
            ui.text(screen, "R", theme.XS, (70, 30, 90), tag.center, shadow=False)
        if skin.hero is not None and skin.hero == self.hero:              # o herói de quem abriu
            screen.fill(theme.SLOT_COLORS.get(self.fighter.slot, theme.BONE), (card.x, card.y, card.width, 3))
        screen.fill((14, 12, 22), strip)                                  # preço, cadeado ou USANDO
        if state == "comprar":
            ok = cacos.balance() >= skin.price
            draw_caco(screen, strip.x + 9, strip.centery, t, size=4)
            ui.text(screen, str(skin.price), theme.XS, CACO_COLOR if ok else theme.BLOOD,
                    (strip.x + 16, strip.centery + 1), anchor="midleft")
        elif state == "cupom":
            self._lock(screen, strip.x + 6, strip.centery + 1)
            ui.text(screen, "CUPOM", theme.XS, theme.MUTED, (strip.x + 12, strip.centery + 1), anchor="midleft")
        elif state == "tirar":
            screen.fill(theme.MOSS, strip)
            ui.text(screen, "USANDO", theme.XS, theme.INK, (strip.centerx, strip.centery + 1), shadow=False)
        else:
            ui.text(screen, "É SEU" if isinstance(skin, ShopPet) else "É SUA", theme.XS, theme.BONE,
                    (strip.centerx, strip.centery + 1))
        if state == "cupom" and not on:                                   # rara trancada: mais apagada
            veil = pygame.Surface((card.width, card.height - 13), pygame.SRCALPHA)
            veil.fill((10, 8, 16, 90))
            screen.blit(veil, card.topleft)
        self._frame(screen, card, skin.color, on)

    def _lock(self, screen, x, y):
        pygame.draw.rect(screen, theme.MUTED, (x - 3, y - 7, 7, 6), 1)
        screen.fill(theme.MUTED, (x - 4, y - 2, 9, 7))
        screen.fill((14, 12, 22), (x, y, 1, 3))

    def _draw_ticket(self, screen, ui, card, on):
        t = self.match.frame
        screen.fill((8, 6, 12), card.move(2, 3))
        screen.fill(PAPER, card)
        screen.fill((120, 200, 255), (card.x, card.y, card.width, 10))
        for k in range(card.x + 3, card.right - 3, 5):                    # picote
            screen.fill((190, 176, 140), (k, card.y + 38, 3, 1))
        bob = math.sin(t * 0.08) * 2 if on else 0
        draw_caco(screen, card.centerx, card.y + 24 + bob, t, size=8)
        strip = pygame.Rect(card.x, card.bottom - 13, card.width, 13)
        screen.fill((14, 12, 22), strip)
        ui.text(screen, "CUPOM", theme.XS, CACO_COLOR, (strip.centerx, strip.centery + 1))
        self._frame(screen, card, CACO_COLOR, on)

    def _button(self, screen, ui, rect, label, fill, ink, caco=False):
        screen.fill((8, 6, 12), rect.move(0, 3))
        screen.fill(fill, rect)
        screen.fill(tuple(min(255, c + 40) for c in fill), (rect.x, rect.y, rect.width, 2))
        if caco:
            draw_caco(screen, rect.right - 16, rect.centery, self.match.frame)
            ui.text(screen, label, theme.XS, ink, (rect.centerx - 8, rect.centery + 1), shadow=False)
        else:
            ui.text(screen, label, theme.XS, ink, (rect.centerx, rect.centery + 1), shadow=False)

    # o cupom na TV: o código e o teclado, dentro da janela pequena
    def _draw_coupon(self, screen, ui, area):
        t = self.match.frame
        box = pygame.Rect(area.x, area.y, area.w, 18)
        screen.fill((255, 255, 250), box)
        pygame.draw.rect(screen, (120, 200, 255), box, 2)
        blink = "_" if (t // 20) % 2 else ""
        ui.text(screen, (self.code + blink) or "DIGITE AQUI", theme.XS,
                (30, 30, 40) if self.code else (150, 150, 160), box.center, shadow=False)
        rows = self._keys()
        top = box.bottom + 6
        rh = (area.bottom - top) // len(rows)
        for r, row in enumerate(rows):
            cw = area.w // len(row)
            for c, k in enumerate(row):
                cell = pygame.Rect(area.x + c * cw, top + r * rh, cw - 3, rh - 3)
                on = (r, c) == self.key
                screen.fill(CACO_COLOR if on else (44, 42, 58), cell)
                ui.text(screen, k, theme.XS, (20, 20, 30) if on else theme.BONE, cell.center, shadow=False)


def _fit(ui, text, width):
    """Corta o texto com reticências para caber na largura."""
    while len(text) > 4 and ui.assets.text_width(text, theme.XS) > width:
        text = text[:-2].rstrip(" ,·") + "…"
    return text
