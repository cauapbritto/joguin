"""A LOJINHA DA TURMA no quintal da Casa: a loja de CACOS (soulstrike/cacos.py).

Vende só skins (soulstrike/skins.py). As raras saem por cupom: o cupom dá os cacos e a skin do
personagem dele. Quem já tem a skin veste ou tira por aqui (vale para qualquer jogador que escolher
aquele herói, na campanha, no duelo e na Casa).

ATACAR perto do balcão abre. Na TV: analógico escolhe, ATACAR compra/veste/tira, ESQUIVA fecha.
INSERIR CUPOM abre um teclado na tela (no celular, o cupom é digitado no teclado do celular).
"""
import math
import random

import pygame

from . import cacos, config, pecas, theme
from .data import CHARACTERS
from .entities import Entity, Particle, Wall
from .skins import CACO_COLOR, PETS, SKINS, ShopPet, draw_back, draw_caco, draw_front

STICK = 0.5
REACH = 80
KEY_ROWS = ("ABCDEFGHI", "JKLMNOPQR", "STUVWXYZ0", "123456789")
KEY_ACTIONS = ("APAGAR", "LIMPAR", "USAR")
MAX_CODE = 20
HERO_NAMES = {c.key: c.name.upper() for c in CHARACTERS}
ORDER = sorted(SKINS.values(), key=lambda s: (s.rarity != "rara", s.name))
ROWS = 2                      # a grade da TV: 2 linhas de cartas, rolando para o lado
COLS = 5                      # colunas que cabem de uma vez
CARD_W, CARD_H, GAP = 100, 116, 10
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
    def draw(self, screen, ui, anchor):
        f = self.fighter
        w, h = 640, 384
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(52, min(config.SCREEN_H - h - 64, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        ui.panel(screen, rect, fill=theme.INK_2, accent=CACO_COLOR)
        t = self.match.frame
        # cabeçalho: jogador, onde está, o botão do cupom e o pote de cacos
        chip = pygame.Rect(rect.x + 12, rect.y + 10, 30, 20)
        screen.fill(theme.SLOT_COLORS.get(f.slot, theme.BONE), chip)
        ui.text(screen, f"P{f.slot}", theme.XS, theme.INK, chip.center, shadow=False)
        draw_caco(screen, rect.x + 58, rect.y + 20, t, size=7)
        if self.page == "home":
            ui.text(screen, "LOJA DE CACOS", theme.S, theme.BONE, (rect.x + 72, rect.y + 20), anchor="midleft")
        else:
            title = dict(SECTIONS).get(self.page, "")
            ui.text(screen, "LOJA ›", theme.XS, theme.MUTED, (rect.x + 72, rect.y + 21), anchor="midleft")
            ui.text(screen, title, theme.S, theme.BONE, (rect.x + 122, rect.y + 20), anchor="midleft")
        pill = pygame.Rect(rect.right - 112, rect.y + 8, 100, 24)
        screen.fill((12, 10, 18), pill)
        pygame.draw.rect(screen, CACO_COLOR, pill, 1)
        draw_caco(screen, pill.x + 14, pill.centery, t)
        ui.text(screen, str(cacos.balance()), theme.S, CACO_COLOR, (pill.right - 10, pill.centery + 1),
                anchor="midright")
        coupon = pygame.Rect(pill.x - 140, rect.y + 8, 130, 24)
        on = self.coupon or self.typing
        screen.fill((8, 6, 12), coupon.move(0, 3))
        screen.fill(PAPER if on else (44, 42, 58), coupon)
        if on:
            pygame.draw.rect(screen, (250, 248, 240), coupon.inflate(4, 4), 2)
        ui.text(screen, "INSERIR CUPOM", theme.XS, (20, 40, 80) if on else theme.BONE,
                (coupon.centerx, coupon.centery + 1), shadow=False)
        text, color = self.note
        if text:
            ui.text(screen, text, theme.XS, color, (rect.centerx, rect.y + 46))
        body = pygame.Rect(rect.x + 12, rect.y + 58, w - 24, ROWS * CARD_H + GAP + 64)
        key, skin = self.current()
        if self.typing:
            self._draw_coupon(screen, ui, body)
            hint = "ANALÓGICO: TECLA · ATACAR: DIGITAR · ESQUIVA: VOLTAR"
        elif self.page == "home":
            self._draw_home(screen, ui, body)
            hint = ("ATACAR: INSERIR CUPOM · ESQUIVA: VOLTAR" if self.coupon
                    else "ANALÓGICO: ESCOLHER · ATACAR: ABRIR · CIMA: CUPOM · ESQUIVA: FECHAR")
        else:
            area = pygame.Rect(body.x, body.y, body.width, ROWS * CARD_H + GAP + 8)
            self._draw_grid(screen, ui, area, self.entries())
            shown = skin if skin is not None else self.entries()[self.index % len(self.entries())][1]
            self._draw_detail(screen, ui, pygame.Rect(body.x, area.bottom + 6, body.width, 50), shown)
            hint = ("ATACAR: INSERIR CUPOM · BAIXO: VOLTAR À VITRINE" if self.coupon
                    else "ANALÓGICO: ESCOLHER · ATACAR: " + ("IR AO CUPOM" if state_of(skin) == "cupom"
                                                      else ACTION_LABEL[state_of(skin)]) + " · ESQUIVA: VOLTAR")
        ui.text(screen, hint, theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 10))

    # a tela inicial: um card por seção
    def _draw_home(self, screen, ui, body):
        t = self.match.frame
        cw, ch = 280, body.height - 30
        gap = 24
        x0 = body.centerx - (cw * len(SECTIONS) + gap * (len(SECTIONS) - 1)) // 2
        for k, (name, title) in enumerate(SECTIONS):
            card = pygame.Rect(x0 + k * (cw + gap), body.y + 10, cw, ch)
            on = k == self.section and not self.coupon
            if on:
                card.move_ip(0, -3)
            screen.fill((8, 6, 12), card.move(3, 4))
            if name == "skins":
                self._gradient(screen, card, (70, 44, 120), (28, 36, 80))
                self._showcase(screen, card, t, on)
                owned = len([s for s in SKINS if s in cacos.owned()])
                sub = f"{len(SKINS)} ROUPAS · " + ("NENHUMA SUA AINDA" if not owned else f"{owned} SUA" + ("S" if owned > 1 else ""))
                color = (200, 160, 255)
            else:
                self._gradient(screen, card, (36, 96, 70), (20, 44, 40))
                self._pet_showcase(screen, card, t, on)
                owned = len(cacos.owned_pets())
                sub = f"{len(PETS)} BICHINHOS · " + ("NENHUM SEU AINDA" if not owned
                                                      else f"{owned} SEU" + ("S" if owned > 1 else ""))
                color = (140, 230, 170)
            strip = pygame.Rect(card.x, card.bottom - 54, card.width, 54)
            screen.fill((14, 12, 22), strip)
            ui.text(screen, title, theme.M, color, (strip.centerx, strip.y + 18))
            ui.text(screen, sub, theme.XS, theme.MUTED, (strip.centerx, strip.y + 40))
            if name == "pets" and not cacos.owned_pets():
                tag = pygame.Rect(card.right - 58, card.y + 8, 50, 16)
                screen.fill((250, 210, 90), tag)
                ui.text(screen, "NOVO", theme.XS, (70, 40, 20), tag.center, shadow=False)
            self._frame(screen, card, color, on)

    def _showcase(self, screen, card, t, on):
        """Três skins de vitrine no card: a do meio grande, girando entre todas de tempos em tempos."""
        mine = [s for s in self.order if s.hero == self.hero]
        if mine and (t // 150) % 2 == 0:            # a skin do seu herói aparece no meio de vez em quando
            start = self.order.index(mine[(t // 300) % len(mine)])
        else:
            start = (t // 150) % len(self.order)
        picks = [self.order[(start + k) % len(self.order)] for k in (1, 0, 2)]
        places = ((-78, 0.9, 120), (0, 1.5, 255), (78, 0.9, 120))
        for skin, (dx, scale, alpha) in zip(picks, places):
            sprites = self.match.assets.skin_sprites(skin.key)
            if sprites is None:
                continue
            img = sprites.frame("frente", t // 8 if (on and dx == 0) else 0)
            img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
            spot = img.get_rect(midbottom=(card.centerx + dx, card.bottom - 66))
            if dx == 0:
                halo = pygame.Surface((160, 160), pygame.SRCALPHA)
                for rad, a in ((76, 26), (54, 36), (34, 46)):
                    pygame.draw.circle(halo, (*skin.color, a), (80, 80), rad)
                screen.blit(halo, halo.get_rect(center=(spot.centerx, spot.centery)))
                pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 26, spot.bottom - 6, 52, 12))
                draw_back(screen, skin.key, spot, t)
                screen.blit(img, spot)
                draw_front(screen, skin.key, spot, t)
            else:
                img.set_alpha(alpha)
                screen.blit(img, spot)

    def _pet_showcase(self, screen, card, t, on):
        """Três pets passeando no card: o do meio grande, trocando de tempos em tempos."""
        pets = list(PETS.values())
        start = (t // 150) % len(pets)
        picks = [pets[(start + k) % len(pets)] for k in (1, 0, 2)]
        for pet, (dx, scale, alpha) in zip(picks, ((-84, 1.4, 130), (0, 2.4, 255), (84, 1.4, 130))):
            img = pet_image(pet.key, on and dx == 0 and (t // 20) % 2)
            if img is None:
                continue
            img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
            bob = math.sin(t * 0.1 + dx) * 3 if pet.flies else 0
            spot = img.get_rect(midbottom=(card.centerx + dx, card.bottom - 72 + bob - (24 if pet.flies else 0)))
            if dx == 0:
                halo = pygame.Surface((160, 160), pygame.SRCALPHA)
                for rad, a in ((70, 26), (50, 36), (30, 46)):
                    pygame.draw.circle(halo, (*pet.color, a), (80, 80), rad)
                screen.blit(halo, halo.get_rect(center=spot.center))
                pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 30, card.bottom - 78, 60, 12))
            else:
                img.set_alpha(alpha)
            screen.blit(img, spot)

    # a grade de cartas
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
        screen.fill((8, 6, 12), card.move(3, 4))                          # sombra da carta
        self._gradient(screen, card, *(RARE_BG if skin.rarity == "rara" else SHOP_BG))
        # brilho atrás do herói, na cor da skin
        halo = pygame.Surface((card.width, card.width), pygame.SRCALPHA)
        for rad, alpha in ((44, 30), (32, 40), (20, 50)):
            pygame.draw.circle(halo, (*skin.color, alpha), (card.width // 2, card.width // 2), rad)
        screen.blit(halo, (card.x, card.y + 4))
        if skin.rarity == "rara" and on:                                   # raios girando na rara marcada
            rays = pygame.Surface(card.size, pygame.SRCALPHA)
            cx, cy = card.width // 2, 50
            for k in range(6):
                a = t * 0.02 + k * math.pi / 3
                pts = [(cx, cy), (cx + math.cos(a) * 80, cy + math.sin(a) * 80),
                       (cx + math.cos(a + 0.22) * 80, cy + math.sin(a + 0.22) * 80)]
                pygame.draw.polygon(rays, (255, 226, 150, 46), pts)
            screen.blit(rays, card.topleft)
        sprites = None if isinstance(skin, ShopPet) else self.match.assets.skin_sprites(skin.key)
        if isinstance(skin, ShopPet):
            img = pet_image(skin.key, on and (t // 20) % 2)
            if img is not None:
                img = pygame.transform.scale(img, (round(img.get_width() * 1.6), round(img.get_height() * 1.6)))
                bob = round(math.sin(t * 0.12) * 2) if skin.flies else 0
                spot = img.get_rect(midbottom=(card.centerx, card.bottom - 30 + bob - (8 if skin.flies else 0)))
                pygame.draw.ellipse(screen, (0, 0, 0), (card.centerx - 22, card.bottom - 34, 44, 8))
                screen.blit(img, spot)
        if sprites is not None:
            img = sprites.frame("frente", t // 8 if on else 0)
            spot = img.get_rect(midbottom=(card.centerx, card.bottom - 26))
            pygame.draw.ellipse(screen, (0, 0, 0), (spot.centerx - 18, spot.bottom - 4, 36, 8))
            if on:
                draw_back(screen, skin.key, spot, t)
            screen.blit(img, spot)
            if on:
                draw_front(screen, skin.key, spot, t)
        # selo de raridade
        if skin.rarity == "rara":
            tag = pygame.Rect(card.x + 4, card.y + 4, 34, 13)
            screen.fill((250, 210, 90), tag)
            ui.text(screen, "RARA", theme.XS, (70, 30, 90), tag.center, shadow=False)
        if skin.hero is not None and skin.hero == self.hero:              # selo do herói de quem abriu
            tag = pygame.Rect(card.x, card.bottom - 35, card.width, 13)
            screen.fill(theme.SLOT_COLORS.get(self.fighter.slot, theme.BONE), tag)
            ui.text(screen, "SEU HERÓI", theme.XS, theme.INK, tag.center, shadow=False)
        # faixa de baixo: preço, cadeado ou VESTIDA
        strip = pygame.Rect(card.x, card.bottom - 22, card.width, 22)
        screen.fill((14, 12, 22), strip)
        if state == "comprar":
            ok = cacos.balance() >= skin.price
            draw_caco(screen, strip.centerx - 18, strip.centery, t)
            ui.text(screen, str(skin.price), theme.XS, CACO_COLOR if ok else theme.BLOOD,
                    (strip.centerx - 8, strip.centery + 1), anchor="midleft")
        elif state == "cupom":
            self._lock(screen, strip.centerx - 26, strip.centery)
            ui.text(screen, "CUPOM", theme.XS, theme.MUTED, (strip.centerx - 16, strip.centery + 1), anchor="midleft")
        elif state == "tirar":
            screen.fill(theme.MOSS, strip)
            ui.text(screen, "VESTIDA", theme.XS, theme.INK, (strip.centerx, strip.centery + 1), shadow=False)
        else:
            ui.text(screen, "É SEU" if isinstance(skin, ShopPet) else "É SUA", theme.XS, theme.BONE,
                    (strip.centerx, strip.centery + 1))
        if state == "cupom" and not on:                                   # rara trancada: mais apagada
            veil = pygame.Surface((card.width, card.height - 22), pygame.SRCALPHA)
            veil.fill((10, 8, 16, 90))
            screen.blit(veil, card.topleft)
        self._frame(screen, card, skin.color, on)

    def _lock(self, screen, x, y):
        pygame.draw.rect(screen, theme.MUTED, (x - 3, y - 7, 7, 6), 1)
        screen.fill(theme.MUTED, (x - 4, y - 2, 9, 7))
        screen.fill((14, 12, 22), (x, y, 1, 3))

    def _draw_ticket(self, screen, ui, card, on):
        t = self.match.frame
        screen.fill((8, 6, 12), card.move(3, 4))
        screen.fill(PAPER, card)
        screen.fill((120, 200, 255), (card.x, card.y, card.width, 18))
        ui.text(screen, "CUPOM", theme.XS, (20, 40, 80), (card.centerx, card.y + 9), shadow=False)
        for k in range(card.x + 4, card.right - 4, 6):                    # picote
            screen.fill((190, 176, 140), (k, card.y + 70, 3, 1))
        for side in (card.x, card.right):                                 # mordidinhas do ingresso
            pygame.draw.circle(screen, theme.INK_2, (side, card.y + 70), 6)
        bob = math.sin(t * 0.08) * 2 if on else 0
        draw_caco(screen, card.centerx, card.y + 42 + bob, t, size=12)
        ui.text(screen, "+CACOS", theme.XS, (60, 70, 110), (card.centerx, card.y + 84), shadow=False)
        strip = pygame.Rect(card.x, card.bottom - 22, card.width, 22)
        screen.fill((14, 12, 22), strip)
        ui.text(screen, "INSERIR", theme.XS, CACO_COLOR, (strip.centerx, strip.centery + 1))
        self._frame(screen, card, CACO_COLOR, on)

    # a barra de baixo: nome, herói, descrição e o botão da ação
    def _draw_detail(self, screen, ui, bar, skin):
        screen.fill((16, 14, 24), bar)
        pygame.draw.rect(screen, theme.LINE, bar, 1)
        button = pygame.Rect(bar.right - 150, bar.y + 10, 140, 30)
        if skin is None:
            ui.text(screen, "INSERIR CUPOM", theme.S, CACO_COLOR, (bar.x + 10, bar.y + 16), anchor="midleft")
            ui.text(screen, "DÁ CACOS E, ÀS VEZES, UMA SKIN RARA",
                    theme.XS, theme.MUTED, (bar.x + 10, bar.y + 36), anchor="midleft")
            self._button(screen, ui, button, "TECLA USAR" if self.typing else "DIGITAR", CACO_COLOR, theme.INK)
            return
        state = state_of(skin)
        ui.text(screen, skin.name, theme.S if len(skin.name) <= 24 else theme.XS, skin.color,
                (bar.x + 10, bar.y + 16), anchor="midleft")
        sub = ("PET" if isinstance(skin, ShopPet) else HERO_NAMES.get(skin.hero, "")) + " · " + skin.blurb
        room = button.x - bar.x - 20
        while len(sub) > 8 and ui.assets.text(sub, theme.XS, theme.MUTED).get_width() > room:
            sub = sub[:-2].rstrip(" ,·") + "…"
        ui.text(screen, sub, theme.XS, theme.MUTED, (bar.x + 10, bar.y + 36), anchor="midleft")
        if state == "comprar":
            ok = cacos.balance() >= skin.price
            self._button(screen, ui, button, f"COMPRAR {skin.price}", CACO_COLOR if ok else theme.FAINT, theme.INK,
                         caco=True)
        elif state in ("vestir", "tirar"):
            self._button(screen, ui, button, "PEGAR NO ARMÁRIO" if isinstance(skin, ShopPet) else "VESTIR NO ARMÁRIO",
                         theme.LINE_HI, theme.BONE)
        else:
            self._button(screen, ui, button, "SÓ COM CUPOM", theme.LINE, theme.MUTED)

    def _button(self, screen, ui, rect, label, fill, ink, caco=False):
        screen.fill((8, 6, 12), rect.move(0, 3))
        screen.fill(fill, rect)
        screen.fill(tuple(min(255, c + 40) for c in fill), (rect.x, rect.y, rect.width, 2))
        if caco:
            draw_caco(screen, rect.right - 16, rect.centery, self.match.frame)
            ui.text(screen, label, theme.XS, ink, (rect.centerx - 8, rect.centery + 1), shadow=False)
        else:
            ui.text(screen, label, theme.XS, ink, (rect.centerx, rect.centery + 1), shadow=False)

    # o cupom na TV: ingresso com o código e o teclado na tela
    def _draw_coupon(self, screen, ui, area):
        t = self.match.frame
        ticket = pygame.Rect(area.x + 14, area.y + 20, 200, 200)
        screen.fill((8, 6, 12), ticket.move(3, 4))
        screen.fill(PAPER, ticket)
        screen.fill((120, 200, 255), (ticket.x, ticket.y, ticket.width, 24))
        ui.text(screen, "CUPOM", theme.S, (20, 40, 80), (ticket.centerx, ticket.y + 13), shadow=False)
        draw_caco(screen, ticket.centerx, ticket.y + 70, t, size=16)
        box = pygame.Rect(ticket.x + 12, ticket.y + 118, ticket.width - 24, 26)
        screen.fill((255, 255, 250), box)
        pygame.draw.rect(screen, (120, 200, 255), box, 2)
        blink = "_" if (t // 20) % 2 else ""
        ui.text(screen, (self.code + blink) or "DIGITE AQUI", theme.XS,
                (30, 30, 40) if self.code else (150, 150, 160), box.center, shadow=False)
        for i, line in enumerate(("VALE UMA VEZ POR SAVE", "OU DIGITE NO CELULAR")):
            ui.text(screen, line, theme.XS, (90, 90, 110), (ticket.centerx, ticket.y + 160 + i * 14), shadow=False)
        keys = pygame.Rect(ticket.right + 20, area.y + 20, area.right - ticket.right - 34, 200)
        rows = self._keys()
        for r, row in enumerate(rows):
            cw = keys.width // len(row)
            for c, k in enumerate(row):
                cell = pygame.Rect(keys.x + c * cw, keys.y + r * 40, cw - 4, 34)
                on = (r, c) == self.key
                screen.fill((8, 6, 12), cell.move(0, 3))
                screen.fill(CACO_COLOR if on else (44, 42, 58), cell)
                ui.text(screen, k, theme.XS if len(k) > 1 else theme.S, (20, 20, 30) if on else theme.BONE,
                        (cell.centerx, cell.centery + 1), shadow=False)
