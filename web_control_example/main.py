import sys
import math
import pygame

import remote_input
from web_server import start_server_thread

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

COLOR_BG = (15, 12, 25)
COLOR_PLAYER = (255, 180, 30)
COLOR_PLAYER_ATTACK = (255, 60, 60)
COLOR_FLOOR_A = (30, 26, 50)
COLOR_FLOOR_B = (25, 22, 42)
COLOR_TEXT = (140, 135, 160)

GRAVITY = 0.6
JUMP_SPEED = -12
MOVE_SPEED = 5

class Player:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 40, 40)
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 40
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.attacking = False
        self.attack_timer = 0
        self.facing = 1

    def update(self, commands):
        dx = 0
        if commands.get("right"):
            dx += 1
            self.facing = 1
        if commands.get("left"):
            dx -= 1
            self.facing = -1

        self.vx = dx * MOVE_SPEED

        if commands.get("jump") and self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

        self.vy += GRAVITY

        self.rect.x += self.vx
        self.rect.y += self.vy

        if self.rect.bottom >= SCREEN_HEIGHT - 40:
            self.rect.bottom = SCREEN_HEIGHT - 40
            self.vy = 0
            self.on_ground = True

        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        if commands.get("attack") and not self.attacking:
            self.attacking = True
            self.attack_timer = 15

        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

    def draw(self, screen):
        color = COLOR_PLAYER_ATTACK if self.attacking else COLOR_PLAYER
        pygame.draw.rect(screen, color, self.rect, border_radius=4)

        if self.attacking:
            atk_rect = self.rect.inflate(30, 30)
            alpha = int(100 * (self.attack_timer / 15))
            surf = pygame.Surface((atk_rect.width, atk_rect.height), pygame.SRCALPHA)
            surf.fill((*COLOR_PLAYER_ATTACK[:3], alpha))
            screen.blit(surf, atk_rect.topleft)

def draw_background(screen):
    screen.fill(COLOR_BG)
    for x in range(0, SCREEN_WIDTH, 40):
        for y in range(0, SCREEN_HEIGHT, 40):
            color = COLOR_FLOOR_A if (x + y) // 40 % 2 == 0 else COLOR_FLOOR_B
            pygame.draw.rect(screen, color, (x, y, 40, 40))

def draw_controls_hint(screen):
    commands = remote_input.get_state()
    pressed = [k for k, v in commands.items() if v]
    text = "Comandos recebidos: " + (", ".join(pressed) if pressed else "nenhum")
    font = pygame.font.Font(None, 24)
    surf = font.render(text, True, COLOR_TEXT)
    screen.blit(surf, (20, 20))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Web Control Example")
    clock = pygame.time.Clock()

    player = Player()

    start_server_thread()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        commands = remote_input.get_state()
        player.update(commands)

        draw_background(screen)

        floor_rect = pygame.Rect(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40)
        pygame.draw.rect(screen, (40, 36, 60), floor_rect)
        pygame.draw.line(screen, (60, 55, 80), (0, SCREEN_HEIGHT - 40), (SCREEN_WIDTH, SCREEN_HEIGHT - 40), 2)

        player.draw(screen)
        draw_controls_hint(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
