"""
MINESWEEPER - Introduction to Programming Project

This program implements a graphical version of the classic Minesweeper game
using Pygame for the interface and NumPy for storing the internal game board.

How the game works:
    - The player first picks a board size from a menu.
    - The player is then shown a grid of covered cells.
    - A number of mines are hidden randomly under some of the cells.
    - The player clicks a cell to "select" it.
        - If the cell has a mine, the game ends immediately (GAME OVER).
        - If the cell is safe, it shows how many mines are touching it
          (the eight neighboring cells: up, down, left, right, and the
          four diagonals). If it has zero neighboring mines, all of its
          connected neighbors are revealed automatically as well.
    - The player wins by revealing every safe cell without clicking a mine.
    - The player can right-click (or Control-click on Mac) a covered cell
      to place or remove a flag as a reminder of where a mine might be.
    - The window can be freely resized; the whole interface scales to fit.

AUTHORS:
    - Gio
    - <Your Name Here>
"""

import math
import random
import sys

import numpy as np
import pygame


# ------------------------------------------------------------------------
# GAME SETTINGS
# ------------------------------------------------------------------------
# The available board sizes the player can pick from the menu. "mines" is
# chosen at roughly 15-20% of the cells so difficulty scales with size.
DIFFICULTY_OPTIONS = [
    {"label": "Small  (5 x 5)  -  5 mines", "size": 5, "mines": 5},
    {"label": "Medium (8 x 8)  -  10 mines", "size": 8, "mines": 10},
    {"label": "Large  (10 x 10)  -  18 mines", "size": 10, "mines": 18},
    {"label": "Extra Large (12 x 12)  -  28 mines", "size": 12, "mines": 28},
]

BOARD_SIZE = DIFFICULTY_OPTIONS[0]["size"]        # Set by choose_difficulty()
NUMBER_OF_MINES = DIFFICULTY_OPTIONS[0]["mines"]  # Set by choose_difficulty()

MINE_VALUE = -1          # How a mine is represented inside the NumPy array

# ------------------------------------------------------------------------
# VISUAL SETTINGS
# ------------------------------------------------------------------------
# The BASE_* values are the "design size" of the interface, in pixels, at
# a scale of 1.0. Since the window is resizable, compute_layout() and
# compute_menu_layout() scale every one of them by the current scale
# factor to get the actual sizes used for drawing that frame.
BASE_CELL_SIZE = 60
BASE_CELL_GAP = 3
BASE_BOARD_PADDING = 10
BASE_MARGIN = 24
BASE_SECTION_GAP = 10

BASE_TITLE_HEIGHT = 46
BASE_SUBTITLE_HEIGHT = 40
BASE_INFO_HEIGHT = 32
BASE_STATUS_HEIGHT = 28
BASE_BUTTON_WIDTH = 150
BASE_BUTTON_HEIGHT = 42
BASE_BUTTON_GAP = 14

BASE_MENU_BUTTON_WIDTH = 340
BASE_MENU_BUTTON_HEIGHT = 50
BASE_MENU_BUTTON_GAP = 16

BASE_TITLE_FONT_SIZE = 30
BASE_SUBTITLE_FONT_SIZE = 14
BASE_INFO_FONT_SIZE = 16
BASE_CELL_FONT_SIZE = 20
BASE_STATUS_FONT_SIZE = 15

# How far the player is allowed to shrink/grow the window relative to
# the design size.
MIN_SCALE = 0.6
MAX_SCALE = 2.5

BG_COLOR = (44, 62, 80)             # Main window background (dark navy)
PANEL_COLOR = (52, 73, 94)          # Board frame background
COVERED_COLOR = (93, 173, 226)      # Covered (unrevealed) cell color
REVEALED_COLOR = (236, 240, 241)    # Revealed (safe) cell color
FLAG_COLOR = (244, 208, 63)         # Flagged cell color
MINE_COLOR = (231, 76, 60)          # Mine cell color (shown at game over)
LOSING_MINE_COLOR = (192, 57, 43)   # The exact mine that was clicked
TEXT_COLOR = (236, 240, 241)        # Light text on dark background
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BORDER_COLOR = (30, 42, 55)

BUTTON_COLOR = (39, 174, 96)
BUTTON_HOVER_COLOR = (46, 204, 113)
SECONDARY_BUTTON_COLOR = (93, 173, 226)
SECONDARY_BUTTON_HOVER_COLOR = (133, 193, 233)

# Text color used for each mine-count number, matching classic Minesweeper.
NUMBER_COLORS = {
    1: (41, 128, 185),    # blue
    2: (39, 174, 96),     # green
    3: (192, 57, 43),     # red
    4: (142, 68, 173),    # purple
    5: (127, 140, 141),   # gray
    6: (22, 160, 133),    # teal
    7: (44, 62, 80),      # dark navy
    8: (0, 0, 0),         # black
}

# ------------------------------------------------------------------------
# GLOBAL GAME STATE
# ------------------------------------------------------------------------
# These variables hold the current state of the game. They are updated by
# the functions below every time the player interacts with the board.
#
# board:      NumPy 2D array of integers.
#             -1 means "this cell has a mine".
#             0-8 means "this cell is safe and touches this many mines".
# revealed:   2D list of True/False. True means the player has already
#             uncovered that cell.
# flagged:    2D list of True/False. True means the player marked that
#             cell with a flag.
# mine_hit:   (row, col) of the mine that ended the game, or None.
# game_over:  True once the player has won or lost. Used to ignore clicks
#             after the game has ended.
board = None
revealed = None
flagged = None
mine_hit = None
game_over = False
status_message = "Good luck!"

# Current (scaled) pixel sizes and screen positions. These start out
# equal to the BASE_* design values and are recomputed every frame by
# compute_layout() / compute_menu_layout() according to how much the
# player has resized the window.
CELL_SIZE = BASE_CELL_SIZE
CELL_GAP = BASE_CELL_GAP
BOARD_PADDING = BASE_BOARD_PADDING
MARGIN = BASE_MARGIN
SECTION_GAP = BASE_SECTION_GAP
TITLE_HEIGHT = BASE_TITLE_HEIGHT
SUBTITLE_HEIGHT = BASE_SUBTITLE_HEIGHT
INFO_HEIGHT = BASE_INFO_HEIGHT
STATUS_HEIGHT = BASE_STATUS_HEIGHT
BUTTON_WIDTH = BASE_BUTTON_WIDTH
BUTTON_HEIGHT = BASE_BUTTON_HEIGHT
BUTTON_GAP = BASE_BUTTON_GAP

# Screen coordinates of the top-left corner of the first cell, and the
# total size of the drawable content area. Computed by compute_layout()
# and reused whenever we need to draw a cell or figure out which cell
# the player clicked.
board_origin = (0, 0)
new_game_button_rect = None
change_size_button_rect = None
content_width = 0
content_height = 0

# The equivalent layout information for the difficulty-selection menu.
menu_title_pos = (0, 0)
menu_subtitle_pos = (0, 0)
menu_option_rects = []
menu_content_width = 0
menu_content_height = 0


# ------------------------------------------------------------------------
# BOARD CREATION
# ------------------------------------------------------------------------
def create_board(size):
    """
    Create an empty size x size NumPy array filled with zeros.
    Every cell starts as "0 nearby mines" until mines are placed and
    the neighboring mine counts are calculated.
    """
    new_board = np.zeros((size, size), dtype=int)
    return new_board


def place_mines(board, size, num_mines):
    """
    Randomly choose num_mines unique positions on the board and mark
    them as mines using MINE_VALUE (-1).

    We build a list of every possible (row, col) position, then use
    random.sample to pick num_mines of them without repeats.
    """
    all_positions = []
    for row in range(size):
        for col in range(size):
            all_positions.append((row, col))

    mine_positions = random.sample(all_positions, num_mines)

    for (row, col) in mine_positions:
        board[row][col] = MINE_VALUE

    return mine_positions


def count_adjacent_mines(board, size):
    """
    Fill in the number of neighboring mines for every safe cell.

    For each cell that is NOT a mine, we look at its eight possible
    neighbors (up, down, left, right, and the four diagonals) and count
    how many of them contain a mine. That count is stored in the cell.

    Cells that are mines are left unchanged (they stay as MINE_VALUE).
    """
    for row in range(size):
        for col in range(size):
            if board[row][col] == MINE_VALUE:
                continue  # Skip mines; they don't need a neighbor count

            mine_count = 0
            for row_offset in [-1, 0, 1]:
                for col_offset in [-1, 0, 1]:
                    if row_offset == 0 and col_offset == 0:
                        continue  # Skip the cell itself

                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset

                    # Stay inside the board (important at edges/corners)
                    if 0 <= neighbor_row < size and 0 <= neighbor_col < size:
                        if board[neighbor_row][neighbor_col] == MINE_VALUE:
                            mine_count += 1

            board[row][col] = mine_count


# ------------------------------------------------------------------------
# GAME LOGIC
# ------------------------------------------------------------------------
def check_win():
    """
    Check whether the player has won the game.

    The player wins when every SAFE cell has been revealed:

        revealed_safe_cells == total_cells - number_of_mines

    Returns True if the win condition is met, otherwise False.
    """
    revealed_safe_cells = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if revealed[row][col]:
                revealed_safe_cells += 1

    total_cells = BOARD_SIZE * BOARD_SIZE
    return revealed_safe_cells == total_cells - NUMBER_OF_MINES


def flood_reveal(row, col):
    """
    Reveal the cell at (row, col). If it has zero neighboring mines,
    this is the classic Minesweeper "flood fill": we keep revealing its
    neighbors outward, since a 0 means none of them can be a mine
    either. The expansion stops as soon as it reaches a numbered cell.
    Flagged cells are left untouched.
    """
    cells_to_check = [(row, col)]

    while cells_to_check:
        current_row, current_col = cells_to_check.pop()

        if revealed[current_row][current_col] or flagged[current_row][current_col]:
            continue

        revealed[current_row][current_col] = True

        if board[current_row][current_col] != 0:
            continue  # Only cells with 0 nearby mines expand further

        for row_offset in [-1, 0, 1]:
            for col_offset in [-1, 0, 1]:
                if row_offset == 0 and col_offset == 0:
                    continue

                neighbor_row = current_row + row_offset
                neighbor_col = current_col + col_offset

                if 0 <= neighbor_row < BOARD_SIZE and 0 <= neighbor_col < BOARD_SIZE:
                    if not revealed[neighbor_row][neighbor_col]:
                        cells_to_check.append((neighbor_row, neighbor_col))


def on_left_click(row, col):
    """
    Handle a left-click on the cell at (row, col).

    - Ignored if the game has already ended, the cell is flagged, or the
      cell is already revealed (a cell cannot be selected twice).
    - If the cell is a mine: end the game (loss) and remember which mine.
    - If the cell is safe: reveal it (and any connected safe cells) and
      check if the player has won.
    """
    global game_over, mine_hit, status_message

    if game_over or flagged[row][col] or revealed[row][col]:
        return  # Invalid selection: do nothing

    if board[row][col] == MINE_VALUE:
        mine_hit = (row, col)
        game_over = True
        status_message = "Game over! You hit a mine."
    else:
        flood_reveal(row, col)
        if check_win():
            game_over = True
            status_message = "Congratulations, YOU WIN!"
        else:
            status_message = "Safe cell!"


def on_right_click(row, col):
    """
    Handle a right-click (or Control-click) on the cell at (row, col):
    toggle a flag on or off. Flags mark cells the player suspects
    contain a mine, and cannot be placed on already-revealed cells.
    """
    if game_over or revealed[row][col]:
        return  # Invalid selection: do nothing

    flagged[row][col] = not flagged[row][col]


def count_flags():
    """Count how many cells are currently flagged."""
    flag_total = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if flagged[row][col]:
                flag_total += 1
    return flag_total


def choose_difficulty(option):
    """
    Apply the chosen board size/mine count and start a brand new game.
    `option` is one of the dictionaries in DIFFICULTY_OPTIONS.
    """
    global BOARD_SIZE, NUMBER_OF_MINES

    BOARD_SIZE = option["size"]
    NUMBER_OF_MINES = option["mines"]
    reset_game()


def reset_game():
    """
    Start a brand new game at the current BOARD_SIZE / NUMBER_OF_MINES:
    create a fresh board, place new mines, recalculate neighbor counts,
    and clear the revealed/flagged state.
    """
    global board, revealed, flagged, game_over, mine_hit, status_message

    board = create_board(BOARD_SIZE)
    place_mines(board, BOARD_SIZE, NUMBER_OF_MINES)
    count_adjacent_mines(board, BOARD_SIZE)

    revealed = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    flagged = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    game_over = False
    mine_hit = None
    status_message = "Good luck!"


# ------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------
def compute_layout(scale):
    """
    Recompute every pixel size and screen position of the GAME screen
    for the given scale factor, so the whole interface grows or shrinks
    smoothly as the player resizes the window. Returns the (width,
    height) of the drawable content area at that scale.
    """
    global CELL_SIZE, CELL_GAP, BOARD_PADDING, MARGIN, SECTION_GAP
    global TITLE_HEIGHT, SUBTITLE_HEIGHT, INFO_HEIGHT, STATUS_HEIGHT
    global BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_GAP
    global board_origin, new_game_button_rect, change_size_button_rect
    global title_pos, subtitle_pos, info_y, panel_rect, status_pos
    global content_width, content_height

    def scaled(value):
        return max(1, round(value * scale))

    CELL_SIZE = scaled(BASE_CELL_SIZE)
    CELL_GAP = scaled(BASE_CELL_GAP)
    BOARD_PADDING = scaled(BASE_BOARD_PADDING)
    MARGIN = scaled(BASE_MARGIN)
    SECTION_GAP = scaled(BASE_SECTION_GAP)
    TITLE_HEIGHT = scaled(BASE_TITLE_HEIGHT)
    SUBTITLE_HEIGHT = scaled(BASE_SUBTITLE_HEIGHT)
    INFO_HEIGHT = scaled(BASE_INFO_HEIGHT)
    STATUS_HEIGHT = scaled(BASE_STATUS_HEIGHT)
    BUTTON_WIDTH = scaled(BASE_BUTTON_WIDTH)
    BUTTON_HEIGHT = scaled(BASE_BUTTON_HEIGHT)
    BUTTON_GAP = scaled(BASE_BUTTON_GAP)

    board_pixels = BOARD_SIZE * CELL_SIZE + (BOARD_SIZE - 1) * CELL_GAP
    panel_size = board_pixels + 2 * BOARD_PADDING

    buttons_width = 2 * BUTTON_WIDTH + BUTTON_GAP
    window_width = max(panel_size + 2 * MARGIN, buttons_width + 2 * MARGIN)

    y = MARGIN
    title_pos = (window_width // 2, y + TITLE_HEIGHT // 2)
    y += TITLE_HEIGHT

    subtitle_pos = (window_width // 2, y + SUBTITLE_HEIGHT // 2)
    y += SUBTITLE_HEIGHT + SECTION_GAP

    info_y = y
    y += INFO_HEIGHT + SECTION_GAP

    panel_rect = pygame.Rect((window_width - panel_size) // 2, y, panel_size, panel_size)
    board_origin = (panel_rect.x + BOARD_PADDING, panel_rect.y + BOARD_PADDING)
    y += panel_size + SECTION_GAP

    status_pos = (window_width // 2, y + STATUS_HEIGHT // 2)
    y += STATUS_HEIGHT + SECTION_GAP

    buttons_start_x = (window_width - buttons_width) // 2
    new_game_button_rect = pygame.Rect(buttons_start_x, y, BUTTON_WIDTH, BUTTON_HEIGHT)
    change_size_button_rect = pygame.Rect(
        buttons_start_x + BUTTON_WIDTH + BUTTON_GAP, y, BUTTON_WIDTH, BUTTON_HEIGHT
    )
    y += BUTTON_HEIGHT + MARGIN

    content_width, content_height = window_width, y
    return content_width, content_height


def compute_menu_layout(scale):
    """
    Recompute every pixel size and screen position of the difficulty
    MENU for the given scale factor. Returns the (width, height) of the
    drawable content area at that scale.
    """
    global menu_title_pos, menu_subtitle_pos, menu_option_rects
    global menu_content_width, menu_content_height

    def scaled(value):
        return max(1, round(value * scale))

    margin = scaled(BASE_MARGIN)
    title_height = scaled(BASE_TITLE_HEIGHT)
    subtitle_height = scaled(BASE_SUBTITLE_HEIGHT)
    section_gap = scaled(BASE_SECTION_GAP)
    button_width = scaled(BASE_MENU_BUTTON_WIDTH)
    button_height = scaled(BASE_MENU_BUTTON_HEIGHT)
    button_gap = scaled(BASE_MENU_BUTTON_GAP)

    window_width = button_width + 2 * margin

    y = margin
    menu_title_pos = (window_width // 2, y + title_height // 2)
    y += title_height

    menu_subtitle_pos = (window_width // 2, y + subtitle_height // 2)
    y += subtitle_height + section_gap

    menu_option_rects = []
    for _ in DIFFICULTY_OPTIONS:
        rect = pygame.Rect((window_width - button_width) // 2, y, button_width, button_height)
        menu_option_rects.append(rect)
        y += button_height + button_gap

    y += margin - button_gap  # Replace the last button's gap with the bottom margin

    menu_content_width, menu_content_height = window_width, y
    return menu_content_width, menu_content_height


def compute_scale(screen_size, base_width, base_height):
    """
    Work out how much to scale the interface so it fits the current
    window size, without distorting its proportions.
    """
    width_ratio = screen_size[0] / base_width
    height_ratio = screen_size[1] / base_height
    scale = min(width_ratio, height_ratio)
    return max(MIN_SCALE, min(MAX_SCALE, scale))


def initial_scale_for(base_width, base_height):
    """
    Pick a starting scale so the initial window comfortably fits the
    player's screen, even for the larger board sizes.
    """
    display_info = pygame.display.Info()
    max_width = display_info.current_w * 0.85
    max_height = display_info.current_h * 0.85
    scale = min(1.0, max_width / base_width, max_height / base_height)
    return max(MIN_SCALE, min(MAX_SCALE, scale))


def get_cell_rect(row, col):
    """Return the pygame.Rect occupied by the cell at (row, col)."""
    step = CELL_SIZE + CELL_GAP
    x = board_origin[0] + col * step
    y = board_origin[1] + row * step
    return pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)


def get_cell_at_pos(pos):
    """
    Translate a content-area position into a (row, col) board
    coordinate. Returns None if the position is outside the grid or in
    the small gap between two cells.
    """
    x, y = pos
    step = CELL_SIZE + CELL_GAP

    rel_x = x - board_origin[0]
    rel_y = y - board_origin[1]
    if rel_x < 0 or rel_y < 0:
        return None

    col = rel_x // step
    row = rel_y // step
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        return None

    if (rel_x % step) >= CELL_SIZE or (rel_y % step) >= CELL_SIZE:
        return None  # Clicked in the gap between cells

    return int(row), int(col)


# ------------------------------------------------------------------------
# DRAWING HELPERS
# ------------------------------------------------------------------------
def shade(color, amount):
    """Return `color` shifted lighter (positive amount) or darker (negative)."""
    return tuple(max(0, min(255, channel + amount)) for channel in color)


def draw_raised_cell(surface, rect, color):
    """Draw a covered cell with a simple beveled (3D) look."""
    pygame.draw.rect(surface, color, rect)
    light = shade(color, 45)
    dark = shade(color, -45)
    pygame.draw.line(surface, light, rect.topleft, (rect.right - 1, rect.top), 2)
    pygame.draw.line(surface, light, rect.topleft, (rect.left, rect.bottom - 1), 2)
    pygame.draw.line(surface, dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 2)
    pygame.draw.line(surface, dark, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1), 2)


def draw_mine_icon(surface, rect):
    """Draw a simple mine (a spiked ball). No emoji involved."""
    center = rect.center
    radius = min(rect.width, rect.height) // 4

    for angle_degrees in range(0, 360, 45):
        angle = math.radians(angle_degrees)
        end_point = (
            center[0] + int(radius * 1.7 * math.cos(angle)),
            center[1] + int(radius * 1.7 * math.sin(angle)),
        )
        pygame.draw.line(surface, BLACK, center, end_point, 2)

    pygame.draw.circle(surface, BLACK, center, radius)
    highlight = (center[0] - radius // 3, center[1] - radius // 3)
    pygame.draw.circle(surface, WHITE, highlight, max(1, radius // 4))


def draw_flag_icon(surface, rect):
    """Draw a simple flag on a pole. No emoji involved."""
    pole_x = rect.left + rect.width // 3
    pole_top = rect.top + rect.height // 5
    pole_bottom = rect.bottom - rect.height // 5

    pygame.draw.line(surface, BLACK, (pole_x, pole_top), (pole_x, pole_bottom), 3)
    pygame.draw.line(
        surface, BLACK,
        (pole_x - rect.width // 5, pole_bottom),
        (pole_x + rect.width // 5, pole_bottom),
        3,
    )

    flag_points = [
        (pole_x, pole_top),
        (pole_x + rect.width // 3, pole_top + rect.height // 6),
        (pole_x, pole_top + rect.height // 3),
    ]
    pygame.draw.polygon(surface, LOSING_MINE_COLOR, flag_points)


def draw_text(surface, font, text, color, center):
    """Render `text` with `font` and blit it centered at `center`."""
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, text_surface.get_rect(center=center))


# ------------------------------------------------------------------------
# MAIN DRAWING ROUTINE
# ------------------------------------------------------------------------
def draw_cell(surface, fonts, row, col):
    """Draw a single cell according to the current game state."""
    rect = get_cell_rect(row, col)
    value = board[row][col]
    is_mine = value == MINE_VALUE

    if game_over and is_mine:
        color = LOSING_MINE_COLOR if mine_hit == (row, col) else MINE_COLOR
        pygame.draw.rect(surface, color, rect)
        draw_mine_icon(surface, rect)
    elif revealed[row][col]:
        pygame.draw.rect(surface, REVEALED_COLOR, rect)
        if value > 0:
            draw_text(surface, fonts["cell"], str(value), NUMBER_COLORS.get(value, BLACK), rect.center)
    else:
        base_color = FLAG_COLOR if flagged[row][col] else COVERED_COLOR
        draw_raised_cell(surface, rect, base_color)
        if flagged[row][col]:
            draw_flag_icon(surface, rect)

    pygame.draw.rect(surface, BORDER_COLOR, rect, 1)


def draw_buttons(surface, fonts, mouse_pos):
    """Draw the 'New Game' and 'Change Size' buttons, highlighting hovered ones."""
    is_hovered = new_game_button_rect.collidepoint(mouse_pos)
    color = BUTTON_HOVER_COLOR if is_hovered else BUTTON_COLOR
    pygame.draw.rect(surface, color, new_game_button_rect, border_radius=8)
    draw_text(surface, fonts["info"], "New Game", WHITE, new_game_button_rect.center)

    is_hovered = change_size_button_rect.collidepoint(mouse_pos)
    color = SECONDARY_BUTTON_HOVER_COLOR if is_hovered else SECONDARY_BUTTON_COLOR
    pygame.draw.rect(surface, color, change_size_button_rect, border_radius=8)
    draw_text(surface, fonts["info"], "Change Size", WHITE, change_size_button_rect.center)


def draw_window(surface, fonts, mouse_pos):
    """Draw the entire game content area: title, info bar, board, status, buttons."""
    surface.fill(BG_COLOR)

    draw_text(surface, fonts["title"], "MINESWEEPER", TEXT_COLOR, title_pos)
    draw_text(
        surface, fonts["subtitle"],
        "Left click: Reveal a cell   |   Right click / Control-click: Place a flag",
        TEXT_COLOR, subtitle_pos,
    )

    window_width = surface.get_width()
    draw_text(
        surface, fonts["info"], "Mines: " + str(NUMBER_OF_MINES), TEXT_COLOR,
        (window_width // 2 - 90, info_y + INFO_HEIGHT // 2),
    )
    draw_text(
        surface, fonts["info"], "Flags: " + str(count_flags()), TEXT_COLOR,
        (window_width // 2 + 90, info_y + INFO_HEIGHT // 2),
    )

    pygame.draw.rect(surface, PANEL_COLOR, panel_rect, border_radius=6)
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            draw_cell(surface, fonts, row, col)

    draw_text(surface, fonts["status"], status_message, TEXT_COLOR, status_pos)
    draw_buttons(surface, fonts, mouse_pos)


def draw_menu(surface, fonts, mouse_pos):
    """Draw the difficulty-selection menu: title, subtitle, and size buttons."""
    surface.fill(BG_COLOR)

    draw_text(surface, fonts["title"], "MINESWEEPER", TEXT_COLOR, menu_title_pos)
    draw_text(
        surface, fonts["subtitle"], "Choose a board size to begin",
        TEXT_COLOR, menu_subtitle_pos,
    )

    for option, rect in zip(DIFFICULTY_OPTIONS, menu_option_rects):
        is_hovered = rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER_COLOR if is_hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, rect, border_radius=8)
        draw_text(surface, fonts["info"], option["label"], WHITE, rect.center)


def build_fonts(scale):
    """Build every font used by the UI, sized for the given scale factor."""
    def size(base_size):
        return max(8, round(base_size * scale))

    return {
        "title": pygame.font.SysFont("helvetica", size(BASE_TITLE_FONT_SIZE), bold=True),
        "subtitle": pygame.font.SysFont("helvetica", size(BASE_SUBTITLE_FONT_SIZE)),
        "info": pygame.font.SysFont("helvetica", size(BASE_INFO_FONT_SIZE), bold=True),
        "cell": pygame.font.SysFont("helvetica", size(BASE_CELL_FONT_SIZE), bold=True),
        "status": pygame.font.SysFont("helvetica", size(BASE_STATUS_FONT_SIZE), italic=True),
    }


# ------------------------------------------------------------------------
# PROGRAM ENTRY POINT
# ------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Minesweeper")

    menu_base_width, menu_base_height = compute_menu_layout(1.0)
    initial_scale = initial_scale_for(menu_base_width, menu_base_height)
    screen = pygame.display.set_mode(
        compute_menu_layout(initial_scale), pygame.RESIZABLE
    )

    app_state = "menu"          # "menu" while picking a size, "game" while playing
    base_width, base_height = menu_base_width, menu_base_height
    current_scale = initial_scale
    fonts = build_fonts(current_scale)

    clock = pygame.time.Clock()
    running = True
    while running:
        # Recompute the layout every frame so resizing the window feels
        # instantaneous. Fonts are only rebuilt when the scale actually
        # changes, since font creation is comparatively expensive.
        scale = compute_scale(screen.get_size(), base_width, base_height)
        if abs(scale - current_scale) > 0.01:
            current_scale = scale
            fonts = build_fonts(current_scale)

        if app_state == "menu":
            content_width, content_height = compute_menu_layout(current_scale)
        else:
            content_width, content_height = compute_layout(current_scale)

        # The content area is centered inside the window and letterboxed
        # (rather than stretched) so cells and buttons always stay
        # correctly proportioned.
        offset = (
            (screen.get_width() - content_width) // 2,
            (screen.get_height() - content_height) // 2,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                content_pos = (event.pos[0] - offset[0], event.pos[1] - offset[1])

                if app_state == "menu":
                    for option, rect in zip(DIFFICULTY_OPTIONS, menu_option_rects):
                        if rect.collidepoint(content_pos):
                            choose_difficulty(option)
                            base_width, base_height = compute_layout(1.0)
                            initial_scale = initial_scale_for(base_width, base_height)
                            current_scale = initial_scale
                            fonts = build_fonts(current_scale)
                            screen = pygame.display.set_mode(
                                compute_layout(initial_scale), pygame.RESIZABLE
                            )
                            app_state = "game"
                            break
                else:
                    if new_game_button_rect.collidepoint(content_pos):
                        reset_game()
                        continue

                    if change_size_button_rect.collidepoint(content_pos):
                        base_width, base_height = menu_base_width, menu_base_height
                        initial_scale = initial_scale_for(base_width, base_height)
                        current_scale = initial_scale
                        fonts = build_fonts(current_scale)
                        screen = pygame.display.set_mode(
                            compute_menu_layout(initial_scale), pygame.RESIZABLE
                        )
                        app_state = "menu"
                        continue

                    cell = get_cell_at_pos(content_pos)
                    if cell is None:
                        continue
                    row, col = cell

                    control_held = pygame.key.get_mods() & pygame.KMOD_CTRL
                    if event.button == 1 and not control_held:
                        on_left_click(row, col)
                    elif event.button == 3 or (event.button == 1 and control_held):
                        on_right_click(row, col)

        content_surface = pygame.Surface((content_width, content_height))
        mouse_pos = pygame.mouse.get_pos()
        content_mouse_pos = (mouse_pos[0] - offset[0], mouse_pos[1] - offset[1])

        if app_state == "menu":
            draw_menu(content_surface, fonts, content_mouse_pos)
        else:
            draw_window(content_surface, fonts, content_mouse_pos)

        screen.fill(BG_COLOR)
        screen.blit(content_surface, offset)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
