"""Desenho da janelinha da loja, do ferreiro e do altar na TV (MarketMenu.draw).

Mesmo tamanho de sempre (300 de largura, 26 por linha), só que mais caprichado: quem atende no
topo, o saldo com a joia, o ícone de cada item num quadradinho da cor da raridade, uma segunda
linha (dono, motivo, nível em quadradinhos), carimbo no que não dá para comprar, cantoneiras no
item marcado com a arma em tamanho maior ao lado da janela, e o antes > depois do ferreiro.
"""
import math

import pygame

from . import config, pecas, theme, weapon_art

GOLD = (255, 215, 90)
SOUL = (200, 170, 255)
ROW_BG = ((30, 25, 45), (27, 22, 40))
RARITY = {"COMUM": (138, 134, 160), "RARA": (74, 140, 255), "ÉPICA": (180, 90, 255),
          "FORJADA": (255, 90, 168), "LENDÁRIA": (255, 180, 60)}
ITEM_ICON = {"pocao": "pocao", "energia": "raio", "arma": "bau", "trocar": "trocar", "continue": "coracao",
             "doar": "alma"}
IC_DIR = config.ROOT / "web" / "static" / "ic"
_cache = {}


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _load(key, path):
    if key not in _cache:
        img = None
        try:
            img = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            img = None
        _cache[key] = img
    return _cache[key]


def pixel_icon(name):
    return _load(("ic", name), IC_DIR / f"i_{name}.png")


def weapon_icon(info, key):
    """Ícone da arma do item: o pequeno da interface, ou a arte do arquivo."""
    w = info.get("weapon") or (info.get("next") if info.get("type") == "fusao" else None)
    if not w:
        return None
    name = info.get("group") or key.split(":", 1)[-1]
    img = weapon_art.icon(name)
    if img is None and w.get("icon"):
        img = _load(("arma", w["icon"]), config.ASSETS_DIR / "weapons" / w["icon"])
    return img


def fit(img, box):
    """Escala inteira que cabe na caixa; grande demais reduz por um divisor inteiro (sem borrar)."""
    w, h = img.get_size()
    if w <= box and h <= box:
        k = max(1, min(box // w, box // h))
        return pygame.transform.scale(img, (w * k, h * k)) if k > 1 else img
    d = math.ceil(max(w, h) / box)
    return pygame.transform.scale(img, (max(1, w // d), max(1, h // d)))


def gem(surf, cx, cy, color=SOUL):
    pts = [(cx, cy - 4), (cx + 3, cy), (cx, cy + 4), (cx - 3, cy)]
    pygame.draw.polygon(surf, mix(color, (0, 0, 0), .45), [(x + 1, y + 1) for x, y in pts])
    pygame.draw.polygon(surf, color, pts)
    surf.fill(mix(color, (255, 255, 255), .6), (cx - 1, cy - 2, 1, 2))


def brackets(surf, r, color, n=4):
    for x, y, dx, dy in ((r.x, r.y, 1, 1), (r.right - 1, r.y, -1, 1), (r.x, r.bottom - 1, 1, -1),
                         (r.right - 1, r.bottom - 1, -1, -1)):
        surf.fill(color, (min(x, x + dx * (n - 1)), y, n, 1))
        surf.fill(color, (x, min(y, y + dy * (n - 1)), 1, n))


def rarity_of(entry):
    info = entry.info or {}
    if info.get("type") == "fusao":
        return RARITY["FORJADA"]
    w = info.get("weapon")
    return RARITY.get(w.get("rarity"), RARITY["COMUM"]) if w else None


def icon_of(entry):
    info = entry.info or {}
    img = weapon_icon(info, entry.key)
    if img is None:
        img = pixel_icon(ITEM_ICON.get(entry.key.split(":")[0], "bau"))
    return img


def stamp_of(entry):
    sub = ((entry.info or {}).get("sub") or "").upper()
    if "CHEIA" in sub:
        return "CHEIA"
    if "VENDIDA" in sub:
        return "VENDIDA"
    return "MÁX"


def draw(menu, screen, ui, anchor):
    entries = menu.entries()
    f = menu.fighter
    w, row = 300, 26
    h = 50 + row * len(entries) + 24                       # o mesmo tamanho de sempre
    x = max(8, min(config.SCREEN_W - w - 8, round(anchor[0]) - w // 2))
    y = max(60, min(config.SCREEN_H - h - 70, round(anchor[1]) - h - 70))
    rect = pygame.Rect(x, y, w, h)
    ticks = pygame.time.get_ticks()
    ui.panel(screen, rect, fill=(24, 20, 36), accent=f.color)
    _head(menu, screen, ui, rect, ticks)
    wallet = menu.run.wallet(f.slot)
    sel = menu.index % len(entries) if entries else -1
    for k, e in enumerate(entries):
        r = pygame.Rect(rect.x + 6, rect.y + 28 + k * row, w - 12, row - 2)
        _row(screen, ui, e, r, k, k == sel, e.ok and wallet >= e.cost, f.color, ticks)
        if k == sel:
            _zoom(screen, e, r, rect)
    screen.fill(theme.LINE, (rect.x + 8, rect.bottom - 35, w - 16, 1))
    if entries:
        _foot(screen, ui, entries[sel], rect)
    ui.hints(screen, [("ATACAR", "COMPRAR"), ("ESQUIVA", "FECHAR")], (rect.centerx, rect.bottom - 11),
             max_width=w - 16)


def _head(menu, screen, ui, rect, ticks):
    f = menu.fighter
    tag = pygame.Rect(rect.x + 6, rect.y + 7, 20, 14)
    screen.fill(theme.SHADOW, tag.move(1, 1))
    screen.fill(f.color, tag)
    screen.fill(mix(f.color, (255, 255, 255), .4), (tag.x, tag.y, tag.w, 1))
    ui.text(screen, f.label, theme.XS, (255, 255, 255), tag.center, shadow=False)
    tx = tag.right + 6
    npc = pecas.npc_frame(menu.stall.kind, menu.stall.chapter, "parado", (ticks // 500) % 2)
    if npc is not None and npc.get_height() > 26:          # rostinho de quem atende
        fw = min(npc.get_width(), 30)
        box = pygame.Rect(tx, rect.y + 5, fw + 4, 18)
        screen.fill((14, 11, 22), box)
        face = npc.subsurface((max(0, (npc.get_width() - fw) // 2), 8, fw, 16))
        screen.blit(face, (box.x + 2, box.y + 1))
        pygame.draw.rect(screen, theme.LINE_HI, box, 1)
        tx = box.right + 6
    ui.text(screen, menu.stall.title, theme.XS, theme.BRASS, (tx, rect.y + 14), anchor="midleft")
    wallet = str(menu.run.wallet(f.slot))
    ww = ui.assets.text_width(wallet, theme.XS)
    pill = pygame.Rect(rect.right - 18 - ww - 12, rect.y + 7, ww + 22, 14)
    screen.fill((10, 8, 16), pill)
    pygame.draw.rect(screen, (58, 49, 86), pill, 1)
    gem(screen, pill.x + 8, pill.centery)
    ui.text(screen, wallet, theme.XS, SOUL, (pill.right - 5, pill.centery), anchor="midright", shadow=False)


def _row(screen, ui, e, r, k, picked, afford, color, ticks):
    screen.fill(mix(color, (24, 20, 36), .72) if picked else ROW_BG[k % 2], r)
    info = e.info or {}
    # ícone num quadradinho da cor da raridade
    ib = pygame.Rect(r.x + 1, r.y, 24, 24)
    rc = rarity_of(e) or (90, 84, 110)
    screen.fill(theme.SHADOW, ib)
    inner = ib.inflate(-2, -2)
    screen.fill(mix(rc, (14, 11, 22), .62), inner)
    screen.fill(mix(rc, (14, 11, 22), .4), (inner.x, inner.y, inner.w, 1))
    img = icon_of(e)
    if img is not None:
        icon = fit(img, 22)
        if info.get("type") == "fusao" and not info.get("known"):
            icon = icon.copy()
            icon.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        elif not afford:
            icon = icon.copy()
            icon.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(icon, icon.get_rect(center=inner.center))
    # nome e a linha de baixo
    ui.text(screen, e.label, theme.XS, e.color if afford else theme.FAINT, (ib.right + 6, r.y + 8), anchor="midleft")
    sub = info.get("sub") or ""
    sx = ib.right + 6
    if info.get("type") in ("forja", "encanto"):
        lv = (info.get("weapon") or {}).get("level", 0)
        for i in range(3):
            blink = i == lv and picked and (ticks // 300) % 2
            c = GOLD if i < lv or blink else (60, 52, 84)
            screen.fill(theme.SHADOW, (sx + i * 7 + 1, r.y + 15, 5, 5))
            screen.fill(c, (sx + i * 7, r.y + 14, 5, 5))
        sub = e.desc.upper() if info["type"] == "encanto" else ""
        sx += 26
    if sub:
        ui.text(screen, sub, theme.XS, theme.MUTED if picked else theme.FAINT, (sx, r.y + 18), anchor="midleft",
                shadow=False)
    # preço com a joia, ou carimbo de quando não dá
    if not e.ok and e.cost:
        stamp = stamp_of(e)
        sw = ui.assets.text_width(stamp, theme.XS) + 8
        sr = pygame.Rect(r.right - 6 - sw, r.centery - 6, sw, 12)
        pygame.draw.rect(screen, theme.BLOOD, sr, 1)
        ui.text(screen, stamp, theme.XS, theme.BLOOD, sr.center, shadow=False)
    elif e.cost:
        cost = str(e.cost)
        ui.text(screen, cost, theme.XS, SOUL if afford else theme.FAINT, (r.right - 6, r.centery), anchor="midright")
        gem(screen, r.right - 12 - ui.assets.text_width(cost, theme.XS), r.centery, SOUL if afford else theme.FAINT)
    if picked:
        brackets(screen, r.inflate(2, 2), GOLD)
        t = (ticks // 250) % 2
        cx = r.x - 5 + t
        pygame.draw.polygon(screen, GOLD, [(cx, r.centery - 3), (cx + 3, r.centery), (cx, r.centery + 3)])


def _zoom(screen, e, r, rect):
    """A arma do item marcado em tamanho maior, num quadradinho colado na janela (fora dela)."""
    info = e.info or {}
    img = weapon_icon(info, e.key)
    if img is None:
        return
    size = 44
    bx = rect.x - size - 4 if rect.x - size - 4 >= 2 else rect.right + 4
    box = pygame.Rect(bx, max(2, min(config.SCREEN_H - size - 2, r.centery - size // 2)), size, size)
    rc = rarity_of(e) or (90, 84, 110)
    screen.fill(theme.SHADOW, box.move(2, 2))
    screen.fill(theme.SHADOW, box)
    screen.fill(mix(rc, (14, 11, 22), .55), box.inflate(-2, -2))
    screen.fill(mix(rc, (255, 255, 255), .25), (box.x + 1, box.y + 1, box.w - 2, 1))
    brackets(screen, box.inflate(4, 4), GOLD)
    icon = fit(img, size - 6)
    if info.get("type") == "fusao" and not info.get("known"):
        icon = icon.copy()
        icon.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(icon, icon.get_rect(center=box.center))


def _foot(screen, ui, e, rect):
    info = e.info or {}
    wp, nx = info.get("weapon") or {}, info.get("next") or {}
    cy = rect.bottom - 26
    if info.get("type") in ("forja", "encanto") and nx:
        parts = [("DANO ", theme.MUTED), (str(wp.get("damage")), theme.BONE), (" > ", GOLD),
                 (str(nx.get("damage")), theme.MOSS)]
        if wp.get("mag"):
            parts += [("   PENTE ", theme.MUTED), (str(wp.get("mag")), theme.BONE), (" > ", GOLD),
                      (str(nx.get("mag")), theme.MOSS)]
        total = sum(ui.assets.text_width(t, theme.XS) for t, _ in parts)
        px = rect.centerx - total // 2
        for t, c in parts:
            ui.text(screen, t, theme.XS, c, (px, cy), anchor="midleft", shadow=False)
            px += ui.assets.text_width(t, theme.XS)
    else:
        ui.text(screen, e.desc.upper(), theme.XS, theme.MUTED, (rect.centerx, cy))
