"""Liga e desliga como TV antiga: os painéis que abrem no meio do jogo (loja, pausa, armário...)
aparecem como uma tela de tubo ligando e somem como ela desligando.

- Ligando: um ponto de luz no meio vira uma linha fina na horizontal, e a linha abre para cima e
  para baixo até virar o painel inteiro, com um clarão que se apaga.
- Desligando: o contrário. O painel se fecha de cima e de baixo até a linha do meio, a linha
  encolhe até virar um ponto e o ponto some.

Uso: no lugar de desenhar o painel direto na tela, ``crt.panel(screen, chave, desenhar)``, onde
``desenhar(superfície)`` é a função que já existia. Quando o painel para de ser desenhado (o menu
fechou), o desligar roda sozinho no fim do quadro com a última imagem dele (``end_frame``, chamado
pelo jogo depois de cada cena).
"""
import pygame

OPEN_MS = 240                # ligando
CLOSE_MS = 200               # desligando
LINE_PART = 0.34             # parte do tempo em que é só a linha de luz
LINE = (255, 252, 240)
GLOW = (150, 200, 255)

now = pygame.time.get_ticks  # trocado nos testes e nas prévias


class _Tube:
    def __init__(self, t0):
        self.opened_at = t0       # quando começou a ligar
        self.closed_at = None     # quando começou a desligar
        self.snap = None          # última imagem do painel (para o desligar)
        self.rect = None


_tubes = {}
_seen = set()
_layers = {}


def _layer(size):
    layer = _layers.get(size)
    if layer is None:
        layer = _layers[size] = pygame.Surface(size, pygame.SRCALPHA)
    layer.fill((0, 0, 0, 0))
    return layer


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def panel(screen, key, draw, rect=None):
    """Desenha o painel ``key`` com o efeito de TV. ``rect``: área do painel (sem ela, a área
    desenhada de fato)."""
    t = now()
    tube = _tubes.get(key)
    if tube is None:
        tube = _tubes[key] = _Tube(t)
    elif tube.closed_at is not None:
        # reabriu no meio do desligar: liga a partir de onde estava
        p = _closing_progress(tube, t)
        tube.opened_at = t - round(p * OPEN_MS)
        tube.closed_at = None
    _seen.add(key)
    p = min(1.0, (t - tube.opened_at) / OPEN_MS)
    layer = _layer(screen.get_size())
    draw(layer)
    _keep(tube, layer, rect)
    if p >= 1:
        screen.blit(layer, (0, 0))
    else:
        _render(screen, tube.snap, tube.rect, p, opening=True)


def _keep(tube, layer, rect):
    area = pygame.Rect(rect) if rect is not None else layer.get_bounding_rect()
    area = area.clip(layer.get_rect())
    if area.w and area.h:
        tube.rect = area
        tube.snap = layer.subsurface(area).copy()


def _closing_progress(tube, t):
    return max(0.0, 1 - (t - tube.closed_at) / CLOSE_MS)


def end_frame(screen):
    """Fim do quadro: os painéis que não foram desenhados agora desligam (e somem ao terminar)."""
    t = now()
    for key in list(_tubes):
        tube = _tubes[key]
        if key in _seen:
            continue
        if tube.closed_at is None:
            if tube.snap is None:
                del _tubes[key]
                continue
            # desliga a partir de onde estava (se nem terminou de ligar, desliga dali)
            opened = min(1.0, (t - tube.opened_at) / OPEN_MS)
            tube.closed_at = t - round((1 - opened) * CLOSE_MS)
        p = _closing_progress(tube, t)
        if p <= 0:
            del _tubes[key]
            continue
        _render(screen, tube.snap, tube.rect, p, opening=False)
    _seen.clear()


def reset():
    """Troca de cena: nada da tela anterior fica desligando por cima da nova."""
    _tubes.clear()
    _seen.clear()


def _render(screen, snap, rect, p, opening):
    """Um quadro do efeito. ``p``: 0 = desligado, 1 = painel inteiro."""
    if snap is None or rect is None or p <= 0:
        return
    cx, cy = rect.center
    if p < LINE_PART:
        q = p / LINE_PART
        if opening:
            w = max(4, round(rect.w * _ease(q)))
        else:
            w = max(2, round(rect.w * q ** 2))           # a linha encolhe até o ponto
        bright = 1.0 if q > 0.15 or opening else q / 0.15
        glow = tuple(round(c * 0.5 * bright) for c in GLOW)
        screen.fill(glow, (cx - w // 2 - 6, cy - 3, w + 12, 6), special_flags=pygame.BLEND_RGB_ADD)
        screen.fill(tuple(round(c * bright) for c in LINE), (cx - w // 2, cy - 1, w, 2))
        if w < 12:                                         # o pontinho no meio
            screen.fill(LINE, (cx - 2, cy - 2, 4, 4))
        return
    q = (p - LINE_PART) / (1 - LINE_PART)
    h = max(2, round(rect.h * (_ease(q) if opening else q ** 1.6)))
    img = pygame.transform.scale(snap, (rect.w, h))
    flash = round(170 * (1 - q) ** 2)
    if flash:
        img.fill((flash, flash, flash), special_flags=pygame.BLEND_RGB_ADD)
    if q < 0.85:                                           # linhas de varredura do tubo
        dark = round(255 - 90 * (1 - q / 0.85))
        lines = pygame.Surface((rect.w, h), pygame.SRCALPHA)
        lines.fill((255, 255, 255, 255))
        for y in range(0, h, 3):
            lines.fill((dark, dark, dark, 255), (0, y, rect.w, 1))
        img.blit(lines, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    top = cy - h // 2
    screen.blit(img, (rect.x, top))
    if q < 0.5:                                            # o resto da linha de luz no meio
        k = 1 - q / 0.5
        screen.fill(tuple(round(c * k) for c in LINE), (rect.x, cy - 1, rect.w, 2),
                    special_flags=pygame.BLEND_RGB_ADD)
