"""Imagens "ao vivo" da EDIÇÃO EXTRAORDINÁRIA do plantão (a rodada grande da 1.56.0).

Cada função desenha uma notícia dentro da TV (``rect``) no quadro ``t``, com as peças reais do
jogo: ícones das armas, dos equipamentos, as folhas dos pets, os bonecos e os vendedores.
``plantao.FOOTAGE`` junta estas com as antigas; uma notícia escolhe a sua com "tv" em novidades.py.
"""
import math

import pygame

from .. import equipamento, mascotes, pecas, theme, weapon_art

RED = (214, 52, 52)
RED_D = (120, 24, 30)
GOLD = (255, 222, 120)
PAPER = (246, 238, 214)
VIOLET = (170, 120, 250)

# armas novas da rodada que entram no carrossel (todas têm arte em assets/weapons)
ARSENAL = ("Tocha", "Bisturi", "Cadeira Gamer", "Fax Lança-Papéis", "Estilingue de Galho", "Maçarico Quente de Fogo",
           "Grampeador Industrial", "Pistola de Água Molhada", "Cajado do Gelo Gelado", "Boleto Bumerangue",
           "Mangual de Ossos", "Taser Elétrico Eletrizante", "Guarda-chuva Executivo", "Laser Depilador",
           "Bomba Explosiva que Explode", "Martelo Martelador", "Espelho de Selfie", "Sino Fúnebre")
BAG = ("Tocha", "Cadeira Gamer", "Bisturi", "Fax Lança-Papéis", "Estilingue de Galho")
FORGE_IN = ("Maçarico Quente de Fogo", "Secador de Cabelo", "Tocha")
PETS = ("gato", "cachorro", "papagaio", "capivara", "mico", "tuiuiu", "jabuti", "drone", "caquinho")
PET_SAYS = ("MIAU", "AU AU!", "CURRUPACO!", "HMMM...", "IIII!", "TÁ TÁ TÁ", "...", "BIP BIP", "TLIN!")
COUNTERS = (("46", "ARMAS NOVAS"), ("41", "FORJADAS"), ("12", "EQUIPAMENTOS"), ("9", "PETS COM VIDA"),
            ("17", "SEGREDOS"), ("20+", "MÚSICAS"))


# ── peças ────────────────────────────────────────────────────────────────
def _cover(screen, ui, key, rect):
    from .menus import cover_image
    try:
        screen.blit(cover_image(ui.assets, key, rect.size), rect)
    except Exception:                                    # mapa que não carregou: fundo liso
        screen.fill((20, 18, 28), rect)


def _shade(screen, rect, alpha=120, color=(8, 6, 14)):
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    layer.fill((*color, alpha))
    screen.blit(layer, rect.topleft)


def _scale(img, k):
    return pygame.transform.scale(img, (round(img.get_width() * k), round(img.get_height() * k)))


def _weapon(name, k=1.0):
    img = weapon_art.icon2x(name)
    if img is None:
        return None
    return _scale(img, k) if k != 1 else img


def _glow(screen, center, radius, color, strength=60):
    """Brilho suave: anéis bem transparentes, mais fortes no meio (sem estourar o fundo claro)."""
    halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -6):
        pygame.draw.circle(halo, (*color, max(1, round(strength * 0.12))), (radius, radius), r)
    screen.blit(halo, (center[0] - radius, center[1] - radius))


def _actor(screen, ui, name, x, y, direction="frente", kind="parado", i=0, k=1, slot=None):
    from .plantao import actor
    return actor(screen, ui, name, x, y, direction, kind, i, k=k, slot=slot)


def _bubble(screen, ui, text, x, y, color=theme.INK):
    w = ui.assets.text_width(text, theme.XS) + 14
    box = pygame.Rect(0, 0, w, 18)
    box.midbottom = (x, y)
    screen.fill((0, 0, 0), box.move(2, 2))
    screen.fill(theme.BONE, box)
    pygame.draw.polygon(screen, theme.BONE, [(x - 4, box.bottom), (x + 4, box.bottom), (x, box.bottom + 5)])
    ui.text(screen, text, theme.XS, color, box.center, shadow=False)


def _slot(screen, rect, lit, color=theme.BRASS):
    screen.fill((0, 0, 0), rect.move(2, 2))
    screen.fill((30, 26, 40), rect)
    pygame.draw.rect(screen, color if lit else theme.LINE_HI, rect, 2)


def _ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


# ── abertura da edição extraordinária ───────────────────────────────────
def tv_extra(screen, ui, rect, t):
    """O estúdio com a faixa URGENTE correndo e os números da rodada subindo, um por um."""
    from .plantao import tv_estudio
    tv_estudio(screen, ui, rect, t, "EDIÇÃO EXTRAORDINÁRIA")
    _shade(screen, rect, 150)
    band = pygame.Rect(rect.x, rect.y + 186, rect.w, 14)          # a faixa correndo por cima da bancada
    screen.fill(RED_D if (t // 20) % 2 else RED, band)
    word = "URGENTE  ·  "
    span = ui.assets.text_width(word, theme.XS)
    x = rect.x - (t * 2) % span
    clip = screen.get_clip()
    screen.set_clip(band)
    while x < rect.right:
        ui.text(screen, word, theme.XS, (255, 255, 255), (x, band.centery + 1), anchor="midleft", shadow=False)
        x += span
    screen.set_clip(clip)
    # os números da rodada: cada quadrinho entra e conta até o valor
    shown = min(len(COUNTERS), max(0, (t - 10) // 20 + 1))
    w, h, gap = 112, 56, 12
    x0 = rect.centerx - (3 * w + 2 * gap) // 2
    for i, (value, label) in enumerate(COUNTERS[:shown]):
        age = t - 10 - i * 20
        col, row = i % 3, i // 3
        box = pygame.Rect(x0 + col * (w + gap), rect.y + 42 + row * (h + 14) - round(10 * (1 - _ease(age / 12))), w, h)
        screen.fill((0, 0, 0), box.move(3, 3))
        screen.fill((26, 20, 38), box)
        pygame.draw.rect(screen, theme.BRASS, box, 2)
        screen.fill(RED, (box.x, box.y, box.w, 3))
        digits = value.rstrip("+")
        n = min(int(digits), round(int(digits) * _ease(age / 30)))
        ui.text(screen, f"{n}{'+' if value.endswith('+') else ''}", theme.M, GOLD, (box.centerx, box.y + 22))
        ui.text(screen, label, theme.XS, theme.BONE, (box.centerx, box.bottom - 12), shadow=False)


# ── arsenal ─────────────────────────────────────────────────────────────
def tv_arsenal(screen, ui, rect, t):
    """46 ARMAS: o carrossel de armas novas girando em volta da Excalitora fincada na pedra."""
    _cover(screen, ui, "chapter4", rect)
    _shade(screen, rect, 120)
    cx, cy = rect.centerx, rect.y + 160
    n = len(ARSENAL)
    items = []
    for i, name in enumerate(ARSENAL):
        a = t * 0.012 + i * math.tau / n
        depth = (math.sin(a) + 1) / 2                     # 0 = atrás, 1 = na frente
        items.append((depth, name, cx + math.cos(a) * 200, cy + math.sin(a) * 44))
    items.sort()
    behind = [it for it in items if it[0] < 0.5]
    front = [it for it in items if it[0] >= 0.5]

    def draw(group):
        for depth, name, x, y in group:
            img = _weapon(name, 0.7 + 0.5 * depth)
            if img is None:
                continue
            if depth < 0.5:
                img = img.copy()
                img.fill((110, 110, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(img, img.get_rect(center=(round(x), round(y))))

    draw(behind)
    # a Excalitora em pé no meio do carrossel (com a pedra de inscrição grudada no cabo)
    _glow(screen, (cx, cy - 30), 56, (255, 230, 150), 18 + round(8 * math.sin(t * 0.08)))
    sword = _weapon("Excalitora", 0.45)
    if sword is not None:
        sword = pygame.transform.rotate(sword, 90)
        screen.blit(sword, sword.get_rect(midbottom=(cx, cy + 22 + round(3 * math.sin(t * 0.1)))))
    draw(front)
    ui.text(screen, "EXCALITORA", theme.S, GOLD, (cx, rect.y + 26))
    ui.text(screen, "TIRADA DA PEDRA DE INSCRIÇÃO", theme.XS, theme.BONE, (cx, rect.y + 46))
    name = items[-1][1]                                   # a da frente do carrossel
    ui.text(screen, f"NA FRENTE: {name.upper()}", theme.XS, theme.MUTED, (cx, rect.y + 64), shadow=False)


def tv_bolsa(screen, ui, rect, t):
    """BOLSA DE 3 ARMAS: arma nova voa para a vaga e a da mão cai no chão, à vista de todo mundo."""
    _cover(screen, ui, "chapter1", rect)
    cycle = 150
    k, turn = t % cycle, (t // cycle) % len(BAG)
    hx, hy = rect.x + 150, rect.y + 214
    bag = [BAG[(turn + i) % len(BAG)] for i in range(3)]
    new = BAG[(turn + 3) % len(BAG)]
    hand = 1
    # as 3 vagas, igual ao quadro do jogador na TV
    panel = pygame.Rect(rect.x + 270, rect.y + 34, 214, 86)
    screen.fill((0, 0, 0), panel.move(3, 3))
    screen.fill((20, 16, 30), panel)
    pygame.draw.rect(screen, theme.SLOT_COLORS[1], panel, 2)
    ui.text(screen, "P1 · BOLSA", theme.XS, theme.SLOT_COLORS[1], (panel.x + 10, panel.y + 12), anchor="midleft")
    slots = [pygame.Rect(panel.x + 12 + i * 66, panel.y + 24, 58, 50) for i in range(3)]
    flying = k < 60
    for i, (box, name) in enumerate(zip(slots, bag)):
        _slot(screen, box, i == hand, theme.SLOT_COLORS[1])
        if i == hand and not flying:
            name = new
        img = _weapon(name, 0.8)
        if img is not None:
            screen.blit(img, img.get_rect(center=box.center))
    ui.text(screen, "NA MÃO", theme.XS, theme.SLOT_COLORS[1], (slots[hand].centerx, panel.bottom + 10))
    _actor(screen, ui, "guerreiro", hx, hy, "direita", "parado", 0, k=2)
    gx0, gy0 = rect.x + 420, rect.y + 214
    if flying:                                           # a arma nova sai do chão e vai para a vaga da mão
        f = _ease(k / 60)
        ex, ey = slots[hand].center
        x = gx0 + (ex - gx0) * f
        y = gy0 + (ey - gy0) * f - math.sin(f * math.pi) * 50
        img = _weapon(new, 1.0)
        if img is not None:
            screen.blit(img, img.get_rect(center=(round(x), round(y))))
    else:                                                # a velha cai do lado do herói e fica no chão
        f = _ease((k - 60) / 30)
        img = _weapon(bag[hand], 1.0)
        if img is not None:
            gx, gy = hx + 50 + round(90 * f), hy - 10 - round(math.sin(f * math.pi) * 60)
            if f >= 1:
                pygame.draw.ellipse(screen, theme.BRASS if (k // 8) % 2 else theme.LINE_HI, (gx - 30, gy + 6, 60, 14), 2)
            screen.blit(img, img.get_rect(center=(gx, gy)))
            if f >= 1:
                ui.text(screen, "FICA NO CHÃO", theme.XS, theme.BONE, (gx, gy - 26))


def tv_energia(screen, ui, rect, t):
    """ENERGIA QUE VOLTA: cada acerto depois da habilidade devolve +3, e o orbe grande dá +15."""
    _cover(screen, ui, "duel", rect)
    k = t % 180
    hx, hy = rect.x + 170, rect.y + 214
    hit = (k // 22) % 2 == 1 and k < 132
    _actor(screen, ui, "ninja", hx, hy, "direita", "ataque" if hit else "parado", k // 5, k=2, slot=1)
    _actor(screen, ui, "golem", hx + 120, hy, "esquerda", "dano" if hit else "parado", 0, k=2)
    gained = min(5, k // 44 + (1 if k % 44 >= 22 else 0)) * 3 if k < 132 else 15
    if k >= 132:                                          # o orbe grande do elite
        f = _ease((k - 132) / 24)
        ox = rect.x + 420 - round(250 * f)
        _glow(screen, (ox, hy - 60), 26, (120, 200, 255), 90)
        pygame.draw.circle(screen, (180, 230, 255), (ox, hy - 60), 9)
        gained = 15 + (15 if f >= 1 else 0)
    if hit:
        ui.text(screen, "+3", theme.S, (120, 210, 255), (hx + 120, hy - 120 - (k % 22)))
    # a barra de energia grande, enchendo
    bar = pygame.Rect(rect.x + 60, rect.y + 40, 250, 18)
    screen.fill((0, 0, 0), bar.move(2, 2))
    screen.fill((24, 30, 50), bar)
    fill = bar.inflate(-4, -4)
    fill.w = round(fill.w * min(1.0, (40 + gained) / 100))
    screen.fill((90, 170, 250), fill)
    screen.fill((180, 230, 255), (fill.x, fill.y, fill.w, 3))
    pygame.draw.rect(screen, theme.LINE_HI, bar, 2)
    ui.text(screen, f"ENERGIA +{gained}", theme.XS, theme.BONE, (bar.centerx, bar.bottom + 12))
    ui.text(screen, "GOLPE DE PERTO", theme.XS, GOLD, (rect.right - 100, rect.y + 42))
    ui.text(screen, "DE GRAÇA", theme.S, GOLD, (rect.right - 100, rect.y + 60))


def tv_forja(screen, ui, rect, t):
    """41 FORJADAS: o ferreiro martela, três armas viram uma, e o livro de receitas conta."""
    _cover(screen, ui, "treino", rect)
    _shade(screen, rect, 70)
    k = t % 160
    bench = pecas.image("banca_ferreiro_4_frente")
    bx, by = rect.x + 170, rect.y + 214
    smith = pecas.image(f"npc_ferreiro_{'ataque' if (k // 10) % 2 and k < 100 else 'parado'}{(k // 10) % 2}")
    if smith is not None:
        img = _scale(smith, 2)
        screen.blit(img, img.get_rect(midbottom=(bx - 10, by - 30)))
    if bench is not None:
        img = _scale(bench, 1.5)
        screen.blit(img, img.get_rect(midbottom=(bx, by)))
    anvil = (bx + 6, by - 70)
    if k < 100:                                          # as três entram girando na bigorna
        for i, name in enumerate(FORGE_IN):
            a = i * math.tau / 3 + k * 0.08
            r = 90 * (1 - _ease(k / 100))
            img = _weapon(name, 0.8)
            if img is not None:
                screen.blit(img, img.get_rect(center=(round(anvil[0] + math.cos(a) * r),
                                                      round(anvil[1] + math.sin(a) * r * 0.6))))
        if (k // 10) % 2:
            for s in range(6):
                ang = s * math.tau / 6 + k
                pygame.draw.line(screen, GOLD, anvil, (anvil[0] + math.cos(ang) * 18, anvil[1] + math.sin(ang) * 12), 2)
    else:                                                # e sai o Bafo do Dragão
        f = _ease((k - 100) / 20)
        _glow(screen, anvil, 60, (255, 150, 60), round(110 * f))
        img = _weapon("Maçarico Quente de Fogo", 1.4)
        if img is not None:
            screen.blit(img, img.get_rect(center=(anvil[0], anvil[1] - round(20 * f))))
        ui.text(screen, "BAFO DO DRAGÃO", theme.S, GOLD, (anvil[0], anvil[1] - 60))
        ui.text(screen, "FORJADA SECRETA", theme.XS, theme.BONE, (anvil[0], anvil[1] - 40))
    # o livro de receitas aberto à direita
    book = pygame.Rect(rect.right - 196, rect.y + 46, 160, 116)
    screen.fill((0, 0, 0), book.move(4, 4))
    screen.fill((120, 60, 40), book.inflate(10, 10))
    screen.fill(PAPER, book)
    screen.fill((160, 120, 90), (book.centerx - 1, book.y, 2, book.h))
    found = 12 + (1 if k >= 110 else 0)
    ui.text(screen, "RECEITAS", theme.XS, (90, 50, 30), (book.x + 40, book.y + 12), shadow=False)
    ui.text(screen, f"{found}/49", theme.XS, RED_D, (book.right - 40, book.y + 12), shadow=False)
    for i in range(5):
        y = book.y + 32 + i * 16
        ok = i < 2 or (i == 2 and k >= 110)
        text = ("KATANA BRASA", "MARTELO SOLAR", "BAFO DO DRAGÃO", "???", "???")[i] if ok or i > 2 else "???"
        ui.text(screen, text if ok else "???", theme.XS, (60, 40, 30) if ok else (170, 150, 130),
                (book.x + 8, y), anchor="midleft", shadow=False)
    ui.text(screen, "HÍBRIDAS · ASSINATURA", theme.XS, theme.BONE, (book.centerx, book.bottom + 18))
    ui.text(screen, "SECRETAS", theme.XS, GOLD, (book.centerx, book.bottom + 32))


def tv_equipamento(screen, ui, rect, t):
    """12 EQUIPAMENTOS: a vitrine com os doze, e o que está aceso mostra o nome."""
    _cover(screen, ui, "chapter2", rect)
    _shade(screen, rect, 140)
    keys = list(equipamento.GEAR)
    lit = (t // 40) % len(keys)
    cols, size, gap = 6, 56, 14
    x0 = rect.centerx - (cols * size + (cols - 1) * gap) // 2
    for i, key in enumerate(keys):
        box = pygame.Rect(x0 + (i % cols) * (size + gap), rect.y + 40 + (i // cols) * (size + 18), size, size)
        on = i == lit
        _slot(screen, box, on)
        if on:
            _glow(screen, box.center, 46, equipamento.GEAR[key].color, 70)
        img = equipamento.icon(key, 5 if on else 4)
        screen.blit(img, img.get_rect(center=(box.centerx, box.centery - (2 if on else 0))))
    g = equipamento.GEAR[keys[lit]]
    ui.text(screen, g.name.upper(), theme.S, GOLD, (rect.centerx, rect.y + 186))
    ui.text(screen, g.desc.upper(), theme.XS, theme.BONE, (rect.centerx, rect.y + 206))


def tv_pets(screen, ui, rect, t):
    """PETS COM VIDA: os 9 passeando, cada um com o seu jeito e um balão de fala com som."""
    _cover(screen, ui, "chapter1", rect)
    talker = (t // 50) % len(PETS)
    for i, pet in enumerate(PETS):
        row, col = divmod(i, 5)
        x = rect.x + 64 + col * 98 + row * 48
        y = rect.y + 140 + row * 80
        anim = ("andando", "parado", "feliz", "especial", "dormindo")[(i + t // 120) % 5]
        frames = mascotes.frames(pet, anim) or mascotes.frames(pet, "parado")
        if not frames:
            continue
        img = _scale(frames[(t // mascotes.SPEED.get(anim, 8)) % len(frames)], 2)
        pygame.draw.ellipse(screen, (8, 6, 12), (x - 20, y - 6, 40, 10))
        screen.blit(img, img.get_rect(midbottom=(x, y)))
        if i == talker:
            _bubble(screen, ui, PET_SAYS[i], x, y - img.get_height() - 4)
        if anim == "dormindo":
            ui.text(screen, "z" if (t // 20) % 2 else "Z", theme.XS, theme.MUTED, (x + 18, y - img.get_height()))
    ui.text(screen, "6 ANIMAÇÕES · FALAS COM SOM · BUSCAM ITEM", theme.XS, theme.BONE, (rect.centerx, rect.y + 28))


def tv_trilha(screen, ui, rect, t):
    """TRILHA NOVA: o equalizador de orquestra, com as três camadas da luta acendendo."""
    screen.fill((12, 8, 22), rect)
    _glow(screen, (rect.centerx, rect.y + 190), 200, (90, 40, 160), 40)
    bars = 40
    w = (rect.w - 60) // bars
    base = rect.y + 214
    layer = min(3, (t // 90) % 4 + 1)
    for i in range(bars):
        h = 20 + 60 * layer / 3 * (0.5 + 0.5 * math.sin(t * 0.12 + i * 0.55)) * (0.6 + 0.4 * math.sin(i * 1.7 + t * 0.05))
        x = rect.x + 30 + i * w
        for y in range(base - round(h), base, 6):
            k = (base - y) / 140
            screen.fill((round(120 + 135 * k), round(80 + 60 * (1 - k)), round(240 - 120 * k)), (x, y, w - 3, 4))
        screen.fill((60, 40, 90), (x, base + 4, w - 3, round(h * 0.25)))
    for i in range(5):                                   # notas subindo
        y = base - ((t * 1.3 + i * 47) % 170)
        x = rect.x + 60 + i * 96 + round(10 * math.sin(t * 0.05 + i))
        pygame.draw.circle(screen, GOLD, (x, round(y)), 5)
        pygame.draw.line(screen, GOLD, (x + 4, round(y)), (x + 4, round(y) - 18), 2)
        pygame.draw.line(screen, GOLD, (x + 4, round(y) - 18), (x + 11, round(y) - 12), 2)
    for i, name in enumerate(("EXPLORAR", "COMBATE", "FÚRIA")):
        box = pygame.Rect(rect.x + 80 + i * 130, rect.y + 44, 110, 18)
        on = i < layer
        screen.fill(VIOLET if on else (40, 32, 60), box)
        ui.text(screen, name, theme.XS, theme.INK if on else theme.MUTED, box.center, shadow=False)
    ui.text(screen, "ORQUESTRA · CORO · TAIKOS · SINTETIZADOR", theme.XS, theme.BONE, (rect.centerx, rect.y + 28))


def tv_segredos(screen, ui, rect, t):
    """SEGREDOS: o caderno aberto, quase tudo ???, e um segredo achado ganhando o ✓ e os cacos."""
    _cover(screen, ui, "chapter3", rect)
    _shade(screen, rect, 120)
    book = pygame.Rect(rect.x + 90, rect.y + 30, 340, 168)
    screen.fill((0, 0, 0), book.move(5, 5))
    screen.fill((150, 50, 50), book.inflate(12, 12))
    screen.fill(PAPER, book)
    for y in range(book.y + 30, book.bottom, 18):
        pygame.draw.line(screen, (200, 214, 230), (book.x, y), (book.right, y))
    pygame.draw.line(screen, (230, 150, 150), (book.x + 30, book.y), (book.x + 30, book.bottom))
    ui.text(screen, "CADERNO DE SEGREDOS", theme.XS, (120, 40, 40), (book.centerx, book.y + 14), shadow=False)
    k = t % 200
    rows = ("O ESPANTALHO SENTIU", "???", "???", "???", "???", "???", "???")
    for i, text in enumerate(rows):
        y = book.y + 39 + i * 18
        if i == 0:
            shown = text if k >= 60 else "???"
            if k >= 60:
                pygame.draw.line(screen, (60, 150, 80), (book.x + 10, y), (book.x + 14, y + 4), 2)
                pygame.draw.line(screen, (60, 150, 80), (book.x + 14, y + 4), (book.x + 22, y - 5), 2)
            ui.text(screen, shown, theme.XS, (40, 40, 60) if k >= 60 else (150, 150, 160), (book.x + 40, y),
                    anchor="midleft", shadow=False)
        else:
            ui.text(screen, text, theme.XS, (150, 150, 160), (book.x + 40, y), anchor="midleft", shadow=False)
    if 60 <= k < 130:
        ui.text(screen, "+5 CACOS", theme.S, (200, 120, 30), (book.right - 70, book.y + 50 - (k - 60) // 4), shadow=False)
    ui.text(screen, "17 ESCONDIDOS · O JOGO NÃO AVISA", theme.XS, theme.BONE, (rect.centerx, book.bottom + 18))


def _phone(screen, rect):
    ph = rect
    pygame.draw.rect(screen, (0, 0, 0), ph.move(5, 5), border_radius=16)
    pygame.draw.rect(screen, (40, 36, 50), ph, border_radius=16)
    pygame.draw.rect(screen, theme.LINE_HI, ph, 2, border_radius=16)
    scr = ph.inflate(-36, -16)
    screen.fill(theme.INK, scr)
    return scr


def tv_celular(screen, ui, rect, t):
    """CELULAR REMASTERIZADO: a loja em grade de cartões, com quem atende a banca e a falinha."""
    screen.fill((18, 14, 28), rect)
    scr = _phone(screen, pygame.Rect(rect.x + 36, rect.y + 34, 448, 184))
    screen.fill(theme.BLOOD, (scr.x, scr.y, scr.w, 3))
    ui.text(screen, "LOJA", theme.S, GOLD, (scr.x + 40, scr.y + 16))
    ui.text(screen, "ALMAS 240", theme.XS, theme.BONE, (scr.x + 150, scr.y + 16), shadow=False)
    npc = pecas.image(f"npc_mascate_{'ataque' if (t // 40) % 3 == 0 else 'parado'}{(t // 12) % 2}")
    if npc is not None:
        img = _scale(npc, 2)
        screen.blit(img, img.get_rect(midbottom=(scr.right - 60, scr.bottom - 10)))
        _bubble(screen, ui, "OLHA ESSA!", scr.right - 60, scr.bottom - 14 - img.get_height())
    names = ("Tocha", "Bisturi", "Cadeira Gamer", "Estilingue de Galho", "Boleto Bumerangue", "Taser Elétrico Eletrizante")
    sel = (t // 30) % len(names)
    for i, name in enumerate(names):
        card = pygame.Rect(scr.x + 10 + (i % 3) * 94, scr.y + 30 + (i // 3) * 68, 86, 62)
        on = i == sel
        screen.fill((0, 0, 0), card.move(2, 2))
        screen.fill((34, 28, 48) if not on else (52, 40, 70), card)
        pygame.draw.rect(screen, GOLD if on else theme.LINE_HI, card, 2)
        img = _weapon(name, 0.7)
        if img is not None:
            screen.blit(img, img.get_rect(center=(card.centerx, card.y + 24)))
        ui.text(screen, f"{30 + i * 15}", theme.XS, GOLD, (card.centerx, card.bottom - 11), shadow=False)


def tv_janelas(screen, ui, rect, t):
    """JANELAS PEQUENAS: um mexe no computador numa janelinha e o resto da turma anda livre."""
    _cover(screen, ui, "chapter2", rect)
    desk = pecas.image("sala_mesa_pc")
    dx, dy = rect.x + 140, rect.y + 190
    if desk is not None:
        img = _scale(desk, 1.5)
        screen.blit(img, img.get_rect(midbottom=(dx, dy)))
    _actor(screen, ui, "cauanzera", dx, dy + 30, "costas", "parado", 0, slot=1)
    win = pygame.Rect(dx + 40, rect.y + 40, 170, 104)
    screen.fill((0, 0, 0), win.move(3, 3))
    screen.fill((20, 26, 46), win)
    pygame.draw.rect(screen, theme.SLOT_COLORS[1], win, 2)
    screen.fill((40, 70, 120), (win.x + 2, win.y + 2, win.w - 4, 14))
    ui.text(screen, "CAUANZERA OS", theme.XS, (255, 255, 255), (win.x + 8, win.y + 9), anchor="midleft", shadow=False)
    sel = (t // 30) % 4
    for i, label in enumerate(("ARQUIVOS", "NAVEGADOR", "TERMINAL", "CADERNO")):
        row = pygame.Rect(win.x + 6, win.y + 20 + i * 20, win.w - 12, 18)
        screen.fill((60, 80, 130) if i == sel else (30, 36, 60), row)
        ui.text(screen, label, theme.XS, theme.BONE, (row.x + 6, row.centery), anchor="midleft", shadow=False)
    for i, (name, x0, y0) in enumerate((("aryel", 420, 180), ("borba", 380, 226), ("albeguinio", 290, 230))):
        x = rect.x + x0 + round(50 * math.sin(t * 0.03 + i * 2))
        y = rect.y + y0 + round(16 * math.cos(t * 0.025 + i))
        direction = "direita" if math.cos(t * 0.03 + i * 2) > 0 else "esquerda"
        _actor(screen, ui, name, x, y, direction, "andar", t // 6 + i, slot=i + 2)
    ui.text(screen, "QUEM NÃO ESTÁ NA JANELA ANDA LIVRE", theme.XS, theme.BONE, (rect.right - 150, rect.y + 28))


FOOTAGE = {"extra": tv_extra, "arsenal": tv_arsenal, "bolsa": tv_bolsa, "energia": tv_energia, "forja": tv_forja,
           "equipamento": tv_equipamento, "pets": tv_pets, "trilha": tv_trilha, "segredos": tv_segredos,
           "celular_novo": tv_celular, "janelas": tv_janelas}
# assunto de cada imagem (etiqueta e cor da tarja)
TOPIC = {"extra": "plantao", "arsenal": "armas", "bolsa": "armas", "energia": "armas", "forja": "armas",
         "equipamento": "armas", "pets": "casa", "trilha": "som", "segredos": "casa", "celular_novo": "celular",
         "janelas": "casa"}
