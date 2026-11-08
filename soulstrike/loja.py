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
from .skins import CACO_COLOR, SKINS, draw_back, draw_caco, draw_front

STICK = 0.5
REACH = 80
KEY_ROWS = ("ABCDEFGHI", "JKLMNOPQR", "STUVWXYZ0", "123456789")
KEY_ACTIONS = ("APAGAR", "LIMPAR", "USAR")
MAX_CODE = 20
HERO_NAMES = {c.key: c.name.upper() for c in CHARACTERS}
ORDER = sorted(SKINS.values(), key=lambda s: (s.rarity != "rara", s.name))


def state_of(skin):
    """O que dá para fazer com a skin agora: "tirar", "vestir", "comprar" ou "cupom"."""
    if skin.key in cacos.owned():
        return "tirar" if cacos.worn(skin.hero) == skin.key else "vestir"
    return "comprar" if skin.price else "cupom"


ACTION_LABEL = {"tirar": "TIRAR", "vestir": "VESTIR", "comprar": "COMPRAR", "cupom": "SÓ COM CUPOM"}


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

    # ── linhas ───────────────────────────────
    def entries(self):
        rows = [("cupom", None)]
        rows += [(s.key, s) for s in ORDER]
        return rows

    def current(self):
        rows = self.entries()
        return rows[self.index % len(rows)]

    # ── ações ────────────────────────────────
    def buy(self):
        key, skin = self.current()
        if skin is None:
            self.typing = True
            self.key = (0, 0)
            self.match.assets.play("select", 0.4)
            return True
        return self.act(skin)

    def act(self, skin):
        state = state_of(skin)
        play = self.match.assets.play
        if state == "cupom":
            self._say("ESSA SÓ VEM COM UM CUPOM ESPECIAL", theme.BLOOD)
            play("cancel", 0.3)
            return False
        if state == "comprar":
            if not cacos.spend(skin.price):
                self._say(f"FALTAM {skin.price - cacos.balance()} CACOS", theme.BLOOD)
                play("cancel", 0.3)
                return False
            cacos.give_skin(skin.key)
            cacos.wear(skin.hero, skin.key)
            self._say("COMPROU E JÁ VESTIU!", theme.MOSS)
            self._celebrate(skin)
            play("compra", 0.5)
        elif state == "vestir":
            cacos.wear(skin.hero, skin.key)
            self._say(f"{HERO_NAMES.get(skin.hero, '')} VESTIU!", theme.MOSS)
            play("select", 0.45)
        else:
            cacos.wear(skin.hero, None)
            self._say("VOLTOU PARA A ROUPA DE SEMPRE", theme.BONE)
            play("click", 0.4)
        self.match.redress()
        return True

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
            self._say(f"+{amount} CACOS" + (f" E {name}!" if name else "!"), CACO_COLOR)
            if skin in SKINS:
                cacos.wear(SKINS[skin].hero, skin)
                self.index = next(i for i, (k, _) in enumerate(self.entries()) if k == skin)
                self._celebrate(SKINS[skin])
                self.match.redress()
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
        if moved and sy:
            self.index = (self.index + sy) % len(self.entries())
            self.match.assets.play("click", 0.3)
        if inp.pressed("attack") or inp.pressed("confirm"):
            self.buy()
        return True

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
        for i, (k, _) in enumerate(self.entries()):
            if k == key:
                if i != self.index % len(self.entries()):
                    self.match.assets.play("click", 0.3)
                self.index = i
                self.typing = False
                return True
        return False

    # ── celular ──────────────────────────────
    def snapshot(self):
        key, skin = self.current()
        balance = cacos.balance()
        items = [{"id": "cupom", "label": "INSERIR CUPOM", "cost": 0, "desc": "digite o cupom para ganhar cacos",
                  "ok": True, "afford": True, "color": "#78c8ff",
                  "info": {"type": "cupom", "sub": "CACOS E SKIN RARA", "note": self.note[0]}}]
        for s in ORDER:
            state = state_of(s)
            items.append({
                "id": s.key, "label": s.name, "cost": s.price if state == "comprar" else 0,
                "desc": s.blurb, "ok": state != "cupom", "afford": state != "comprar" or balance >= s.price,
                "color": "#%02x%02x%02x" % s.color,
                "info": {"type": "skin", "img": f"/skin/{s.key}.png", "hero": HERO_NAMES.get(s.hero, ""),
                         "sub": {"tirar": "VESTIDA", "vestir": "É SUA", "comprar": f"{s.price} CACOS",
                                 "cupom": "SÓ COM CUPOM"}[state],
                         "rarity": "RARA · CUPOM" if s.rarity == "rara" else "LOJA"},
            })
        action = "USAR CUPOM" if skin is None else ACTION_LABEL[state_of(skin)]
        return {"kind": "cacos", "title": "LOJA DE CACOS", "souls": balance, "unit": "CACOS",
                "picked": key, "mates": [], "items": items, "action": action}

    # ── TV ───────────────────────────────────
    def draw(self, screen, ui, anchor):
        f = self.fighter
        w, h = 520, 300
        x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
        y = max(56, min(config.SCREEN_H - h - 70, round(anchor[1]) - h - 70))
        rect = pygame.Rect(x, y, w, h)
        ui.panel(screen, rect, fill=theme.INK_2, accent=CACO_COLOR)
        ui.text(screen, f"{f.label} · LOJA DE CACOS", theme.XS, theme.BONE, (rect.x + 12, rect.y + 14),
                anchor="midleft")
        balance = cacos.balance()
        draw_caco(screen, rect.right - 20, rect.y + 14, self.match.frame)
        ui.text(screen, f"{balance} CACOS", theme.XS, CACO_COLOR, (rect.right - 32, rect.y + 14), anchor="midright")
        rows = self.entries()
        cur = self.index % len(rows)
        list_w = 250
        for i, (key, skin) in enumerate(rows):
            r = pygame.Rect(rect.x + 8, rect.y + 30 + i * 24, list_w, 22)
            if i == cur:
                screen.fill(theme.INK_3, r)
                pygame.draw.rect(screen, CACO_COLOR if skin is None else skin.color, r, 1)
            if skin is None:
                ui.text(screen, "INSERIR CUPOM", theme.XS, CACO_COLOR, (r.x + 8, r.centery), anchor="midleft")
                continue
            state = state_of(skin)
            color = skin.color if state != "cupom" else theme.FAINT
            label = skin.name if len(skin.name) <= 22 else skin.name[:21] + "…"
            ui.text(screen, label, theme.XS, color, (r.x + 8, r.centery), anchor="midleft")
            tag = {"tirar": "VESTIDA", "vestir": "SUA", "comprar": str(skin.price), "cupom": "CUPOM"}[state]
            tag_color = {"tirar": theme.MOSS, "vestir": theme.BONE, "cupom": theme.FAINT}.get(
                state, CACO_COLOR if balance >= skin.price else theme.FAINT)
            ui.text(screen, tag, theme.XS, tag_color, (r.right - 6, r.centery), anchor="midright")
        side = pygame.Rect(rect.x + list_w + 18, rect.y + 30, w - list_w - 26, h - 62)
        screen.fill((20, 18, 28), side)
        key, skin = rows[cur]
        if self.typing or skin is None:
            self._draw_coupon(screen, ui, side)
        else:
            self._draw_skin(screen, ui, side, skin)
        text, color = self.note
        if text:
            ui.text(screen, text, theme.XS, color, (rect.centerx, rect.bottom - 26))
        hint = ("ANALÓGICO: TECLA · ATACAR: DIGITAR · ESQUIVA: VOLTAR" if self.typing
                else "ATACAR: " + ("ABRIR TECLADO" if skin is None else ACTION_LABEL[state_of(skin)])
                + " · ESQUIVA: FECHAR")
        ui.text(screen, hint, theme.XS, (130, 126, 140), (rect.centerx, rect.bottom - 10))

    def _draw_skin(self, screen, ui, side, skin):
        sprites = self.match.assets.skin_sprites(skin.key)
        t = self.match.frame
        if sprites is not None:
            img = sprites.frame("frente", t // 8)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            spot = img.get_rect(midbottom=(side.centerx, side.y + 172))
            draw_back(screen, skin.key, spot, t)
            screen.blit(img, spot)
            draw_front(screen, skin.key, spot, t)
        ui.text(screen, skin.name, theme.XS, skin.color, (side.centerx, side.y + 186))
        ui.text(screen, "RARA · SÓ COM CUPOM" if skin.rarity == "rara" else "LOJA", theme.XS, theme.MUTED,
                (side.centerx, side.y + 202))
        state = state_of(skin)
        line = {"tirar": "VESTIDA NO " + HERO_NAMES.get(skin.hero, ""), "vestir": "É SUA: ATACAR VESTE",
                "comprar": f"{skin.price} CACOS", "cupom": "CUPOM ESPECIAL"}[state]
        ui.text(screen, line, theme.XS, theme.BONE, (side.centerx, side.y + 218))

    def _draw_coupon(self, screen, ui, side):
        ui.text(screen, "CUPOM", theme.S, CACO_COLOR, (side.centerx, side.y + 16))
        box = pygame.Rect(side.x + 10, side.y + 32, side.width - 20, 24)
        screen.fill((240, 240, 236), box)
        blink = "_" if self.typing and (self.match.frame // 20) % 2 else ""
        ui.text(screen, (self.code + blink) or "DIGITE AQUI", theme.XS,
                (30, 30, 40) if self.code else (150, 150, 160), (box.centerx, box.centery), shadow=False)
        if not self.typing:
            for i, line in enumerate(("CADA CUPOM VALE UMA VEZ", "E DÁ CACOS. ALGUNS DÃO", "UMA SKIN RARA JUNTO.",
                                      "", "NO CELULAR: DIGITE NO", "TECLADO DO CELULAR.")):
                ui.text(screen, line, theme.XS, theme.MUTED, (side.centerx, side.y + 80 + i * 16))
            return
        rows = self._keys()
        for r, row in enumerate(rows):
            cw = (side.width - 20) // len(row)
            for c, k in enumerate(row):
                cell = pygame.Rect(side.x + 10 + c * cw, side.y + 66 + r * 26, cw - 2, 22)
                on = (r, c) == self.key
                screen.fill(CACO_COLOR if on else (44, 42, 58), cell)
                ui.text(screen, k, theme.XS, (20, 20, 30) if on else theme.BONE, cell.center, shadow=False)
