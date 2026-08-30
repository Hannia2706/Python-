"""
HOOK 'EM SWEEPER - a Minesweeper clone, UT Austin edition

Based on the simple structure of the "minesweeper-pygame" clone
(Tile / Board / Game classes), extended with:

    - Two board modes: SQUARE (8 neighbours) and HEXAGONAL (6 neighbours).
    - The player freely types the board width and height, within a limit
      (MIN_DIM .. MAX_DIM) so the window still fits on screen.
    - The mine count is also free, with an automatic cap based on the
      chosen board size.
    - If the board is large, each cell shrinks on its own to fit the
      screen (auto-fit).
    - Minimal top bar (HUD) with remaining bulls and a timer.
    - Always-safe first click: bulls are placed after the first click,
      avoiding the clicked cell and its neighbours.
    - Win / lose screens and restart with the R key.

Minimalist look: flat cells with a thin gap, no borders, a single accent
color. The mines are "bulls" (Texas Longhorns) and a flag is the "Hook 'em"
hand. Both can be swapped for a PNG in assets/: toro.png for the bull
(or bull / longhorn / bevo / mine) and hookemhand.png for the flag
(or hookem / hand / flag); otherwise they are drawn. Everything is rendered
on a canvas SS times larger and scaled down with smoothing when shown
(SSAA), so edges and text do not look jagged or blurry.

The palette is built on the two UT Austin core colors: Burnt Orange
(#BF5700) as the only accent, over limestone paper and charcoal text.

Controls:
    - Left click   -> reveal a cell
    - Right click  -> place / remove a flag
    - R            -> restart (back to the menu)
    - ESC          -> quit

AUTHORS:
    - Gio
"""

import math
import os
import random
import sys
import time

import pygame


# ------------------------------------------------------------------------
# GENERAL SETTINGS
# ------------------------------------------------------------------------
FPS = 60
TITLE = "Hook 'Em Sweeper"

# Optional images. Drop a PNG in the assets/ folder with any of these names
# and it is used instead of the drawn shape (longhorn / Hook 'em hand).
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
MINE_IMAGE_NAMES = ("toro.png", "bull.png", "longhorn.png", "bevo.png", "mine.png")
FLAG_IMAGE_NAMES = ("hookemhand.png", "hookem.png", "hand.png", "flag.png")

# Supersampling (SSAA): everything is drawn on a canvas SS times larger and
# scaled down when shown. That smooths edges and text (less "blur").
SS = 2

HUD_HEIGHT = 52 * SS

# Board resize limit (in cells per side).
MIN_DIM = 5
MAX_DIM = 30

# Maximum room the play area may take, in canvas pixels (HUD not included).
# The real window will be SS times smaller.
MAX_VIEW_W = 1180 * SS
MAX_VIEW_H = 780 * SS
MIN_WIN_W = 360 * SS         # so the HUD text fits

# "Design" size of each cell and the smallest it may shrink to.
BASE_TS = 34 * SS
MIN_TS = 14 * SS
BASE_HEXR = 24 * SS          # hexagon radius (center -> vertex)
MIN_HEXR = 12 * SS

# ------------------------------------------------------------------------
# COLORS - minimalist, built on the two UT Austin core colors
# ------------------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

UT_ORANGE = (191, 87, 0)        # Burnt Orange  #BF5700
UT_CHARCOAL = (51, 63, 72)      # #333F48

BG = (237, 234, 226)            # limestone paper
INK = (51, 63, 72)             # primary text / lines
MUTED = (150, 144, 130)         # secondary text
ACCENT = (191, 87, 0)           # burnt orange - the only strong color
ACCENT_DIM = (150, 68, 0)       # pressed / hover

BGCOLOUR = BG
LIGHTGREY = MUTED
GREEN = (86, 132, 62)           # win text
RED = ACCENT                    # lose text

# Number colors (1..8), muted, readable on the near-white revealed cell.
NUMBER_COLORS = {
    1: (0, 95, 134), 2: (58, 115, 48), 3: (191, 87, 0), 4: (0, 59, 92),
    5: (140, 55, 20), 6: (0, 119, 138), 7: (51, 63, 72), 8: (120, 120, 120),
}
# Cells are flat and separated by a small gap (no borders).
CELL_COVER = (206, 200, 187)    # warm gray
CELL_REVEAL = (243, 241, 234)   # near-paper
CELL_EXPLODE = UT_CHARCOAL      # the bull you clicked
CELL_GAP = 0.90                 # cells shrink toward their center

SQRT3 = math.sqrt(3)

# Cell types: "." empty   "X" mine   "C" clue (number)


# ------------------------------------------------------------------------
# BOARD GEOMETRY
# ------------------------------------------------------------------------
class SquareGrid:
    """Classic grid: each cell touches 8 neighbours."""

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.ts = max(MIN_TS, min(BASE_TS, MAX_VIEW_W // cols, MAX_VIEW_H // rows))

    def coords(self):
        for r in range(self.rows):
            for c in range(self.cols):
                yield (c, r)

    def in_bounds(self, c, r):
        return 0 <= c < self.cols and 0 <= r < self.rows

    def neighbours(self, c, r):
        out = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                if self.in_bounds(c + dc, r + dr):
                    out.append((c + dc, r + dr))
        return out

    def pixel_size(self):
        return (self.cols * self.ts, self.rows * self.ts)

    def inradius(self):
        return self.ts / 2

    def center(self, c, r):
        return (c * self.ts + self.ts / 2, r * self.ts + self.ts / 2)

    def polygon(self, c, r):
        x, y, s = c * self.ts, r * self.ts, self.ts
        return [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]

    def cell_at(self, px, py):
        c, r = int(px // self.ts), int(py // self.ts)
        return (c, r) if self.in_bounds(c, r) else None


# Neighbour offsets for "pointy-top" hexagons, "odd-r" layout
# (odd rows are shifted half a cell to the right). [dcol, drow]
ODDR_NEIGHBOURS = {
    0: [(+1, 0), (0, -1), (-1, -1), (-1, 0), (-1, +1), (0, +1)],   # even row
    1: [(+1, 0), (+1, -1), (0, -1), (-1, 0), (0, +1), (+1, +1)],   # odd row
}


class HexGrid:
    """Hexagonal board: each cell touches 6 neighbours."""

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        fit_w = MAX_VIEW_W / (SQRT3 * (cols + 0.5))
        fit_h = MAX_VIEW_H / (1.5 * rows + 0.5)
        self.R = max(MIN_HEXR, min(BASE_HEXR, fit_w, fit_h))

    def coords(self):
        for r in range(self.rows):
            for c in range(self.cols):
                yield (c, r)

    def in_bounds(self, c, r):
        return 0 <= c < self.cols and 0 <= r < self.rows

    def neighbours(self, c, r):
        diffs = ODDR_NEIGHBOURS[r & 1]
        return [(c + dc, r + dr) for dc, dr in diffs if self.in_bounds(c + dc, r + dr)]

    def center(self, c, r):
        x = self.R * SQRT3 * (c + 0.5 * (r & 1) + 0.5)
        y = self.R * (1 + 1.5 * r)
        return (x, y)

    def polygon(self, c, r):
        cx, cy = self.center(c, r)
        pts = []
        for i in range(6):
            ang = math.radians(60 * i - 90)
            pts.append((cx + self.R * math.cos(ang), cy + self.R * math.sin(ang)))
        return pts

    def pixel_size(self):
        w = math.ceil(self.R * SQRT3 * (self.cols + 0.5))
        h = math.ceil(self.R * (1.5 * self.rows + 0.5))
        return (w, h)

    def inradius(self):
        return self.R * SQRT3 / 2

    def cell_at(self, px, py):
        # In a hex grid the hexagon is the region closest to its center,
        # so it is enough to find the nearest center.
        best, best_d = None, float("inf")
        for cell in self.coords():
            cx, cy = self.center(*cell)
            d = (cx - px) ** 2 + (cy - py) ** 2
            if d < best_d:
                best, best_d = cell, d
        if best is not None and best_d <= (self.R * 1.2) ** 2:
            return best
        return None


# ------------------------------------------------------------------------
# GAME MODEL
# ------------------------------------------------------------------------
class Tile:
    __slots__ = ("type", "revealed", "flagged", "number", "wrong")

    def __init__(self):
        self.type = "."
        self.revealed = False
        self.flagged = False
        self.number = 0
        self.wrong = False       # wrong flag (shown when you lose)


class Board:
    def __init__(self, grid, mines):
        self.grid = grid
        self.mines = mines
        self.tiles = {cell: Tile() for cell in grid.coords()}
        self.mines_placed = False
        self.detonated = None
        self.dug = set()

    def place_mines(self, safe_cell):
        forbidden = {safe_cell} | set(self.grid.neighbours(*safe_cell))
        candidates = [c for c in self.grid.coords() if c not in forbidden]
        target = min(self.mines, len(candidates))
        for cell in random.sample(candidates, target):
            self.tiles[cell].type = "X"
        self.mines = target

        for cell in self.grid.coords():
            tile = self.tiles[cell]
            if tile.type == "X":
                continue
            n = sum(1 for nb in self.grid.neighbours(*cell)
                    if self.tiles[nb].type == "X")
            tile.number = n
            tile.type = "C" if n > 0 else "."
        self.mines_placed = True

    def dig(self, cell):
        """Reveal the cell (and flood empty areas). False if it was a mine."""
        if not self.mines_placed:
            self.place_mines(cell)

        stack = [cell]
        while stack:
            cur = stack.pop()
            if cur in self.dug:
                continue
            tile = self.tiles[cur]
            if tile.flagged:
                continue
            self.dug.add(cur)
            tile.revealed = True

            if tile.type == "X":
                self.detonated = cur
                return False
            if tile.number > 0:
                continue
            for nb in self.grid.neighbours(*cur):
                if nb not in self.dug:
                    stack.append(nb)
        return True

    def flags_used(self):
        return sum(1 for t in self.tiles.values() if t.flagged)

    def reveal_all_mines(self):
        for tile in self.tiles.values():
            if tile.type == "X" and not tile.flagged:
                tile.revealed = True
            elif tile.flagged and tile.type != "X":
                tile.flagged = False
                tile.revealed = True
                tile.wrong = True

    def is_won(self):
        return all(t.revealed for t in self.tiles.values() if t.type != "X")


# ------------------------------------------------------------------------
# DRAWING
# ------------------------------------------------------------------------
def load_image(names):
    """Return a Surface for the first matching file in assets/, or None."""
    for name in names:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.isfile(path):
            try:
                return pygame.image.load(path).convert_alpha()
            except pygame.error:
                pass
    return None


class _Sprite:
    """An optional image, cached at whatever size it is last drawn at."""

    def __init__(self, image):
        self.image = image
        self._scaled = None
        self._box = 0

    def get(self, box):
        if self.image is None:
            return None
        if self._scaled is None or self._box != box:
            iw, ih = self.image.get_size()
            k = min(box / iw, box / ih)
            self._scaled = pygame.transform.smoothscale(
                self.image, (max(1, int(iw * k)), max(1, int(ih * k))))
            self._box = box
        return self._scaled

    def blit(self, screen, cx, cy, box):
        spr = self.get(box)
        if spr is None:
            return False
        screen.blit(spr, (cx - spr.get_width() / 2, cy - spr.get_height() / 2))
        return True


class CellRenderer:
    """Draws the board procedurally. Works for any cell shape (square or
    hexagonal): it asks the grid for each cell's polygon, center and
    "inradius", then paints the contents on top. If images are provided
    they are blitted for the bull / flag instead of the drawn shapes."""

    def __init__(self, mine_img=None, flag_img=None):
        self.mine = _Sprite(mine_img)
        self.flag = _Sprite(flag_img)

    def _draw_mine(self, screen, cx, cy, u):
        if not self.mine.blit(screen, cx, cy, int(u * 1.9)):
            self._bull(screen, cx, cy, u)

    def _draw_flag(self, screen, cx, cy, u):
        if not self.flag.blit(screen, cx, cy, int(u * 1.7)):
            self._flag(screen, cx, cy, u)

    def draw(self, screen, board, grid, ox, oy):
        s = grid.inradius()                       # half a cell; scales the contents
        font = pygame.font.SysFont("Arial", max(10, int(s * 1.5)), bold=True)

        for cell in grid.coords():
            t = board.tiles[cell]
            cx, cy = grid.center(*cell)
            cx += ox
            cy += oy
            # shrink the cell toward its center -> a thin, borderless gap
            poly = [(cx + (x + ox - cx) * CELL_GAP, cy + (y + oy - cy) * CELL_GAP)
                    for x, y in grid.polygon(*cell)]

            if not t.revealed:
                fill = CELL_COVER
            elif t.type == "X" and cell == board.detonated:
                fill = CELL_EXPLODE
            else:
                fill = CELL_REVEAL
            pygame.draw.polygon(screen, fill, poly)

            if t.flagged and not t.revealed:
                self._draw_flag(screen, cx, cy, s)
            elif t.revealed and t.wrong:
                self._draw_mine(screen, cx, cy, s)
                self._cross(screen, cx, cy, s)
            elif t.revealed and t.type == "X":
                self._draw_mine(screen, cx, cy, s)
            elif t.revealed and t.number > 0:
                surf = font.render(str(t.number), True, NUMBER_COLORS[t.number])
                screen.blit(surf, (cx - surf.get_width() / 2,
                                   cy - surf.get_height() / 2))

    @staticmethod
    def _curve(surf, color, p0, p1, p2, width, steps=16):
        """Draw a quadratic Bezier as a thick polyline."""
        pts = []
        for i in range(steps + 1):
            t = i / steps
            k = 1 - t
            pts.append((k * k * p0[0] + 2 * k * t * p1[0] + t * t * p2[0],
                        k * k * p0[1] + 2 * k * t * p1[1] + t * t * p2[1]))
        pygame.draw.lines(surf, color, False, pts, width)

    @classmethod
    def _bull(cls, s, cx, cy, u):
        """A Texas Longhorn (Bevo) head - the "mine"."""
        dark = UT_CHARCOAL
        w = max(2, int(u / 5))

        # Horns: sweep out from the top of the head and curl upward.
        for sd in (-1, 1):
            cls._curve(s, dark,
                       (cx + sd * u * 0.08, cy - u * 0.28),
                       (cx + sd * u * 0.85, cy - u * 0.02),
                       (cx + sd * u * 0.92, cy - u * 0.62), w)
            pygame.draw.circle(s, dark,
                               (int(cx + sd * u * 0.92), int(cy - u * 0.62)),
                               max(1, w // 2))

        # Ears, behind the head.
        for sd in (-1, 1):
            pygame.draw.circle(s, UT_ORANGE,
                               (int(cx + sd * u * 0.5), int(cy - u * 0.02)),
                               max(2, int(u * 0.17)))

        # Head (rounded muzzle) with a charcoal ring so it reads on any cell.
        head = pygame.Rect(0, 0, int(u * 0.92), int(u * 1.05))
        head.center = (int(cx), int(cy + u * 0.16))
        pygame.draw.ellipse(s, dark, head.inflate(w, w))
        pygame.draw.ellipse(s, UT_ORANGE, head)

        # Eyes and nostrils.
        for sd in (-1, 1):
            pygame.draw.circle(s, dark, (int(cx + sd * u * 0.24), int(cy - u * 0.04)),
                               max(1, int(u * 0.08)))
            pygame.draw.circle(s, dark, (int(cx + sd * u * 0.16), int(cy + u * 0.42)),
                               max(1, int(u * 0.09)))

    @staticmethod
    def _flag(s, cx, cy, u):
        w = max(2, int(u / 6))
        # charcoal pole + burnt-orange pennant
        pygame.draw.line(s, INK, (cx, cy - u * 0.55), (cx, cy + u * 0.55), w)
        pygame.draw.polygon(s, ACCENT,
                            [(cx, cy - u * 0.55), (cx, cy - u * 0.05),
                             (cx + u * 0.55, cy - u * 0.3)])
        pygame.draw.line(s, INK,
                         (cx - u * 0.45, cy + u * 0.55),
                         (cx + u * 0.45, cy + u * 0.55), w)

    @staticmethod
    def _cross(s, cx, cy, u):
        w = max(2, int(u / 5))
        pygame.draw.line(s, (193, 55, 43), (cx - u * 0.45, cy - u * 0.45),
                         (cx + u * 0.45, cy + u * 0.45), w)
        pygame.draw.line(s, (193, 55, 43), (cx - u * 0.45, cy + u * 0.45),
                         (cx + u * 0.45, cy - u * 0.45), w)


# ------------------------------------------------------------------------
# NUMERIC TEXT FIELD (for the menu)
# ------------------------------------------------------------------------
class NumberField:
    def __init__(self, rect, value, lo, hi):
        self.rect = pygame.Rect(rect)
        self.text = str(value)
        self.lo = lo
        self.hi = hi
        self.active = False

    def handle(self, event, pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit() and len(self.text) < 4:
                self.text += event.unicode

    def value(self):
        try:
            v = int(self.text)
        except ValueError:
            v = self.lo
        return max(self.lo, min(self.hi, v))

    def draw(self, screen, font):
        # minimal: just the number and a thin underline
        x = self.rect.x + 4 * SS
        if self.text:
            shown, col = self.text, INK
        else:
            shown, col = ("" if self.active else "0"), MUTED
        surf = font.render(shown, True, col)
        screen.blit(surf, (x, self.rect.centery - surf.get_height() // 2))
        pygame.draw.line(screen, ACCENT if self.active else (205, 200, 188),
                         (self.rect.x, self.rect.bottom),
                         (self.rect.right, self.rect.bottom), 2 * SS)
        # blinking text caret while this field is being edited
        if self.active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = x + (surf.get_width() if self.text else 0) + 2 * SS
            ch = font.get_height()
            pygame.draw.line(screen, INK, (cx, self.rect.centery - ch // 2),
                             (cx, self.rect.centery + ch // 2), 2 * SS)


# ------------------------------------------------------------------------
# GAME
# ------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 22 * SS, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 40 * SS, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 17 * SS)
        self._resize(560 * SS, 470 * SS)
        self.mine_img = load_image(MINE_IMAGE_NAMES)
        self.flag_img = load_image(FLAG_IMAGE_NAMES)

    def _resize(self, canvas_w, canvas_h):
        """Create the large canvas (where we draw) and the real window."""
        self.canvas_w, self.canvas_h = canvas_w, canvas_h
        self.screen = pygame.Surface((canvas_w, canvas_h))
        self.win = pygame.display.set_mode((round(canvas_w / SS),
                                            round(canvas_h / SS)))

    def _present(self):
        """Scale the canvas down to the window with smoothing and show it."""
        pygame.transform.smoothscale(self.screen, self.win.get_size(), self.win)
        pygame.display.flip()

    def _mouse(self, pos):
        """Convert a mouse position (window) to canvas coordinates."""
        return (pos[0] * SS, pos[1] * SS)

    # -- menu -------------------------------------------------------------
    def menu(self):
        W, H = 520 * SS, 470 * SS
        self._resize(W, H)
        mid = W // 2
        mode = "square"

        label_font = pygame.font.SysFont("Arial", 14 * SS)
        title_font = pygame.font.SysFont("Arial", 38 * SS, bold=True)
        title_lines = ["HOOK 'EM", "SWEEPER"]

        r_sq = pygame.Rect(0, 0, 150 * SS, 40 * SS)
        r_sq.center = (mid - 88 * SS, 158 * SS)
        r_hex = pygame.Rect(0, 0, 170 * SS, 40 * SS)
        r_hex.center = (mid + 92 * SS, 158 * SS)
        f_w = NumberField((mid + 12 * SS, 212 * SS, 66 * SS, 32 * SS), 12, MIN_DIM, MAX_DIM)
        f_h = NumberField((mid + 12 * SS, 256 * SS, 66 * SS, 32 * SS), 12, MIN_DIM, MAX_DIM)
        f_m = NumberField((mid + 12 * SS, 300 * SS, 66 * SS, 32 * SS), 30, 1, 999)
        btn_play = pygame.Rect(0, 0, 200 * SS, 52 * SS)
        btn_play.center = (mid, 388 * SS)

        while True:
            max_mines = max(1, f_w.value() * f_h.value() - 9)
            f_m.hi = max_mines
            mouse = self._mouse(pygame.mouse.get_pos())

            self.screen.fill(BG)
            ty = 30 * SS
            for i, line in enumerate(title_lines):
                col = ACCENT if i == 0 else INK
                surf = title_font.render(line, True, col)
                self.screen.blit(surf, (mid - surf.get_width() // 2, ty))
                ty += surf.get_height() - 6 * SS

            for key, text, rect in (("square", "Square", r_sq),
                                    ("hex", "Hexagonal", r_hex)):
                on = mode == key
                t = self.font.render(text, True, INK if on else MUTED)
                tx = rect.centerx - t.get_width() // 2
                self.screen.blit(t, (tx, rect.centery - t.get_height() // 2))
                if on:
                    uy = rect.centery + t.get_height() // 2 + 5 * SS
                    pygame.draw.line(self.screen, ACCENT,
                                     (tx, uy), (tx + t.get_width(), uy), 3 * SS)

            for text, field in ((f"WIDTH   {MIN_DIM}–{MAX_DIM}", f_w),
                                (f"HEIGHT   {MIN_DIM}–{MAX_DIM}", f_h),
                                (f"BULLS   1–{max_mines}", f_m)):
                lt = label_font.render(text, True, MUTED)
                self.screen.blit(lt, (mid - 16 * SS - lt.get_width(),
                                      field.rect.centery - lt.get_height() // 2))
                field.draw(self.screen, self.font)

            pygame.draw.rect(self.screen,
                             ACCENT_DIM if btn_play.collidepoint(mouse) else ACCENT,
                             btn_play, border_radius=btn_play.height // 2)
            pt = self.font.render("PLAY", True, BG)
            self.screen.blit(pt, (btn_play.centerx - pt.get_width() // 2,
                                  btn_play.centery - pt.get_height() // 2))
            self._present()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.quit()
                pos = self._mouse(event.pos) if event.type == pygame.MOUSEBUTTONDOWN else None
                for field in (f_w, f_h, f_m):
                    field.handle(event, pos)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if r_sq.collidepoint(pos):
                        mode = "square"
                    elif r_hex.collidepoint(pos):
                        mode = "hex"
                    elif btn_play.collidepoint(pos):
                        return {"mode": mode, "cols": f_w.value(),
                                "rows": f_h.value(), "mines": f_m.value()}
            self.clock.tick(FPS)

    # -- a game round --------------------------------------------------
    def new(self, cfg):
        if cfg["mode"] == "square":
            self.grid = SquareGrid(cfg["cols"], cfg["rows"])
        else:
            self.grid = HexGrid(cfg["cols"], cfg["rows"])
        self.renderer = CellRenderer(self.mine_img, self.flag_img)

        self.board = Board(self.grid, cfg["mines"])
        gw, gh = self.grid.pixel_size()
        canvas_w = max(MIN_WIN_W, gw)
        self.ox = (canvas_w - gw) // 2
        self.oy = HUD_HEIGHT
        self._resize(canvas_w, gh + HUD_HEIGHT)
        self.start_time = None
        self.elapsed = 0
        self.state = "playing"

    def run(self):
        while self.state == "playing":
            self.clock.tick(FPS)
            self.events()
            if self.start_time is not None:
                self.elapsed = int(time.time() - self.start_time)
            self.draw()
        self.end_screen()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                if event.key == pygame.K_r:
                    self.state = "restart"
                    return
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = self._mouse(event.pos)
                cell = self.grid.cell_at(mx - self.ox, my - self.oy)
                if cell is None:
                    continue
                tile = self.board.tiles[cell]

                if event.button == 1 and not tile.flagged and not tile.revealed:
                    if self.start_time is None:
                        self.start_time = time.time()
                    if not self.board.dig(cell):
                        self.board.reveal_all_mines()
                        self.state = "lost"
                        return
                elif event.button == 3 and not tile.revealed:
                    tile.flagged = not tile.flagged

                if self.board.is_won():
                    for t in self.board.tiles.values():
                        if t.type == "X":
                            t.flagged = True
                    self.state = "won"
                    return

    # -- drawing -----------------------------------------------------
    def draw_hud(self):
        # no bar: same paper color, one faint divider line
        bulls_left = self.board.mines - self.board.flags_used()
        left = self.font.render(f"Bulls  {bulls_left}", True, INK)
        right = self.small_font.render(f"{self.elapsed}s", True, MUTED)
        hint = self.small_font.render("R", True, MUTED)
        cy = HUD_HEIGHT // 2
        self.screen.blit(left, (16 * SS, cy - left.get_height() // 2))
        self.screen.blit(right, (self.canvas_w - right.get_width() - 16 * SS,
                                 cy - right.get_height() // 2))
        self.screen.blit(hint, (self.canvas_w // 2 - hint.get_width() // 2,
                                cy - hint.get_height() // 2))
        pygame.draw.line(self.screen, (214, 209, 197),
                         (0, HUD_HEIGHT - SS), (self.canvas_w, HUD_HEIGHT - SS), SS)

    def _render_board(self):
        """Draw the board onto the canvas (without showing it yet)."""
        self.screen.fill(BGCOLOUR)
        self.draw_hud()
        self.renderer.draw(self.screen, self.board, self.grid, self.ox, self.oy)

    def draw(self):
        self._render_board()
        self._present()

    def end_screen(self):
        if self.state == "restart":
            return
        won = self.state == "won"
        msg = self.big_font.render("YOU WIN" if won else "GAME OVER", True,
                                   GREEN if won else RED)
        sub = self.font.render(f"Time: {self.elapsed}s", True, WHITE)
        tip = self.small_font.render("R: play again", True, WHITE)
        cx = self.screen.get_width() // 2
        cy = self.screen.get_height() // 2

        # Composed once: board + dark overlay + text.
        self._render_board()
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        self.screen.blit(msg, (cx - msg.get_width() // 2, cy - 70 * SS))
        self.screen.blit(sub, (cx - sub.get_width() // 2, cy - 10 * SS))
        self.screen.blit(tip, (cx - tip.get_width() // 2, cy + 30 * SS))

        while True:
            self._present()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit()
                    if event.key == pygame.K_r:
                        return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    return
            self.clock.tick(FPS)

    def quit(self):
        pygame.quit()
        sys.exit(0)


def main():
    game = Game()
    while True:
        cfg = game.menu()
        game.new(cfg)
        game.run()


if __name__ == "__main__":
    main()
