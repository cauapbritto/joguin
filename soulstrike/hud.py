"""Informações na tela durante a partida."""
import pygame

from . import config, theme
from .ui import mix


def _hp_color(ratio):
    return theme.MOSS if ratio > 0.5 else theme.BRASS if ratio > 0.25 else theme.BLOOD


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
    ui.text(screen, label, theme.XS, theme.BRASS if ready else theme.MUTED,
            (ab_x + ab_w if not right else ab_x, y + 60), anchor="topright" if not right else "topleft")
    weapon = f.weapon.name.upper()
    ui.text(screen, weapon, theme.XS, theme.MUTED, (x + bar_w if right else x, y + 60),
            anchor="topright" if right else "topleft")

    if f.invulnerable_timer > 0:
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
        ui.bar(screen, bar.inflate(4, 4), ratio, (150, 60, 200), back=(30, 16, 40), ticks=10)
        if getattr(boss, "phase_label", ""):
            ui.text(screen, boss.phase_label, theme.XS, theme.BLOOD, (W // 2, bar.bottom + 14))
    else:
        ui.text(screen, f"FASE {run.phase_index + 1} · {match.phase.name}", theme.XS, theme.BONE, (W // 2, 18))
        total = len(match.phase.waves)
        if match.wave >= 0:
            left = len(match.alive_enemies) + len(match.portals)
            wave = f"ONDA {match.wave + 1}/{total}"
            info = f"{wave} · {left} INIMIGO{'S' if left != 1 else ''}" if left else wave
            ui.text(screen, info, theme.XS, theme.MUTED, (W // 2, 36))
        for k in range(total):
            done = k < match.wave or (k == match.wave and match.state in ("between", "clear"))
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
    ui.text(screen, label, theme.XS, theme.BRASS if ready else theme.MUTED, (ab.right + 6, ab.centery),
            anchor="midleft", shadow=False)
    if f.fury_timer > 0:
        ui.text(screen, "FÚRIA", theme.XS, theme.EMBER, (rect.right - 10, ab.centery), anchor="midright", shadow=False)


def draw_campaign_banners(screen, ui, match):
    W = config.SCREEN_W
    if match.wave_banner > 0 and match.state == "fight":
        age = 100 - match.wave_banner
        x = W // 2 + int((1 - min(1, age / 8)) * W)
        if match.wave_banner > 12 or match.wave_banner % 4 < 2:
            last = match.wave == len(match.phase.waves) - 1
            word = "ONDA FINAL" if last and match.wave > 0 else f"ONDA {match.wave + 1}"
            ui.text(screen, word, theme.L, theme.BRASS, (x, 120))
    if match.state == "between":
        ui.text(screen, "ONDA CONCLUÍDA", theme.S, theme.MOSS, (W // 2, 120))
    if match.banner:
        title, sub, color, age = match.banner
        _band(screen, ui, color, min(1.0, age / 12), title, sub)
