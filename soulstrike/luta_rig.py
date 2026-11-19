"""Lutadores altos do modo LUTA: esqueleto + peças com volume, desenhados por código.

Cada quadro é um dicionário de ângulos (veja POSES em luta_poses.py) e vira uma imagem com
os pontos do corpo (mão, pé, cabeça...), que a luta usa para as caixas de golpe e de corpo.

Convenções dos ângulos (graus): 0 = para baixo, 90 = para a frente, 180 = para cima.
  braço: (ombro, cotovelo relativo)            perna: (quadril, joelho relativo, ponta do pé)
  lean: tronco para a frente (+) ou para trás (−)   turn: −1 de costas … 0 de perfil … 1 de peito
  y: abaixa o quadril (quadros "no ar" não são plantados no chão)

Tudo é desenhado em "unidades" e sai em U pixels por unidade (o dobro de detalhe). O lutador
sempre é desenhado virado para a direita; virado para a esquerda é o espelho.
"""
import math

import pygame

U = 2                        # pixels por unidade
CW, CH = 200, 200            # tela de cada quadro, em unidades
GROUND = 186                 # chão, em unidades, dentro do quadro
ROOT_X = 84                  # onde fica o quadril em pé, em unidades


# ── desenho em unidades ──────────────────────────────────────────────
def _p(p):
    return (p[0] * U, p[1] * U)


def _w(width):
    return max(1, round(width * U)) if width else 0


def _r(rect):
    x, y, w, h = rect
    return pygame.Rect(round(x * U), round(y * U), max(1, round(w * U)), max(1, round(h * U)))


class _Draw:
    """pygame.draw que recebe unidades (meia unidade = 1 pixel de verdade)."""

    @staticmethod
    def circle(s, c, center, r, width=0):
        return pygame.draw.circle(s, c, _p(center), r * U, _w(width))

    @staticmethod
    def line(s, c, a, b, width=1):
        return pygame.draw.line(s, c, _p(a), _p(b), _w(width) or 1)

    @staticmethod
    def lines(s, c, closed, pts, width=1):
        return pygame.draw.lines(s, c, closed, [_p(p) for p in pts], _w(width) or 1)

    @staticmethod
    def polygon(s, c, pts, width=0):
        return pygame.draw.polygon(s, c, [_p(p) for p in pts], _w(width))

    @staticmethod
    def ellipse(s, c, rect, width=0):
        return pygame.draw.ellipse(s, c, _r(rect), _w(width))

    @staticmethod
    def rect(s, c, rect, width=0):
        return pygame.draw.rect(s, c, _r(rect), _w(width))

    @staticmethod
    def arc(s, c, rect, a0, a1, width=1):
        return pygame.draw.arc(s, c, _r(rect), a0, a1, _w(width) or 1)


D = _Draw()


def px(s, x, y, c, w=0.5, h=0.5):
    """Ponto fino: meia unidade = 1 pixel de verdade."""
    s.fill(c, (round(x * U), round(y * U), max(1, round(w * U)), max(1, round(h * U))))


# ── contas ───────────────────────────────────────────────────────────
def sh(c, k):
    return tuple(max(0, min(255, int(v + k))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dirv(a):
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def pt(o, a, length):
    d = dirv(a)
    return (o[0] + d[0] * length, o[1] + d[1] * length)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


# ── peças com volume ─────────────────────────────────────────────────
class Body:
    """Cápsulas em 4 camadas (contorno, sombra, base e luz). Entre begin() e flush() as peças são
    desenhadas juntas, camada por camada, e não aparece emenda entre coxa e canela."""

    def __init__(self, surface):
        self.s = surface
        self.q = None

    def begin(self):
        self.q = []

    def flush(self):
        q, self.q = self.q, None
        for layer in range(4):
            for args in q:
                self._blob(*args, only=layer)

    def blob(self, p0, p1, r0, r1, col, bulge=0.0, edge=True, lit=True):
        if self.q is not None:
            self.q.append((p0, p1, r0, r1, col, bulge, edge, lit))
            return
        for layer in range(4):
            self._blob(p0, p1, r0, r1, col, bulge, edge, lit, only=layer)

    def _blob(self, p0, p1, r0, r1, col, bulge, edge, lit, only, n=22):
        if only == 0 and not edge or only == 3 and not lit:
            return
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
        nx, ny = -(p1[1] - p0[1]) / length, (p1[0] - p0[0]) / length
        if nx * -0.6 + ny * -0.8 < 0:            # a luz vem de cima, da frente
            nx, ny = -nx, -ny
        c, dr, off = ((sh(col, -95), 1.0, 0.0), (sh(col, -48), 0.0, 0.0), (col, -0.18, 0.28),
                      (sh(col, 34), -0.55, 0.5))[only]
        steps = max(4, min(n, int(length / 1.2) + 4))
        for i in range(steps + 1):
            t = i / steps
            x, y = lerp(p0, p1, t)
            r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t)
            rr = r + dr if dr >= 0 else r * (1 + dr)
            if rr < 0.4:
                continue
            D.circle(self.s, c, (x + nx * r * off, y + ny * r * off), rr)


def outline(surface, k=0.24):
    """Contorno colorido de 1 pixel: uma cópia bem escura do boneco, deslocada para os 4 lados,
    fica por baixo (rápido: só blits)."""
    w, h = surface.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = surface.copy()
    dark.fill((round(255 * k), round(255 * k * 0.8), round(255 * k * 1.15), 255), special_flags=pygame.BLEND_RGBA_MULT)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out.blit(dark, (dx, dy))
    out.blit(surface, (0, 0))
    return out


# ── o lutador ────────────────────────────────────────────────────────
SEG = {"thigh": 26, "shin": 25, "ua": 19, "fa": 18, "tor": 36}


def segments(L):
    k = L.get("size", 1.0)
    out = {name: v * k for name, v in SEG.items()}
    for name, key in (("ua", "arm"), ("fa", "arm"), ("tor", "torso"), ("thigh", "leg"), ("shin", "leg")):
        out[name] *= L.get(key, 1.0)          # proporção de cada um (braço mais curto, tronco maior...)
    return out


def ankles(L, F):
    """Onde ficam os tornozelos e as pontas dos pés (só a conta, sem desenhar): para plantar no chão."""
    s = segments(L)
    hip = (0, 0)
    out = []
    for tag in ("nl", "fl"):
        spec = F[tag]
        st = F.get("lstretch", 1.0) if tag == "fl" else 1.0
        kn = pt(hip, spec[0], s["thigh"] * st)
        an = pt(kn, spec[0] + spec[1], s["shin"] * st)
        out.append(an)
        foot = spec[2] if len(spec) > 2 else 0
        toe = pt(an, spec[0] + spec[1] + 90 - foot, 9)
        out.append((toe[0], toe[1] - 1.5))       # a ponta do pé também não pode furar o chão
    return out


def standing_hip_y(L):
    s = segments(L)
    return GROUND - 5 - s["shin"] - s["thigh"]


def plant(L, F):
    """Quadro no chão: abaixa ou sobe o quadril para o pé mais baixo encostar no chão."""
    if F.get("air") or "y" in F and F.get("plant") is False:
        return F.get("y", 0)
    low = max(a[1] for a in ankles(L, F))
    s = segments(L)
    return (s["shin"] + s["thigh"]) - low


def draw_fighter(L, F):
    """L = visual do lutador; F = quadro. Devolve (imagem já com contorno, pontos do corpo)."""
    surface = pygame.Surface((CW * U, CH * U), pygame.SRCALPHA)
    b = Body(surface)
    s = surface
    seg = segments(L)
    k = L["build"]
    fem = L.get("fem", False)
    thigh, shin, ua, fa_, tor = seg["thigh"], seg["shin"], seg["ua"], seg["fa"], seg["tor"]
    turn = F.get("turn", 0.25)
    hip = (ROOT_X + F.get("x", 0), standing_hip_y(L) + plant(L, F) + F.get("dy", 0))
    lean = F.get("lean", 0)
    upA = 180 - lean
    neck = pt(hip, upA, tor)
    fwd = dirv(upA + 90)
    skin = L["skin"]

    def far(c, amt=1.0):
        return mix(sh(c, -38 * amt), (40, 30, 70), 0.22 * amt)

    Ws = (6.0 if fem else 9.5) * (0.9 + 0.1 * k) * L.get("shoulders", 1.0)
    Wh = 5.5 if fem else 5.0
    sp = turn
    sh_n = (neck[0] - fwd[0] * Ws * sp + fwd[0] * 1.5, neck[1] + 6 - fwd[1] * Ws * sp)
    sh_f = (neck[0] + fwd[0] * Ws * sp - fwd[0] * 1.5, neck[1] + 5 + fwd[1] * Ws * sp)
    hp_n = (hip[0] - Wh * sp * 0.6 + 2, hip[1])
    hp_f = (hip[0] + Wh * sp * 0.6 - 2, hip[1])
    P = {"hip": hip, "neck": neck}
    sleeve, long_sleeve = L.get("sleeve"), L.get("long_sleeve")

    def arm(sh0, spec, isfar, tag):
        ang, elb = spec[:2]
        b.begin()
        st = F.get("stretch", 1.0) if tag == "far" else F.get("nstretch", 1.0)
        e = pt(sh0, ang, ua * st)
        h = pt(e, ang + elb, fa_ * st)
        amt = 0.6 if (isfar and turn > 0.4) else 1.0
        sk = far(skin, amt) if isfar else skin
        r_u, r_f = (5.2, 3.8) if fem else (6.8 * k + 0.4, 4.8 * k + 0.4)
        loose = L.get("loose", 0.0)
        if loose:                       # roupa folgada: manga larga e reta, sem músculo marcando
            r_u, r_f = r_u + 0.5 * loose, r_f + 1.2 * loose
        up_col = (far(sleeve, amt) if isfar else sleeve) if sleeve else sk
        if not isfar and sleeve:
            # a manga sai do ombro da camisa sem emenda: um pedaço do tronco vai junto no mesmo
            # desenho (de baixo do ombro para o peito, sem subir no pescoço)
            chest = pt(hip, upA, 22)
            b.blob(lerp(sh0, chest, 0.1), lerp(sh0, chest, 0.55), r_u * 0.95, r_u * 0.8, top, edge=False)
        mus = 1.0 - 0.75 * loose
        b.blob(sh0, e, r_u, r_u * (0.68 + 0.2 * loose), up_col, bulge=(1.0 if fem else 2.4 * k) * mus)
        fcol = (far(sleeve, amt) if isfar else sleeve) if long_sleeve else sk
        b.blob(e, h, r_f + (0.6 if long_sleeve else 0), r_f * (0.72 + 0.12 * loose) + 0.4, fcol,
               bulge=(0.8 if fem else 1.5 * k) * mus)
        if L.get("cuff") and long_sleeve:
            cc = far(L["cuff"], amt) if isfar else L["cuff"]
            b.blob(lerp(e, h, 0.82), lerp(e, h, 0.95), r_f * 0.8 + 0.6, r_f * 0.8 + 0.6, cc, lit=False)
        d = dirv(ang + elb)
        fist = (h[0] + d[0] * 3.5, h[1] + d[1] * 3.5)
        fc = far(L.get("glove", skin), amt) if isfar else L.get("glove", skin)
        b.blob(h, fist, (3.4 if fem else 4.2), (3.2 if fem else 4.0), fc)
        b.flush()
        hand_detail(s, h, fist, d, fc)
        if long_sleeve and loose:       # pano folgado: dobras na manga (mais perto do punho)
            fabric_folds(s, sh0, e, r_u, up_col, (0.45, 0.75))
            fabric_folds(s, e, h, r_f + 0.6, fcol, (0.35, 0.6, 0.78))
        if L.get("stripe"):             # duas listras brancas da manga, do ombro ao punho
            stripe_line(s, [sh0, e, lerp(e, h, 0.8)], [r_u * 0.5, r_f * 0.5], "up",
                        far(L["stripe"], 0.8) if isfar else L["stripe"])
        if sleeve and not long_sleeve and not isfar:      # barra da manga curta
            q0, q1 = lerp(sh0, e, 0.84), lerp(sh0, e, 0.95)
            nn = (-(e[1] - sh0[1]), e[0] - sh0[0])
            ln = math.hypot(*nn) or 1
            nn = (nn[0] / ln * r_u * 0.72, nn[1] / ln * r_u * 0.72)
            D.line(s, sh(up_col, -60), (q0[0] + nn[0], q0[1] + nn[1]), (q0[0] - nn[0], q0[1] - nn[1]), 0.5)
            D.line(s, sh(up_col, 26), (q1[0] + nn[0] * 0.9, q1[1] + nn[1] * 0.9), (q1[0] - nn[0] * 0.9, q1[1] - nn[1] * 0.9), 0.5)
        if long_sleeve and not isfar:                     # dobras da manga no cotovelo
            for t0, w0 in ((0.12, 0.55), (0.24, 0.4)):
                q = lerp(e, h, t0)
                D.line(s, sh(up_col, -40), (q[0] - d[1] * r_f * w0, q[1] + d[0] * r_f * w0),
                       (q[0] - d[1] * r_f * w0 * 0.2 + d[0], q[1] + d[0] * r_f * w0 * 0.2 + d[1]), 0.5)
        if L.get("watch") and not isfar:
            q = lerp(e, h, 0.86)
            D.circle(s, (24, 24, 30), q, 2.0)
            px(s, q[0] - 0.5, q[1] - 0.5, (90, 220, 200), 1, 1)
        P[tag + "_hand"] = (fist[0] + d[0] * 2.5, fist[1] + d[1] * 2.5)
        P[tag + "_elbow"] = e
        P[tag + "_shoulder"] = sh0
        P[tag + "_hand_dir"] = ang + elb

    def leg(hp, spec, isfar, tag):
        ang, knee = spec[:2]
        foot = spec[2] if len(spec) > 2 else 0
        b.begin()
        st = F.get("lstretch", 1.0) if tag == "far" else 1.0
        kn = pt(hp, ang, thigh * st)
        an = pt(kn, ang + knee, shin * st)
        pc = far(L["pants"]) if isfar else L["pants"]
        rt = (7.0, 5.0) if fem else (7.8 * k + 0.6, 5.6 * k + 0.4)
        loose = L.get("loose", 0.0)
        if loose:
            rt = (rt[0] + 0.8 * loose, rt[1] + 1.4 * loose)
        if not isfar:
            # quadril da calça: liga as duas coxas e fica por baixo da barra da camisa
            b.blob((hp_f[0], hp_f[1] - 2), (hp_n[0], hp_n[1] - 2), waist_r, waist_r, pc, edge=False)
        mus = 1.0 - 0.75 * loose
        b.blob(hp, kn, rt[0], rt[1], pc, bulge=(1.4 if fem else 1.8 * k) * mus)
        hem = L.get("hem_leg")              # barra: "solta" (amontoa no sapato) ou "punho" (elástico)
        b.blob(kn, an, rt[1] + 0.4, 3.6 + (2.6 if hem == "solta" else 1.0 if hem else 0.0), pc)
        b.blob(kn, lerp(kn, an, 0.55), rt[1] + 0.2, rt[1] - 0.6, pc, bulge=(1.2 if fem else 1.8 * k) * mus, edge=False)
        if hem == "solta":
            b.blob(lerp(kn, an, 0.7), lerp(kn, an, 0.93), 4.8, 5.2, pc, edge=False)
        elif hem == "punho":
            b.blob(lerp(kn, an, 0.86), pt(an, ang + knee, 0.5), 4.4, 4.4, sh(pc, -10), lit=False)
        # pé: a ponta aponta para a FRENTE da canela; foot > 0 estica a ponta
        toe_dir = ang + knee + 90 - foot
        toe = pt(an, toe_dir, 9)
        bc = far(L["boots"]) if isfar else L["boots"]
        b.blob(pt(an, toe_dir, -1.5), toe, 4.2, 2.8, bc)
        b.flush()
        if not isfar and sum(pc) < 200:    # calça escura: costura com brilho na frente da coxa
            nv = dirv(ang + 90)
            a0, a1 = lerp(hp, kn, 0.15), lerp(hp, kn, 0.85)
            off = rt[0] * 0.55
            D.line(s, sh(pc, 46), (a0[0] + nv[0] * off, a0[1] + nv[1] * off), (a1[0] + nv[0] * rt[1] * 0.6, a1[1] + nv[1] * rt[1] * 0.6), 0.5)
            b0, b1 = lerp(kn, an, 0.15), lerp(kn, an, 0.8)
            D.line(s, sh(pc, 34), (b0[0] + nv[0] * rt[1] * 0.55, b0[1] + nv[1] * rt[1] * 0.55), (b1[0] + nv[0] * 2.4, b1[1] + nv[1] * 2.4), 0.5)
        if not isfar:                       # vinco atrás do joelho e barra da calça
            tn = (-(kn[1] - hp[1]), kn[0] - hp[0])
            ln = math.hypot(*tn) or 1
            tn = (tn[0] / ln, tn[1] / ln)
            if tn[0] * dirv(ang + knee)[0] + tn[1] * dirv(ang + knee)[1] > 0:
                tn = (-tn[0], -tn[1])
            for t0, w0 in ((0.82, 3.6), (0.92, 2.6)):
                q = lerp(hp, kn, t0)
                D.line(s, sh(pc, -46), (q[0] + tn[0] * rt[1] * 0.9, q[1] + tn[1] * rt[1] * 0.9),
                       (q[0] + tn[0] * (rt[1] * 0.9 - w0), q[1] + tn[1] * (rt[1] * 0.9 - w0)), 0.5)
            if hem != "solta":
                q = lerp(kn, an, 0.86)
                sd = dirv(ang + knee)
                D.line(s, sh(pc, -55), (q[0] - sd[1] * 3.9, q[1] + sd[0] * 3.9), (q[0] + sd[1] * 3.9, q[1] - sd[0] * 3.9),
                       0.5)
        if L.get("stripes"):
            sc = L["stripes"]
            for i in (0.3, 0.55):
                q = lerp(an, toe, i)
                D.line(s, sc, (q[0] - 0.8, q[1] - 1.8), (q[0] + 0.8, q[1] + 0.6), 0.5)
            D.line(s, sh(bc, -40), pt(an, toe_dir + 90, 2.6), pt(toe, toe_dir + 90, 2.0), 0.5)
        if loose:                            # pano folgado: dobras na coxa e amontoado no tornozelo
            fabric_folds(s, hp, kn, rt[0], pc, (0.3, 0.85))
            fabric_folds(s, kn, an, rt[1], pc, (0.25, 0.62, 0.8) if hem == "solta" else (0.3, 0.7))
        if L.get("cargo") and not isfar:     # bolso de lado da calça cargo, com aba
            cargo_pocket(s, hp, kn, rt, pc)
        if L.get("stripe"):
            stripe_line(s, [lerp(hp, kn, 0.05), kn, lerp(kn, an, 0.85)], [rt[0] * 0.35, rt[1] * 0.35], "front",
                        far(L["stripe"], 0.8) if isfar else L["stripe"])
        P[tag + "_foot"] = toe
        P[tag + "_knee"] = kn
        P[tag + "_ankle"] = an

    hc = pt(neck, 180 - lean * 0.6 - F.get("head", 0), 10 + L.get("neck", 0))
    top = L.get("shirt") or skin
    chest_r = (8.5 if fem else 12.0 * k + 1.2) + abs(sp) * (1.0 if fem else 2.0) + L.get("chest", 0)
    waist_r = (6.2 if fem else 8.6 * k + 1.0) + L.get("belly", 0) * 0.6
    if turn >= 0:
        arm(sh_f, F["fa"], True, "far")
        leg(hp_f, F["fl"], True, "far")
    else:
        leg(hp_f, F["fl"], True, "far")
        arm(sh_f, F["fa"], True, "far")
    # a perna da frente vem antes do tronco: a camisa cobre o encaixe da coxa
    leg(hp_n, F["nl"], False, "near")
    if L.get("tabard"):
        tabard(s, b, L, P, hp_n, hp_f, far)

    # ── tronco ──
    def at0(t, f):
        q = pt(hip, upA, t)
        return (q[0] + fwd[0] * f, q[1] + fwd[1] * f)

    b.begin()
    b.blob(pt(hip, upA, 4), pt(hip, upA, 15), waist_r, waist_r + 0.6, top)
    b.blob(pt(hip, upA, 18), pt(hip, upA, 29), chest_r - 1, chest_r, top, bulge=1.0)
    shr = (5.6 if fem else 7.0 * k) + L.get("chest", 0) * 0.5
    b.blob((sh_f[0], sh_f[1] - 1), (sh_n[0], sh_n[1] - 1), shr, shr, top)
    if L.get("belly"):                  # barriga e peito cheios: o tronco fica um barril, sem cintura
        bl_ = L["belly"]
        b.blob(at0(7, bl_ * 0.5), at0(19, bl_ * 0.3), waist_r + bl_ * 0.4, chest_r - 0.5, top, bulge=bl_ * 0.4)
    if L.get("back"):                   # costas largas atrás dos ombros
        b.blob(at0(22, -4 - L["back"]), at0(30, -3 - L["back"]), chest_r * 0.75, chest_r * 0.7, top)
    b.blob(pt(hip, upA, 30), pt(neck, upA, 4), 3.6 if fem else 5.2 * k + 1, 3.2 if fem else 4.6, skin)
    if L.get("collar"):                 # gola alta da jaqueta fechada
        b.blob(pt(neck, upA, -3), pt(neck, upA, 2.5), 5.4 * k + 0.8, 4.8 * k + 0.8, top)
    if L.get("band"):                   # barra elástica larga da blusa
        b.blob(at0(1.0, -1), at0(4, -1), waist_r - 0.4, waist_r + 0.2, L["band"])
    b.flush()
    if L.get("hood"):                   # capuz amontoado atrás do pescoço
        b.begin()
        back = (-fwd[0], -fwd[1])
        h0 = (neck[0] + back[0] * 4.5, neck[1] + back[1] * 4.5 + 1)
        b.blob(h0, (h0[0] + back[0] * 2.5, h0[1] + 6), 5.6, 4.6, top)
        b.blob((neck[0] + back[0] * 2.5, neck[1] + 1.5), (neck[0] + fwd[0] * 3.0, neck[1] + 3.0), 4.4, 3.6, sh(top, -8),
               edge=False)
        b.flush()
        D.arc(s, sh(top, -60), (h0[0] - 4, h0[1] - 2, 8, 9), math.pi * 0.6, math.pi * 1.4, 0.5)

    def at(t, f):
        q = pt(hip, upA, t)
        return (q[0] + fwd[0] * f, q[1] + fwd[1] * f)

    front = 6 * (1 - max(0, turn)) if turn >= -0.2 else None
    if L.get("shirt"):
        tc = L["shirt"]
        dk2, li2 = sh(tc, -55), sh(tc, 35)
        if front is not None:
            c0 = front
            tee = L.get("tee")
            if L.get("collar"):    # jaqueta fechada: zíper no meio e a gola
                D.line(s, L.get("zip", li2), at(33, c0 + 1), at(3, c0), 0.5)
                D.line(s, dk2, at(33, c0 + 1.6), at(3, c0 + 0.6), 0.5)
                px(s, *at(31, c0 + 1.5), (230, 230, 236), 1, 1.5)
                for tt in (12, 7):     # bolsos
                    D.line(s, dk2, at(tt, c0 - 8), at(tt + 2, c0 - 4), 0.5)
                D.line(s, li2, at(33.5, c0 - 4), at(33, c0 + 2), 0.5)
            elif tee:            # jaqueta aberta: a camiseta aparece no meio
                wd = 2.5 + 3.5 * max(0.0, turn)
                D.polygon(s, tee, [at(30, c0 - wd), at(30, c0 + wd), at(3, c0 + wd + 0.5), at(3, c0 - wd - 0.5)])
                D.line(s, sh(tee, -30), at(30, c0 - wd), at(30, c0 + wd), 1)
                D.line(s, sh(tee, 22), at(28, c0 - wd + 0.5), at(5, c0 - wd + 0.5), 0.5)
                D.line(s, L.get("zip", li2), at(30, c0 - wd - 0.5), at(3, c0 - wd - 0.5), 0.5)
                D.line(s, dk2, at(30, c0 + wd + 0.5), at(3, c0 + wd + 0.5), 0.5)
                for tt in (12, 7):     # bolsos
                    D.line(s, dk2, at(tt, c0 - wd - 6), at(tt, c0 - wd - 3), 0.5)
                # gola da jaqueta dobrada para fora e barra elástica na cintura
                for side in (-1, 1):
                    e0 = c0 + side * (wd + 0.5)
                    lap = [at(32.5, e0 + side * 0.5), at(33.5, e0 + side * 4.5), at(26, e0 + side * 3), at(27, e0)]
                    D.polygon(s, sh(tc, -18), lap)
                    D.line(s, li2, lap[0], lap[1], 0.5)
                    D.line(s, dk2, lap[1], lap[2], 0.5)
                D.line(s, dk2, at(4.5, c0 - wd - 9), at(4.5, c0 - wd - 0.5), 0.5)
                D.line(s, dk2, at(4.5, c0 + wd + 0.5), at(4.5, c0 + wd + 6), 0.5)
            elif L.get("hood"):    # blusa de capuz: gola redonda, cordão e dobras do tecido fofo
                D.lines(s, dk2, False, [at(31, c0 - 3.5), at(29.5, c0), at(31, c0 + 3.5)], 0.5)
                for f in (-1.2, 1.2):
                    D.line(s, (244, 236, 230), at(29.5, c0 + f), at(24 - abs(f), c0 + f * 1.4), 0.5)
                for tt, f, ln in ((22, c0 - 6, 5), (16, c0 + 1, 6), (11, c0 - 4, 5), (19, c0 + 5, 3)):
                    D.lines(s, dk2, False, [at(tt, f - ln * 0.5), at(tt - 1.2, f), at(tt - 0.4, f + ln * 0.5)], 0.5)
                    D.line(s, li2, at(tt + 1, f - ln * 0.4), at(tt + 0.4, f), 0.5)
            else:
                D.polygon(s, skin, [at(31, c0 - 3), at(31, c0 + 3), at(27, c0 + 0.5)])
                D.lines(s, dk2, False, [at(31, c0 - 3.5), at(26.5, c0 + 0.5), at(31, c0 + 3.5)], 0.5)
                for tt, f in ((20, c0 - 3), (14, c0 + 2), (9, c0 - 1)):
                    D.line(s, dk2, at(tt, f - 3), at(tt - 3, f + 3), 0.5)
            if L.get("print"):     # estampa azul da camisa
                pc = L["print"]
                q = at(21, c0 + 2)
                D.polygon(s, pc, [(q[0] - 3, q[1] - 2), (q[0] + 2, q[1] - 3), (q[0] + 4, q[1] + 1), (q[0] - 1, q[1] + 3)])
                D.circle(s, sh(pc, 50), (q[0] + 0.5, q[1] - 0.5), 1.2)
                q = at(13, c0 - 2)
                D.rect(s, pc, (q[0] - 1.5, q[1] - 1, 3, 2))
        else:
            D.line(s, dk2, at(28, -6 * (1 + turn)), at(6, -6 * (1 + turn)), 0.5)
            for f in (-6 * (1 + turn) - 4, -6 * (1 + turn) + 4):
                q = at(25, f)
                D.arc(s, dk2, (q[0] - 4, q[1] - 3, 8, 7), math.pi * 0.1, math.pi * 0.9, 0.5)
    # barra da camisa e cinto
    if not L.get("band"):
        bl = L["belt"]
        q0, q1 = at(1.5, -9), at(1.5, 10)
        D.line(s, sh(bl, -60), (q0[0], q0[1] + 1), (q1[0], q1[1] + 1), 2)
        D.line(s, bl, q0, q1, 1.5)
        if front is not None:
            q = at(1.5, front + 1)
            D.rect(s, L.get("buckle", sh(bl, 80)), (q[0] - 1.5, q[1] - 1.5, 3, 3))

    # ── cabeça ──
    hx, hy = hc
    b.begin()
    b.blob(pt(neck, upA, -2), hc, 3.4 if fem else 4.6 * k + 1, 3.2 if fem else 4.4 * k + 1, skin, lit=False)
    b.flush()
    D.ellipse(s, sh(skin, -95), (hx - 8, hy - 9, 17, 18))
    D.ellipse(s, sh(skin, -50), (hx - 7, hy - 8, 15, 16))
    D.ellipse(s, skin, (hx - 6, hy - 8, 13, 14))
    face = turn > -0.55
    if face:
        draw_face(s, hc, L, F)
    L["head"](s, b, hc, L, face, F)
    P["head"] = hc

    arm(sh_n, F["na"], False, "near")
    details(s, P, L)
    return outline(surface), P


def stripe_line(s, pts, radii, side, col):
    """Duas listras paralelas ao longo do braço ou da perna (agasalho de treino). Ficam do lado de
    fora da dobra (cotovelo/joelho), então as duas partes se encontram certinho na junta."""
    a, m, z = pts
    for gap in (0.0, 1.3):
        path = []
        for i, (p0, p1, other) in enumerate(((a, m, z), (m, z, a))):
            ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
            n = (-(p1[1] - p0[1]) / ln, (p1[0] - p0[0]) / ln)
            bend = (other[0] - p0[0]) * n[0] + (other[1] - p0[1]) * n[1]
            if abs(bend) > 2.0:
                if bend > 0:
                    n = (-n[0], -n[1])
            elif side == "up" and n[1] > 0 or side == "front" and n[0] < 0:
                n = (-n[0], -n[1])
            r = radii[i] + gap
            path.append(((p0[0] + n[0] * r, p0[1] + n[1] * r), (p1[0] + n[0] * r, p1[1] + n[1] * r)))
        (a0, a1), (b0, b1) = path
        D.line(s, col, a0, a1, 0.5)
        D.line(s, col, b0, b1, 0.5)
        D.line(s, col, a1, b0, 0.5)


def fabric_folds(s, a, b, r, col, ts):
    """Dobras do pano: risquinhos curvos atravessando a manga ou a perna, com luz em cima."""
    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    u = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
    n = (-u[1], u[0])
    dark, light = sh(col, -42), sh(col, 26)
    for i, t in enumerate(ts):
        c = lerp(a, b, t)
        w = r * (0.75 if i % 2 else 0.95)
        side = 1 if i % 2 else -1
        p0 = (c[0] + n[0] * w * side, c[1] + n[1] * w * side)
        p1 = (c[0] + u[0] * 1.6 + n[0] * w * 0.1 * side, c[1] + u[1] * 1.6 + n[1] * w * 0.1 * side)
        p2 = (c[0] - n[0] * w * 0.35 * side + u[0] * 0.6, c[1] - n[1] * w * 0.35 * side + u[1] * 0.6)
        D.lines(s, dark, False, [p0, p1, p2], 0.5)
        D.line(s, light, (p0[0] - u[0] * 0.8, p0[1] - u[1] * 0.8), (p1[0] - u[0] * 0.8, p1[1] - u[1] * 0.8), 0.5)


def cargo_pocket(s, hp, kn, rt, pc):
    """Bolso grande na lateral da coxa (calça cargo), com aba e costura."""
    ln = math.hypot(kn[0] - hp[0], kn[1] - hp[1]) or 1
    u = ((kn[0] - hp[0]) / ln, (kn[1] - hp[1]) / ln)
    n = (-u[1], u[0])
    c = lerp(hp, kn, 0.62)
    hl, hw = 4.6, rt[1] * 0.62

    def q(a, b):
        return (c[0] + u[0] * a + n[0] * b, c[1] + u[1] * a + n[1] * b)

    body = [q(-hl, -hw), q(-hl, hw), q(hl, hw * 0.9), q(hl, -hw * 0.9)]
    D.polygon(s, sh(pc, -14), body)
    D.lines(s, sh(pc, -60), True, body, 0.5)
    flap = [q(-hl - 0.5, -hw - 0.4), q(-hl - 0.5, hw + 0.4), q(-hl + 2.4, hw + 0.2), q(-hl + 2.4, -hw - 0.2)]
    D.polygon(s, sh(pc, -6), flap)
    D.lines(s, sh(pc, -64), True, flap, 0.5)
    D.line(s, sh(pc, 30), q(-hl - 0.2, -hw), q(-hl - 0.2, hw), 0.5)
    px(s, *q(-hl + 1.2, 0), sh(pc, -80), 1, 1)


def hand_detail(s, wrist, fist, d, col):
    """Punho fechado: dedos dobrados na frente (com os vãos), nós dos dedos e o polegar por cima."""
    perp = (-d[1], d[0])
    if perp[1] > 0 or perp[1] == 0 and perp[0] < 0:     # o polegar fica do lado de cima
        perp = (-perp[0], -perp[1])
    dark, light = sh(col, -62), sh(col, 30)
    # vãos entre os dedos (na frente do punho)
    for o in (-1.6, 0.0, 1.6):
        a = (fist[0] + d[0] * 3.6 + perp[0] * o, fist[1] + d[1] * 3.6 + perp[1] * o)
        b = (fist[0] + d[0] * 1.2 + perp[0] * o * 0.9, fist[1] + d[1] * 1.2 + perp[1] * o * 0.9)
        D.line(s, dark, a, b, 0.5)
    # nós dos dedos com brilho
    for o in (-2.4, -0.8, 0.8, 2.4):
        q = (fist[0] + d[0] * 2.6 + perp[0] * o, fist[1] + d[1] * 2.6 + perp[1] * o)
        if o > -2.4:
            px(s, q[0], q[1] - 0.3, light)
    # polegar dobrado por cima dos dedos
    t0 = (fist[0] - d[0] * 0.8 + perp[0] * 2.6, fist[1] - d[1] * 0.8 + perp[1] * 2.6)
    t1 = (fist[0] + d[0] * 2.4 + perp[0] * 1.2, fist[1] + d[1] * 2.4 + perp[1] * 1.2)
    D.line(s, dark, (t0[0] - perp[0] * 1.1, t0[1] - perp[1] * 1.1), (t1[0] - perp[0] * 1.1, t1[1] - perp[1] * 1.1), 0.5)
    D.line(s, light, t0, lerp(t0, t1, 0.7), 0.5)
    # punho (pulso) marcado
    D.line(s, dark, (wrist[0] + perp[0] * 2.6, wrist[1] + perp[1] * 2.6),
           (wrist[0] + perp[0] * 1.4 + d[0], wrist[1] + perp[1] * 1.4 + d[1]), 0.5)


def tabard(s, b, L, P, hp_n, hp_f, far):
    tc = L["tabard"]
    ln = L.get("tabard_len", 0.8)
    b.begin()
    for tag, hp, isfar in (("far", hp_f, True), ("near", hp_n, False)):
        end = lerp(hp, P[tag + "_knee"], ln + 0.25)
        b.blob(hp, end, 8.0, 7.0, far(tc) if isfar else tc)
    b.flush()


def draw_face(s, hc, L, F):
    hx, hy = hc
    skin = L["skin"]
    sd, sdd, sl = sh(skin, -38), sh(skin, -80), sh(skin, 26)
    hurt = F.get("hurt", False)
    jaw = [(hx - 3.5, hy + 2), (hx + 7, hy + 1.5), (hx + 7, hy + 5), (hx + 5.5, hy + 8), (hx, hy + 8.5), (hx - 3, hy + 6.5)]
    if L.get("young"):
        jaw = [(hx - 3, hy + 2), (hx + 6.8, hy + 1.5), (hx + 6.8, hy + 4.5), (hx + 5, hy + 7.5), (hx, hy + 8), (hx - 2.5, hy + 6)]
    D.polygon(s, sh(skin, -110), [(x + 0.5, y + 0.5) for x, y in jaw])
    D.polygon(s, skin, jaw)
    D.line(s, sd, (hx - 2, hy + 5.5), (hx + 3.5, hy + 8), 0.5)
    D.ellipse(s, sl, (hx - 2.5, hy - 7, 6.5, 3))
    D.ellipse(s, sl, (hx + 1.5, hy - 0.5, 4, 1.8))
    D.polygon(s, skin, [(hx + 6, hy - 3), (hx + 8.5, hy + 0.8), (hx + 6.5, hy + 1.5)])
    px(s, hx + 8, hy + 0.5, sl)
    px(s, hx + 6.5, hy + 1.5, sd, 1.5)
    px(s, hx + 7, hy + 1, sdd)
    D.line(s, sd, (hx + 2, hy - 3.6), (hx + 6.5, hy - 3.6), 0.5)
    if hurt:
        D.line(s, sdd, (hx + 3, hy - 2.2), (hx + 6, hy - 2.6), 0.5)
        D.line(s, sdd, (hx + 3.3, hy - 1.6), (hx + 5.8, hy - 1.8), 0.5)
    else:
        D.ellipse(s, (244, 240, 236), (hx + 3, hy - 3, 3.2, 1.8))
        D.rect(s, L.get("iris", (60, 40, 30)), (hx + 4.4, hy - 3, 1.4, 1.8))
        px(s, hx + 5, hy - 2.4, (16, 12, 20))
        px(s, hx + 4.5, hy - 3, (255, 255, 255))
        D.line(s, (30, 20, 26), (hx + 2.8, hy - 3.2), (hx + 6.4, hy - 3.2), 0.5)
    brow = sh(L["hair"], -30)
    D.line(s, brow, (hx + 2.4, hy - 4.6 + (0.8 if hurt else 0)), (hx + 6.6, hy - 4.2 - (0.4 if hurt else 0)), 1)
    if hurt:
        D.ellipse(s, (70, 20, 30), (hx + 3.8, hy + 3.6, 2.6, 2))
        px(s, hx + 4.2, hy + 3.6, (240, 236, 230), 1.6)
    elif F.get("smile"):
        D.lines(s, sdd, False, [(hx + 3.5, hy + 4), (hx + 5, hy + 4.8), (hx + 6.6, hy + 3.8)], 0.5)
        px(s, hx + 4.5, hy + 4.2, (250, 250, 246), 1.5)
    else:
        D.line(s, sdd, (hx + 4, hy + 4.6), (hx + 6.4, hy + 4.4), 0.5)
    D.ellipse(s, sd, (hx - 4.2, hy - 2.2, 3.6, 5))
    D.ellipse(s, sdd, (hx - 3.4, hy - 1, 1.6, 2.8))
    px(s, hx - 4, hy - 2, sl)


def glasses(s, hc, frame, lens, lens_l):
    """Óculos de perfil: a lente na frente do olho e a haste até a orelha."""
    hx, hy = hc
    D.rect(s, sh(frame, -40), (hx + 2.2, hy - 4.2, 5.4, 3.6))
    D.rect(s, lens, (hx + 2.7, hy - 3.7, 4.4, 2.6))
    px(s, hx + 3.2, hy - 3.5, lens_l, 1.2, 0.5)
    px(s, hx + 6.2, hy - 2.0, lens_l, 0.5, 0.5)
    D.line(s, frame, (hx + 2.2, hy - 3.6), (hx - 2.8, hy - 2.6), 0.5)
    D.line(s, frame, (hx + 2.2, hy - 4.2), (hx + 7.6, hy - 4.2), 0.5)


def _strands(s, pts_list, light, dark):
    for i, pts in enumerate(pts_list):
        D.lines(s, light if i % 2 == 0 else dark, False, pts, 0.5)


def aryel_head(s, b, hc, L, face, F):
    """Cabelo castanho bagunçado, franja jogada de lado e óculos."""
    hx, hy = hc
    hair = L["hair"]
    hl, hd = sh(hair, 40), sh(hair, -34)
    sway = F.get("hair", 0) * 0.05
    b.begin()
    b.blob((hx - 5, hy - 6), (hx - 7.5, hy + 4), 4.2 if face else 7.2, 3.4 if face else 6.2, hair)
    b.blob((hx - 5, hy - 8.5), (hx + 3.5, hy - 9), 4.2, 3.4, hair)
    b.blob((hx + 1, hy - 9.5), (hx + 6.5, hy - 6.5), 2.8, 2.0, hair, edge=False)
    b.flush()
    # tufos espetados para cima e para trás
    for x0, y0, x1, y1 in ((-7, -9, -10.5 - sway, -11.5), (-3.5, -11, -4.5, -14), (0, -11.5, 1.5, -14), (3, -11, 5.5, -12.5),
                           (-8.5, -5, -11.5 - sway, -5.5), (-8, -1, -10.5 - sway, 1)):
        D.polygon(s, hair, [(hx + x0 - 1.5, hy + y0 + 1), (hx + x1, hy + y1), (hx + x0 + 2, hy + y0 + 1.5)])
        D.line(s, hd, (hx + x0 + 1, hy + y0 + 1.5), (hx + x1 + 0.5, hy + y1 + 0.5), 0.5)
    _strands(s, [[(hx - 5, hy - 10), (hx - 7.5, hy - 4), (hx - 7.5, hy + 2)],
                 [(hx - 2, hy - 11), (hx - 5, hy - 6), (hx - 6, hy)],
                 [(hx + 1, hy - 10.5), (hx - 2, hy - 7)]], hl, hd)
    if face:
        # franja caindo de lado na testa
        D.polygon(s, hair, [(hx - 1, hy - 10), (hx + 7.5, hy - 8.5), (hx + 7, hy - 5), (hx + 4.5, hy - 6.5), (hx + 2, hy - 5)])
        D.line(s, hd, (hx + 2, hy - 8.5), (hx + 6.5, hy - 5.5), 0.5)
        D.line(s, hl, (hx, hy - 9.5), (hx + 5, hy - 8.2), 0.5)
        D.polygon(s, hair, [(hx - 2.5, hy - 3), (hx - 1, hy - 3), (hx - 1.5, hy + 3), (hx - 2.8, hy + 2)])  # costeleta
        glasses(s, hc, L["frame"], L["lens"], L["lens_l"])


def cauanzera_head(s, b, hc, L, face, F):
    """Cachos em cima, degradê nos lados e óculos de armação clara."""
    hx, hy = hc
    hair = L["hair"]
    hl, hd = sh(hair, 46), sh(hair, -10)
    fade = mix(L["skin"], hair, 0.55)
    # degradê: a lateral raspada fica da cor da pele misturada com o cabelo
    D.ellipse(s, fade, (hx - 7.5, hy - 7.5, 6.5, 6))
    D.polygon(s, fade, [(hx - 5, hy - 7.5), (hx + 1, hy - 7.5), (hx - 1.5, hy - 4.5), (hx - 4.5, hy - 2.5)])
    for i in range(8):
        px(s, hx - 6.8 + (i % 4) * 1.6, hy - 6.8 + (i // 4) * 2.0, sh(fade, -25))
    b.begin()
    b.blob((hx - 6, hy - 8), (hx + 4, hy - 9.5), 5.0, 4.4, hair)
    if not face:
        b.blob((hx - 6, hy - 6), (hx - 7, hy + 4), 6.8, 6.0, hair)
    b.flush()
    # cachos: bolinhas com brilho
    for i, (dx, dy) in enumerate(((-8, -11), (-5, -13), (-2, -14), (1, -14), (4, -13), (6.5, -11), (-9, -8), (-6.5, -9.5),
                                  (-3, -11), (0.5, -11.5), (3.5, -10.5), (6, -8.5))):
        r = 2.2 if i < 6 else 1.9
        D.circle(s, sh(hair, -20), (hx + dx + 0.3, hy + dy + 0.4), r + 0.3)
        D.circle(s, hair, (hx + dx, hy + dy), r)
        px(s, hx + dx - 0.6, hy + dy - 0.9, hl, 1, 0.5)
        if i % 3 == 0:
            px(s, hx + dx + 0.6, hy + dy + 0.5, hd)
    if face:
        glasses(s, hc, L["frame"], L["lens"], L["lens_l"])


def details(s, P, L):
    skin = L["skin"]
    sl = sh(skin, 30)
    e, h = P["near_elbow"], P["near_hand"]
    if not L.get("long_sleeve"):
        D.lines(s, sl, False, [lerp(e, h, 0.15), lerp(e, h, 0.4), lerp(e, h, 0.65)], 0.5)
    for tag in ("near", "far"):
        fx, fy = P[tag + "_foot"]
        px(s, fx - 2, fy - 1.5, sh(L["boots"], 50), 1.5)


# ── visual de cada lutador (as cores vêm dos bonecos do jogo) ─────────
LOOKS = {
    # Aryel: cabelo castanho bagunçado, óculos, blusa de capuz rosa fofa, calça cargo bege e o
    # menor da turma (baixinho e de moto)
    "aryel": dict(build=0.92, size=0.93, young=True, skin=(238, 190, 150), hair=(112, 68, 42),
                  shirt=(234, 142, 172), sleeve=(234, 142, 172), long_sleeve=True, cuff=(212, 118, 150),
                  hood=True, band=(214, 122, 152), loose=1.0, arm=0.88, chest=1.0, shoulders=1.05, neck=-1.5,
                  pants=(220, 204, 164), cargo=True, hem_leg="solta", boots=(118, 72, 42), belt=(96, 62, 40),
                  buckle=(214, 200, 160), frame=(40, 34, 44), lens=(176, 206, 228), lens_l=(236, 246, 255),
                  iris=(80, 52, 32), head=aryel_head),
    # Cauanzera: o mais alto, cachos com degradê, óculos escuros, agasalho preto fechado com duas
    # listras brancas nas mangas e nas pernas, tênis branco e relógio no pulso
    "cauanzera": dict(build=1.0, size=1.07, skin=(196, 142, 104), hair=(30, 26, 30),
                      shirt=(42, 42, 50), sleeve=(42, 42, 50), long_sleeve=True, cuff=(28, 28, 36),
                      collar=True, zip=(150, 150, 160), stripe=(226, 226, 232), loose=0.8, hem_leg="punho",
                      arm=0.9, chest=3.0, back=3.0, belly=3.0, shoulders=1.15, neck=-2, torso=1.03,
                      pants=(36, 36, 44), boots=(240, 240, 236), stripes=(40, 40, 48), belt=(52, 46, 50),
                      buckle=(176, 178, 188), watch=True,
                      frame=(22, 22, 28), lens=(40, 46, 60), lens_l=(120, 170, 220), iris=(50, 34, 24),
                      head=cauanzera_head),
}
