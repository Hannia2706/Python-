# Ejemplo visual con pygame: pelotas de colores con brillo (glow) y estela,
# rebotando sobre un fondo con gradiente y estrellas titilantes.
import pygame
import random
import math

pygame.init()

WIDTH, HEIGHT = 960, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame - Demo visual")
clock = pygame.time.Clock()

# --- Fondo con gradiente vertical (azul oscuro -> violeta) ---
TOP_COLOR = (10, 12, 40)
BOTTOM_COLOR = (60, 20, 80)

background = pygame.Surface((WIDTH, HEIGHT))
for y in range(HEIGHT):
    t = y / HEIGHT
    color = (
        int(TOP_COLOR[0] + (BOTTOM_COLOR[0] - TOP_COLOR[0]) * t),
        int(TOP_COLOR[1] + (BOTTOM_COLOR[1] - TOP_COLOR[1]) * t),
        int(TOP_COLOR[2] + (BOTTOM_COLOR[2] - TOP_COLOR[2]) * t),
    )
    pygame.draw.line(background, color, (0, y), (WIDTH, y))

# --- Estrellas titilantes ---
NUM_STARS = 120
stars = [
    {
        "pos": (random.randint(0, WIDTH), random.randint(0, HEIGHT)),
        "radius": random.uniform(0.5, 2.0),
        "phase": random.uniform(0, math.tau),
        "speed": random.uniform(1.5, 4.0),
    }
    for _ in range(NUM_STARS)
]

# --- Superficie de estela (fade trail) con canal alpha ---
trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

# --- Pelotas de colores ---
COLORS = [
    (255, 90, 90),
    (255, 200, 80),
    (100, 220, 150),
    (90, 170, 255),
    (200, 120, 255),
    (255, 130, 200),
]

NUM_BALLS = 8
balls = []
for _ in range(NUM_BALLS):
    radius = random.randint(10, 22)
    balls.append({
        "pos": [random.uniform(radius, WIDTH - radius), random.uniform(radius, HEIGHT - radius)],
        "vel": [random.uniform(-4, 4), random.uniform(-4, 4)],
        "radius": radius,
        "color": random.choice(COLORS),
    })


def draw_glow_circle(surface, color, center, radius):
    """Dibuja un circulo con un halo de brillo usando varios anillos translucidos."""
    glow_layers = 4
    for i in range(glow_layers, 0, -1):
        alpha = int(45 * (i / glow_layers) ** 2)
        glow_radius = radius + i * radius * 0.6
        glow_color = (*color, alpha)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius), special_flags=pygame.BLEND_RGBA_ADD)

    pygame.draw.circle(surface, color, center, radius)
    highlight = (min(color[0] + 80, 255), min(color[1] + 80, 255), min(color[2] + 80, 255))
    pygame.draw.circle(surface, highlight, (center[0] - radius * 0.3, center[1] - radius * 0.3), radius * 0.35)


running = True
t = 0.0
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    t += clock.get_time() / 1000.0

    # Fondo
    screen.blit(background, (0, 0))

    # Estrellas titilantes
    for star in stars:
        twinkle = (math.sin(t * star["speed"] + star["phase"]) + 1) / 2
        brightness = int(120 + 135 * twinkle)
        pygame.draw.circle(screen, (brightness, brightness, min(255, brightness + 30)), star["pos"], star["radius"])

    # Atenuar la estela del frame anterior
    trail_surface.fill((0, 0, 0, 25))

    # Actualizar y dibujar pelotas
    for ball in balls:
        ball["pos"][0] += ball["vel"][0]
        ball["pos"][1] += ball["vel"][1]

        r = ball["radius"]
        if ball["pos"][0] - r <= 0 or ball["pos"][0] + r >= WIDTH:
            ball["vel"][0] *= -1
            ball["pos"][0] = max(r, min(WIDTH - r, ball["pos"][0]))
        if ball["pos"][1] - r <= 0 or ball["pos"][1] + r >= HEIGHT:
            ball["vel"][1] *= -1
            ball["pos"][1] = max(r, min(HEIGHT - r, ball["pos"][1]))

        pos = (int(ball["pos"][0]), int(ball["pos"][1]))
        pygame.draw.circle(trail_surface, (*ball["color"], 90), pos, r)
        draw_glow_circle(screen, ball["color"], pos, r)

    screen.blit(trail_surface, (0, 0))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
