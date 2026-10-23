"""Informações na tela durante a partida."""
import math

import pygame

from . import config, theme
from .ui import mix


def _hp_color(ratio):
    return theme.MOSS if ratio > 0.5 else theme.BRASS if ratio > 0.25 else theme.BLOOD


def ammo_text(f):
    """Munição da arma na mão, para o HUD: ("4/6", cor), ("RECARGA", cor)... ou None."""
    mag = f.mag
    if not mag or f.weapon.is_melee:
        return None
    if f.reloading:
        return "RECARGA", theme.BRASS
    if f.ammo <= 0:
        return "VAZIO", theme.BLOOD
    return f"{f.ammo}/{mag}", theme.BRASS if f.ammo > mag else theme.BONE


def _weapon_label(screen, ui, f, pos, right):
    """Nome da arma e, ao lado, a munição (alinhado à direita ou à esquerda)."""
    anchor = "midright" if right else "midleft"
    rect = ui.text(screen, f.weapon.name.upper(), theme.XS, theme.MUTED, pos, anchor=anchor, shadow=True)
    ammo = ammo_text(f)
    if ammo:
        text, color = ammo
        x = rect.left - 8 if right else rect.right + 8
        ui.text(screen, text, theme.XS, color, (x, rect.centery), anchor=anchor, shadow=True)


def _fighter_block(screen, ui, f, right, frame, wins=0):
    W = config.SCREEN_W
    bar_w = 300
    x = W - 16 - bar_w if right else 16
    y = 14
    anchor = "topright" if right else "topleft"
    edge = x + bar_w if right else x

    # etiqueta + nome
    tag = ui.assets.text(f.label, theme.XS, theme.INK)
    tag_rect = pygame.Rect(0, 0, tag.get_width() + 10, 14)
    setattr(tag_rect, anchor, (edge, y))
    screen.fill(theme.SHADOW, tag_rect.move(2, 2))
    screen.fill(f.color, tag_rect)
    screen.blit(tag, tag.get_rect(center=tag_rect.center))
    name_pos = (tag_rect.left - 8, y + 7) if right else (tag_rect.right + 8, y + 7)
    ui.text(screen, f.stats.name.upper(), theme.XS, theme.BONE, name_pos,
            anchor="midright" if right else "midleft")

    # rounds vencidos
    for k in range(config.ROUNDS_TO_WIN):
        px = x + 4 + k * 16 if right else x + bar_w - 14 - k * 16
        pip = pygame.Rect(px, y + 2, 10, 10)
        screen.fill(theme.SHADOW, pip.move(1, 1))
        screen.fill(theme.BRASS if k < wins else theme.INK, pip)
        pygame.draw.rect(screen, theme.LINE_HI, pip, 1)

    # vida
    ratio = f.hp / f.max_hp
    low = ratio <= 0.25 and (frame // 10) % 2 == 0
    color = _hp_color(ratio) if not low else mix(theme.BLOOD, theme.BONE, 0.4)
    ui.bar(screen, (x, y + 20, bar_w, 16), ratio, color, back=(30, 22, 30), ticks=10, flip=right)
    hp_txt = f"{f.hp}/{f.max_hp}"
    ui.text(screen, hp_txt, theme.XS, theme.MUTED, (x + bar_w if right else x, y + 44),
            anchor="topright" if right else "topleft", shadow=True)

    # habilidade e arma
    ab_w = 110
    ab_x = x if right else x + bar_w - ab_w
    ready = f.ability_ready
    ab_color = theme.BRASS if ready else theme.SKY
    ui.bar(screen, (ab_x, y + 44, ab_w, 8), f.ability_ratio, ab_color, back=(22, 20, 32), flip=right)
    label = f.ability.name.upper() + (" OK" if ready else "")
    pos = (ab_x + ab_w if not right else ab_x, y + 60)
    lr = ui.text(screen, label, theme.XS, theme.BRASS if ready else theme.MUTED,
                 pos, anchor="topright" if not right else "topleft")
    _sport_icon(screen, f, lr, right)
    _weapon_label(screen, ui, f, (x + bar_w if right else x, y + 64), right)

    if f.hack_timer > 0:
        status, scolor = "HACKEADO", (110, 240, 130)
    elif f.type_timer > 0:
        status, scolor = "HACKEANDO...", (110, 240, 130)
    elif f.exo_timer > 0:
        status, scolor = "EXOESQUELETO", (120, 190, 255)
    elif f.rush_timer > 0:
        status, scolor = "100 METROS", theme.BONE
    elif f.virus_timer > 0:
        status, scolor = "VÍRUS", (110, 240, 130)
    elif f.invulnerable_timer > 0:
        status, scolor = "INVULNERÁVEL", theme.BRASS
    elif f.fury_timer > 0:
        status, scolor = f"FÚRIA {f.fury_timer // config.FPS + 1}s", theme.EMBER
    elif f.speed_timer > 0:
        status, scolor = "TURBO", theme.BRASS
    elif f.stunned:
        status, scolor = "ATORDOADO", theme.MUTED
    else:
        return
    ui.text(screen, status, theme.XS, scolor, (x + bar_w if right else x, y + 76),
            anchor="topright" if right else "topleft")


_TOP_SHADE = None


def _top_shade(w, h):
    """Faixa escura no topo para o HUD não ficar solto em cima da arte da arena."""
    global _TOP_SHADE
    if _TOP_SHADE is None or _TOP_SHADE.get_size() != (w, h):
        _TOP_SHADE = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            a = int(185 * (1 - y / h) ** 1.4)
            _TOP_SHADE.fill((8, 6, 12, a), (0, y, w, 1))
    return _TOP_SHADE


def draw_battle(screen, ui, match):
    W = config.SCREEN_W
    screen.blit(_top_shade(W, 104), (0, 0))
    for i, f in enumerate(match.fighters[:2]):
        _fighter_block(screen, ui, f, right=i == 1, frame=match.frame, wins=match.wins[f])

    # relógio
    clock = pygame.Rect(0, 0, 72, 44)
    clock.midtop = (W // 2, 10)
    ui.panel(screen, clock, fill=theme.INK_2)
    secs = max(0, -(-match.time_left // config.FPS))
    hurry = secs <= 10 and not match.round_end
    color = theme.BLOOD if hurry and (match.frame // 15) % 2 else theme.BONE
    ui.text(screen, str(secs), theme.M, color, (clock.centerx, clock.centery + 1))
    label = "ROUND FINAL" if match.match_point else f"ROUND {match.round_no}"
    ui.text(screen, label, theme.XS, theme.MUTED, (W // 2, clock.bottom + 12))


TEAM_BLOCK_W = 330


def _team_row(screen, ui, f, x, y, right, match):
    """Uma linha do time no 2 x 2: etiqueta, personagem, vida e habilidade."""
    w = TEAM_BLOCK_W
    edge = x + w if right else x
    anchor = "topright" if right else "topleft"
    tag = ui.assets.text(f.label, theme.XS, theme.INK)
    tag_rect = pygame.Rect(0, 0, tag.get_width() + 8, 12)
    setattr(tag_rect, anchor, (edge, y))
    screen.fill(theme.SHADOW, tag_rect.move(1, 1))
    screen.fill(f.color, tag_rect)
    screen.blit(tag, tag.get_rect(center=(tag_rect.centerx + 1, tag_rect.centery)))
    name_pos = (tag_rect.left - 6, tag_rect.centery) if right else (tag_rect.right + 6, tag_rect.centery)
    ui.text(screen, f.stats.name.upper(), theme.XS, theme.BONE, name_pos,
            anchor="midright" if right else "midleft", shadow=True)
    other = (x, tag_rect.centery) if right else (x + w, tag_rect.centery)
    _weapon_label(screen, ui, f, other, not right)

    hp_w, ab_w, gap = 236, 84, 10
    hp_x = x + w - hp_w if right else x
    ab_x = x if right else x + hp_w + gap
    bar = pygame.Rect(hp_x, y + 16, hp_w, 10)
    if not f.alive_in_match:
        ui.bar(screen, bar, 0, theme.BLOOD, back=(30, 22, 30))
        prog = match.revive_progress.get(f, 0.0)
        if prog > 0:
            ui.bar(screen, bar, prog, theme.BONE, back=(30, 22, 30), flip=right)
        color = theme.BLOOD if (match.frame // 15) % 2 else theme.MUTED
        ui.text(screen, "CAÍDO", theme.XS, color, bar.center)
    else:
        ratio = f.hp / f.max_hp
        low = ratio <= 0.25 and (match.frame // 10) % 2 == 0
        color = _hp_color(ratio) if not low else mix(theme.BLOOD, theme.BONE, 0.4)
        ui.bar(screen, bar, ratio, color, back=(30, 22, 30), ticks=8, flip=right)
    ready = f.ability_ready
    ui.bar(screen, (ab_x, y + 18, ab_w, 6), f.ability_ratio, theme.BRASS if ready else theme.SKY,
           back=(22, 20, 32), flip=right)


def draw_team_battle(screen, ui, match):
    """HUD do duelo 2 x 2: um bloco por time (dois jogadores cada) e o relógio no meio."""
    W = config.SCREEN_W
    w = TEAM_BLOCK_W
    screen.blit(_top_shade(W, 96), (0, 0))
    for team in (0, 1):
        right = team == 1
        x = W - 16 - w if right else 16
        color = theme.TEAM_COLORS[team]
        head = pygame.Rect(x, 8, w, 16)
        screen.fill(theme.SHADOW, head.move(2, 2))
        screen.fill(mix(color, theme.INK, 0.55), head)
        screen.fill(color, (head.x, head.bottom - 2, head.w, 2))
        name = f"TIME {theme.TEAM_NAMES[team]}"
        ui.text(screen, name, theme.XS, theme.BONE, (head.right - 8, head.centery) if right else (head.x + 8, head.centery),
                anchor="midright" if right else "midleft", shadow=False)
        for k in range(config.ROUNDS_TO_WIN):
            px = head.x + 6 + k * 14 if right else head.right - 16 - k * 14
            pip = pygame.Rect(px, head.y + 3, 10, 10)
            screen.fill(theme.BRASS if k < match.wins[team] else theme.INK, pip)
            pygame.draw.rect(screen, theme.LINE_HI, pip, 1)
        for i, f in enumerate(sorted(match.members(team), key=lambda f: f.slot)):
            _team_row(screen, ui, f, x, 32 + i * 32, right, match)

    clock = pygame.Rect(0, 0, 72, 44)
    clock.midtop = (W // 2, 10)
    ui.panel(screen, clock, fill=theme.INK_2)
    secs = max(0, -(-match.time_left // config.FPS))
    hurry = secs <= 10 and not match.round_end
    color = theme.BLOOD if hurry and (match.frame // 15) % 2 else theme.BONE
    ui.text(screen, str(secs), theme.M, color, (clock.centerx, clock.centery + 1))
    label = "ROUND FINAL" if match.match_point else f"ROUND {match.round_no}"
    ui.text(screen, label, theme.XS, theme.MUTED, (W // 2, clock.bottom + 12))


def _band(screen, ui, color, slide, title, sub=None, title_color=theme.BONE):
    W, H = config.SCREEN_W, config.SCREEN_H
    band = pygame.Rect(0, 0, int(W * slide), 96)
    band.midleft = (0, H // 2)
    screen.fill(mix(color, theme.INK, 0.6), band)
    screen.fill(color, (band.x, band.y, band.w, 4))
    screen.fill(color, (band.x, band.bottom - 4, band.w, 4))
    if slide >= 1:
        ui.text(screen, title, theme.XL, title_color, (W // 2, H // 2 - (10 if sub else 0)))
        if sub:
            ui.text(screen, sub, theme.XS, theme.BONE, (W // 2, H // 2 + 30))


def draw_round_banner(screen, ui, match):
    W, H = config.SCREEN_W, config.SCREEN_H
    intro_age = config.ROUND_INTRO_FRAMES - match.intro
    if match.intro > 30:
        title = "ROUND FINAL" if match.match_point else f"ROUND {match.round_no}"
        _band(screen, ui, theme.LINE_HI, min(1.0, intro_age / 12), title)
    elif match.intro > 0 and not match.round_end:
        x = W // 2 + int((1 - min(1, (30 - match.intro) / 6)) * W)
        ui.text(screen, "LUTEM!", theme.XL, theme.BRASS, (x, H // 2))
    if match.round_end and match.round_banner:
        title, sub, color = match.round_banner
        age = config.ROUND_END_FRAMES - match.round_end
        if age > 20:
            _band(screen, ui, color, min(1.0, (age - 20) / 10), title, sub)


def draw_soccer(screen, ui, match):
    W, H = config.SCREEN_W, config.SCREEN_H
    board = pygame.Rect(0, 0, 300, 48)
    board.midtop = (W // 2, 10)
    ui.panel(screen, board, fill=theme.INK_2)
    half = board.w // 2
    for team in (0, 1):
        color = theme.TEAM_COLORS[team]
        block = pygame.Rect(board.x + 4 + team * (half - 4), board.y + 4, half - 4, board.h - 8)
        screen.fill(mix(color, theme.INK, 0.6), block)
        screen.fill(color, (block.x, block.bottom - 3, block.w, 3))
        name_x = block.x + 10 if team == 0 else block.right - 10
        ui.text(screen, theme.TEAM_NAMES[team], theme.XS, theme.BONE, (name_x, block.y + 10),
                anchor="midleft" if team == 0 else "midright")
        score_x = block.right - 28 if team == 0 else block.x + 28
        ui.text(screen, str(match.score[team]), theme.L, theme.BONE, (score_x, block.centery + 1))
    ui.text(screen, "x", theme.S, theme.MUTED, board.center)
    ui.text(screen, f"PRIMEIRO A {config.WIN_SCORE}", theme.XS, theme.MUTED, (W // 2, board.bottom + 12))

    # poder de cada jogador humano
    per_team = {0: 0, 1: 0}
    w = 196
    for f in match.fighters:
        if f.is_cpu:
            continue
        k = per_team[f.team]
        per_team[f.team] += 1
        x = 16 + k * (w + 12) if f.team == 0 else W - 16 - w - k * (w + 12)
        rect = pygame.Rect(x, H - 42, w, 30)
        screen.fill(theme.SHADOW, rect.move(2, 2))
        screen.fill(theme.INK_2, rect)
        screen.fill(f.color, (rect.x, rect.y, 4, rect.h))
        ready = f.super_cd <= 0
        ui.text(screen, f.label, theme.XS, f.color, (rect.x + 12, rect.y + 10), anchor="midleft", shadow=False)
        ui.text(screen, f.power.name, theme.XS, theme.BRASS if ready else theme.MUTED,
                (rect.right - 8, rect.y + 10), anchor="midright", shadow=False)
        ratio = 1 - f.super_cd / f.power.cooldown
        ui.bar(screen, (rect.x + 12, rect.y + 19, w - 20, 6), ratio, theme.BRASS if ready else theme.SKY)


def draw_goal_banner(screen, ui, team, scorer, own_goal, age):
    W, H = config.SCREEN_W, config.SCREEN_H
    slide = min(1.0, age / 14)
    color = theme.TEAM_COLORS[team]
    band_h = 96
    band = pygame.Rect(0, 0, int(W * slide), band_h)
    band.midleft = (0, H // 2)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 90))
    screen.blit(veil, (0, 0))
    screen.fill(mix(color, theme.INK, 0.55), band)
    screen.fill(color, (band.x, band.y, band.w, 4))
    screen.fill(color, (band.x, band.bottom - 4, band.w, 4))
    if slide >= 1:
        ui.text(screen, "GOL!", theme.XL, theme.BONE, (W // 2, H // 2 - 10))
        sub = "GOL CONTRA" if own_goal else f"{scorer} · TIME {theme.TEAM_NAMES[team]}".strip(" ·")
        ui.text(screen, sub, theme.XS, theme.BONE, (W // 2, H // 2 + 30))



def draw_basket(screen, ui, match):
    """Placar do basquete: pontos dos times, relógio do tempo e os 10 segundos de posse."""
    W = config.SCREEN_W
    board = pygame.Rect(0, 0, 300, 48)
    board.midtop = (W // 2, 10)
    ui.panel(screen, board, fill=theme.INK_2)
    half = board.w // 2
    for team in (0, 1):
        color = theme.TEAM_COLORS[team]
        block = pygame.Rect(board.x + 4 + team * (half - 4), board.y + 4, half - 4, board.h - 8)
        screen.fill(mix(color, theme.INK, 0.6), block)
        screen.fill(color, (block.x, block.bottom - 3, block.w, 3))
        name_x = block.x + 10 if team == 0 else block.right - 10
        ui.text(screen, theme.TEAM_NAMES[team], theme.XS, theme.BONE, (name_x, block.y + 10),
                anchor="midleft" if team == 0 else "midright")
        score_x = block.right - 28 if team == 0 else block.x + 28
        ui.text(screen, str(match.score[team]), theme.L, theme.BONE, (score_x, block.centery + 1))
    ui.text(screen, "x", theme.S, theme.MUTED, board.center)
    if match.overtime:
        ui.text(screen, "PRÓXIMA CESTA VENCE", theme.XS, theme.BRASS, (W // 2, board.bottom + 12))
    else:
        secs = max(0, -(-match.clock // config.FPS))
        ui.text(screen, f"{match.half}º TEMPO  {secs // 60}:{secs % 60:02d}", theme.XS,
                theme.BRASS if secs <= 10 else theme.MUTED, (W // 2, board.bottom + 12))
    owner = match.holder
    if owner is not None:
        from .basketball import SHOT_CLOCK
        left = max(0, SHOT_CLOCK - match.shot_clock // config.FPS)
        rect = pygame.Rect(0, 0, 120, 6)
        rect.midtop = (W // 2, board.bottom + 24)
        ratio = 1 - match.shot_clock / (SHOT_CLOCK * config.FPS)
        ui.bar(screen, rect, ratio, theme.TEAM_COLORS[owner.team] if left > 3 else theme.BRASS)


def draw_basket_banner(screen, ui, title, sub, team, age):
    """Faixa no meio da tela: cesta (com a cor do time), intervalo ou empate."""
    W, H = config.SCREEN_W, config.SCREEN_H
    slide = min(1.0, age / 14)
    color = theme.TEAM_COLORS[team] if team is not None else theme.BRASS
    band = pygame.Rect(0, 0, int(W * slide), 80)
    band.midleft = (0, H // 2)
    screen.fill(mix(color, theme.INK, 0.55), band)
    screen.fill(color, (band.x, band.y, band.w, 4))
    screen.fill(color, (band.x, band.bottom - 4, band.w, 4))
    if slide >= 1:
        ui.text(screen, title, theme.XL, theme.BONE, (W // 2, H // 2 - 8))
        if sub:
            ui.text(screen, sub, theme.XS, theme.BONE, (W // 2, H // 2 + 26))

# ─────────────────────────────────────────────
#  CAMPANHA
# ─────────────────────────────────────────────
BLOCK_W, BLOCK_H = 214, 48


def campaign_block_rect(i, n):
    """Quadro de cada jogador na parte de baixo da tela."""
    W, H = config.SCREEN_W, config.SCREEN_H
    gap = 10
    total = n * BLOCK_W + (n - 1) * gap
    x0 = 12 if n > 2 else (W - total) // 2
    return (x0 + i * (BLOCK_W + gap), H - BLOCK_H - 10, BLOCK_W, BLOCK_H)


def _soul_icon(screen, center, filled):
    cx, cy = center
    pts = [(cx, cy - 6), (cx + 5, cy), (cx, cy + 6), (cx - 5, cy)]
    pygame.draw.polygon(screen, theme.SHADOW, [(x + 1, y + 1) for x, y in pts])
    pygame.draw.polygon(screen, (170, 90, 230) if filled else theme.INK_3, pts)
    if filled:
        screen.fill((236, 214, 255), (cx - 1, cy - 3, 2, 2))
    else:
        pygame.draw.polygon(screen, theme.LINE_HI, pts, 1)


BOSS_MARKS = (0.5, 0.2)        # chefão chama ajuda com metade da vida e fica furioso com 20%


def draw_campaign(screen, ui, match):
    W = config.SCREEN_W
    run = match.run
    screen.blit(_top_shade(W, 80), (0, 0))

    # fase e onda (ou a vida do chefão)
    boss = match.boss
    if boss is not None and boss.alive_in_match:
        bar = pygame.Rect(0, 0, 440, 16)
        bar.midtop = (W // 2, 30)
        ui.text(screen, boss.stats.name.upper(), theme.XS, (200, 150, 250), (W // 2, 16))
        ratio = boss.hp / boss.max_hp
        tired = getattr(boss, "vulnerability", 1.0) > 1.0
        color = (240, 200, 90) if tired and (match.frame // 6) % 2 else (150, 60, 200)
        frame = ui.bar(screen, bar.inflate(4, 4), ratio, color, back=(30, 16, 40), ticks=10)
        for mark in BOSS_MARKS:
            # onde ele muda de comportamento: o risco some quando a vida já passou dali
            if ratio > mark:
                mx = frame.x + 1 + round((frame.w - 2) * mark)
                screen.fill(theme.BONE, (mx - 1, frame.y - 3, 2, frame.h + 6))
        if getattr(boss, "phase_label", ""):
            ui.text(screen, boss.phase_label, theme.XS, theme.BLOOD, (W // 2, bar.bottom + 14))
    elif match.lobby:
        ui.text(screen, f"FASE {run.phase_index + 1} · {match.phase.name}", theme.XS, theme.BONE, (W // 2, 18))
        ui.text(screen, match.objective_text, theme.XS, theme.BRASS, (W // 2, 36))
    else:
        title = f"FASE {run.phase_index + 1} · MASMORRA {match.dungeon_index + 1} · {match.dungeon.name}"
        ui.text(screen, title, theme.XS, theme.BONE, (W // 2, 18))
        total = len(match.waves)
        goal = match.objective_text
        if goal:
            color = theme.BRASS if (match.frame // 20) % 2 else theme.BONE
            ui.text(screen, goal, theme.XS, color, (W // 2, 36))
        elif match.wave >= 0:
            left = len(match.alive_enemies) + len(match.portals)
            wave = f"ONDA {match.wave + 1}/{total}"
            info = f"{wave} · {left} INIMIGO{'S' if left != 1 else ''}" if left else wave
            ui.text(screen, info, theme.XS, theme.MUTED, (W // 2, 36))
        for k in range(total):
            done = k < match.wave or (k == match.wave and match.state not in ("fight", "intro", "down"))
            pip = pygame.Rect(W // 2 - total * 9 + k * 18 + 3, 48, 12, 6)
            screen.fill(theme.SHADOW, pip.move(1, 1))
            screen.fill(theme.BRASS if done else (theme.LINE_HI if k == match.wave else theme.INK_3), pip)

    # continues e tempo
    ui.text(screen, "CONTINUES", theme.XS, theme.MUTED, (W - 16, 16), anchor="midright")
    for k in range(3):
        _soul_icon(screen, (W - 22 - k * 16, 34), k < run.continues)
    secs = match.elapsed // config.FPS
    ui.text(screen, f"{secs // 60}:{secs % 60:02d}", theme.XS, theme.BONE, (16, 16), anchor="midleft")

    # jogadores
    n = len(match.players)
    for i, f in enumerate(match.players):
        _campaign_block(screen, ui, f, pygame.Rect(campaign_block_rect(i, n)), match)


def _campaign_block(screen, ui, f, rect, match):
    screen.fill(theme.SHADOW, rect.move(2, 2))
    screen.fill(theme.INK_2, rect)
    screen.fill(f.color, (rect.x, rect.y, 4, rect.h))
    x = rect.x + 12
    tag = ui.assets.text(f.label, theme.XS, f.color)
    screen.blit(tag, tag.get_rect(midleft=(x, rect.y + 10)))
    ui.text(screen, f.stats.name.upper(), theme.XS, theme.BONE, (x + tag.get_width() + 8, rect.y + 10),
            anchor="midleft", shadow=False)
    bar = pygame.Rect(x, rect.y + 19, rect.w - 22, 12)
    if not f.alive_in_match:
        ui.bar(screen, bar, 0, theme.BLOOD, back=(30, 22, 30))
        prog = match.revive_progress.get(f, 0.0)
        if prog > 0:
            ui.bar(screen, bar, prog, theme.BONE, back=(30, 22, 30))
        color = theme.BLOOD if (match.frame // 15) % 2 else theme.MUTED
        ui.text(screen, "CAÍDO", theme.XS, color, bar.center)
        return
    ratio = f.hp / f.max_hp
    low = ratio <= 0.25 and (match.frame // 10) % 2 == 0
    color = _hp_color(ratio) if not low else mix(theme.BLOOD, theme.BONE, 0.4)
    ui.bar(screen, bar, ratio, color, back=(30, 22, 30), ticks=8)
    if f.shield > 0:
        screen.fill((150, 212, 240), (bar.x + 1, bar.y + 1, round((bar.w - 2) * min(1, f.shield / 40)), 3))
    ui.text(screen, f"{f.hp}", theme.XS, theme.BONE, (rect.right - 10, rect.y + 10), anchor="midright", shadow=False)
    ab = pygame.Rect(x, rect.y + 35, 70, 6)
    ready = f.ability_ready
    ui.bar(screen, ab, f.ability_ratio, theme.BRASS if ready else theme.SKY, back=(22, 20, 32))
    label = f.ability.name.upper() + (" OK" if ready else "")
    lr = ui.text(screen, label, theme.XS, theme.BRASS if ready else theme.MUTED, (ab.right + 6, ab.centery),
                 anchor="midleft", shadow=False)
    _sport_icon(screen, f, lr, False)
    if f.fury_timer > 0:
        ui.text(screen, "FÚRIA", theme.XS, theme.EMBER, (rect.right - 10, ab.centery), anchor="midright", shadow=False)
    _ammo_strip(screen, f, pygame.Rect(x, rect.bottom - 5, rect.w - 22, 3))


def _sport_icon(screen, f, label_rect, right):
    """Multiesportista (Cauanzera): desenhinho do próximo esporte ao lado do nome."""
    sport = getattr(f.ability, "sport", None)
    if sport is None or label_rect is None:
        return
    cx = label_rect.left - 9 if not right else label_rect.right + 9
    cy = label_rect.centery
    if sport == "ATLETISMO":                       # tênis de corrida
        screen.fill((20, 14, 22), (cx - 6, cy - 3, 12, 7))
        screen.fill((240, 240, 236), (cx - 5, cy - 2, 10, 4))
        screen.fill((84, 162, 222), (cx - 5, cy + 1, 10, 2))
        screen.fill((240, 240, 236), (cx + 3, cy - 4, 2, 2))
        return
    from .projectiles import draw_sport_ball
    draw_sport_ball(screen, cx, cy, 5, "basquete" if sport == "BASQUETE" else "volei", 0)


def _ammo_strip(screen, f, area):
    """Munição em tracinhos na beirada de baixo do quadro do jogador (ou a recarga enchendo)."""
    mag = f.mag
    if not mag or (f.weapon.is_melee and not f.reloading):
        return
    if f.reloading:
        screen.fill((58, 44, 22), area)
        screen.fill(theme.BRASS, (area.x, area.y, round(area.w * f.reload_ratio), area.h))
        return
    cap = max(mag, f.ammo)
    pip = max(1, min(12, (area.w - (cap - 1)) // cap))
    for i in range(cap):
        if i >= f.ammo:
            color = (44, 40, 54)
        elif i >= mag:
            color = theme.BRASS
        else:
            color = (226, 220, 200)
        screen.fill(color, (area.x + i * (pip + 1), area.y, pip, area.h))


def draw_teleport_vote(screen, ui, match):
    """Botão TELETRANSPORTE DE FASE no fim da fase, com quem já confirmou. Devolve o retângulo do botão."""
    W = config.SCREEN_W
    pulse = 0.5 + 0.5 * math.sin(match.frame * 0.12)
    button = pygame.Rect(0, 0, 440, 54)
    button.midtop = (W // 2, 92)
    hot = button.collidepoint(pygame.mouse.get_pos())
    glow = pygame.Surface(button.inflate(24, 24).size, pygame.SRCALPHA)
    glow.fill((170, 120, 250, round(40 + 50 * pulse)))
    screen.blit(glow, button.inflate(24, 24).topleft)
    screen.fill(theme.SHADOW, button.move(3, 4))
    screen.fill((46, 30, 70) if not hot else (70, 46, 104), button)
    pygame.draw.rect(screen, mix(theme.BRASS, (255, 255, 255), 0.3 * pulse), button, 3)
    ui.text(screen, "TELETRANSPORTE DE FASE", theme.S, theme.BONE, (button.centerx, button.centery + 1))
    players = match.players
    chip_w, gap = 96, 8
    x = W // 2 - (len(players) * chip_w + (len(players) - 1) * gap) // 2
    for p in players:
        chip = pygame.Rect(x, button.bottom + 12, chip_w, 20)
        ready = p in match.votes
        screen.fill(theme.SHADOW, chip.move(2, 2))
        screen.fill(mix(theme.MOSS, theme.INK, 0.5) if ready else theme.INK_2, chip)
        screen.fill(p.color, (chip.x, chip.y, 3, chip.h))
        if ready:
            label, color = f"{p.label} PRONTO", theme.BONE
        else:
            label = f"{p.label} " + "." * (1 + (match.frame // 15) % 3)
            color = theme.MUTED
        ui.text(screen, label, theme.XS, color, (chip.x + 10, chip.centery + 1), anchor="midleft", shadow=False)
        x += chip_w + gap
    ui.text(screen, "ATACAR NO TECLADO · BOTÃO NO CELULAR · OU CLIQUE", theme.XS, theme.MUTED,
            (W // 2, button.bottom + 48))
    return button


def draw_campaign_banners(screen, ui, match):
    W = config.SCREEN_W
    if match.wave_banner > 0 and getattr(match, "state", "") == "fight":
        age = 100 - match.wave_banner
        x = W // 2 + int((1 - min(1, age / 8)) * W)
        if match.wave_banner > 12 or match.wave_banner % 4 < 2:
            last = match.wave == len(match.waves) - 1
            word = "ONDA FINAL" if last and match.wave > 0 else f"ONDA {match.wave + 1}"
            ui.text(screen, word, theme.L, theme.BRASS, (x, 120))
    if getattr(match, "state", "") == "between":
        ui.text(screen, "ONDA CONCLUÍDA", theme.S, theme.MOSS, (W // 2, 120))
    if match.banner:
        title, sub, color, age = match.banner
        _band(screen, ui, color, min(1.0, age / 12), title, sub)


def edge_arrow(screen, sx, sy, color, size, top=64, bottom_gap=72):
    """Setinha na borda da tela apontando para (sx, sy), que está fora dela.
    Devolve onde a seta ficou (para pôr um rótulo do lado)."""
    W, H = config.SCREEN_W, config.SCREEN_H
    cx = W / 2
    bottom = H - bottom_gap            # entre o HUD de cima e o de baixo
    cy = (top + bottom) / 2
    dx, dy = sx - cx, sy - cy
    k = min((W / 2 - 22) / abs(dx) if dx else 1e9, (bottom - top) / 2 / abs(dy) if dy else 1e9)
    ax, ay = cx + dx * k, cy + dy * k
    d = math.hypot(dx, dy) or 1
    ux, uy = dx / d, dy / d
    tip = (ax + ux * size, ay + uy * size)
    left = (ax - uy * size * 0.7, ay + ux * size * 0.7)
    right = (ax + uy * size * 0.7, ay - ux * size * 0.7)
    pygame.draw.polygon(screen, theme.SHADOW, [(x + 1, y + 1) for x, y in (tip, left, right)])
    pygame.draw.polygon(screen, color, (tip, left, right))
    return ax, ay, ux, uy
