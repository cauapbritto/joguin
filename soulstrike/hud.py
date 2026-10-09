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
    ratio = f.hp / f.stats.max_hp
    low = ratio <= 0.25 and (frame // 10) % 2 == 0
    color = _hp_color(ratio) if not low else mix(theme.BLOOD, theme.BONE, 0.4)
    ui.bar(screen, (x, y + 20, bar_w, 16), ratio, color, back=(30, 22, 30), ticks=10, flip=right)
    hp_txt = f"{f.hp}/{f.stats.max_hp}"
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
