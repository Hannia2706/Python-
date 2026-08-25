"""
================================================================================
 MINESWEEPER - Introduction to Programming Project
================================================================================
This program implements a graphical version of the classic Minesweeper game
using Python's Tkinter library for the interface and NumPy for storing the
internal game board.

How the game works:
    - The player is shown a grid of covered cells (buttons).
    - A number of mines are hidden randomly under some of the cells.
    - The player clicks a cell to "select" it.
        - If the cell has a mine, the game ends immediately (GAME OVER).
        - If the cell is safe, it shows how many mines are touching it
          (the eight neighboring cells: up, down, left, right, and the
          four diagonals).
    - The player wins by revealing every safe cell without clicking a mine.
    - The player can right-click (or Control-click on Mac) a covered cell
      to place or remove a flag as a reminder of where a mine might be.

AUTHORS:
    - <Your Name Here>
    - <Your Name Here>

================================================================================
"""

import tkinter as tk
from tkinter import messagebox
import random
import numpy as np


# ------------------------------------------------------------------------
# GAME SETTINGS
# ------------------------------------------------------------------------
BOARD_SIZE = 5           # The board is BOARD_SIZE x BOARD_SIZE (5x5)
NUMBER_OF_MINES = 5      # How many mines are hidden on the board

MINE_VALUE = -1          # How a mine is represented inside the NumPy array

# ------------------------------------------------------------------------
# VISUAL SETTINGS
# ------------------------------------------------------------------------
# Keeping all colors/fonts in one place makes the interface easy to
# re-theme without touching the game logic below.
CELL_SIZE = 3                       # Button width/height, in text units
BG_COLOR = "#2c3e50"                # Main window background (dark navy)
PANEL_COLOR = "#34495e"             # Board frame background
COVERED_COLOR = "#5dade2"           # Covered (unrevealed) cell color
REVEALED_COLOR = "#ecf0f1"          # Revealed (safe) cell color
FLAG_COLOR = "#f4d03f"              # Flagged cell color
MINE_COLOR = "#e74c3c"              # Mine cell color (shown at game over)
LOSING_MINE_COLOR = "#c0392b"       # The exact mine that was clicked
TEXT_COLOR = "#ecf0f1"              # Light text on dark background
FONT_TITLE = ("Helvetica", 26, "bold")
FONT_SUBTITLE = ("Helvetica", 11)
FONT_INFO = ("Helvetica", 13, "bold")
FONT_CELL = ("Helvetica", 14, "bold")
FONT_STATUS = ("Helvetica", 12, "italic")

# Text color used for each mine-count number, matching classic Minesweeper.
NUMBER_COLORS = {
    1: "#2980b9",   # blue
    2: "#27ae60",   # green
    3: "#c0392b",   # red
    4: "#8e44ad",   # purple
    5: "#7f8c8d",   # gray
    6: "#16a085",   # teal
    7: "#2c3e50",   # dark navy
    8: "#000000",   # black
}

FLAG_SYMBOL = "\U0001F6A9"   # flag emoji
MINE_SYMBOL = "\U0001F4A3"   # bomb emoji

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
# buttons:    2D list holding the actual Tkinter Button widgets so we can
#             change their text/color when the game state changes.
# game_over:  True once the player has won or lost. Used to ignore clicks
#             after the game has ended.
board = None
revealed = None
flagged = None
buttons = None
game_over = False


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
def reveal_cell(row, col):
    """
    Reveal the cell at (row, col): update the button's text/appearance
    and mark it as revealed. Called after a left-click on a covered,
    unflagged cell.
    """
    revealed[row][col] = True
    value = board[row][col]

    button = buttons[row][col]
    button.config(
        relief=tk.SUNKEN,
        state="disabled",
        bg=REVEALED_COLOR,
        disabledforeground=NUMBER_COLORS.get(value, "black"),
    )

    if value == 0:
        button.config(text="")  # No mines nearby: leave the cell blank
    else:
        button.config(text=str(value))


def reveal_all_mines():
    """
    Show every mine on the board. Called when the player loses so they
    can see where all the mines were.
    """
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] == MINE_VALUE:
                buttons[row][col].config(text=MINE_SYMBOL, bg=MINE_COLOR)


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


def on_left_click(row, col):
    """
    Handle a left-click on the cell at (row, col).

    - Ignored if the game has already ended, the cell is flagged, or the
      cell is already revealed (a cell cannot be selected twice).
    - If the cell is a mine: reveal all mines and end the game (loss).
    - If the cell is safe: reveal it and check if the player has won.
    """
    global game_over

    if game_over or flagged[row][col] or revealed[row][col]:
        return  # Invalid selection: do nothing

    if board[row][col] == MINE_VALUE:
        buttons[row][col].config(text=MINE_SYMBOL, bg=LOSING_MINE_COLOR)
        reveal_all_mines()
        game_over = True
        set_status("Game over!")
        messagebox.showinfo("Game Over", "You hit a mine! GAME OVER.")
    else:
        reveal_cell(row, col)
        if check_win():
            game_over = True
            set_status("You win!")
            messagebox.showinfo("You Win!", "Congratulations, YOU WIN!")
        else:
            set_status("Safe cell!")


def on_right_click(row, col):
    """
    Handle a right-click (or Control-click) on the cell at (row, col):
    toggle a flag on or off. Flags mark cells the player suspects
    contain a mine, and cannot be placed on already-revealed cells.
    """
    if game_over or revealed[row][col]:
        return  # Invalid selection: do nothing

    if flagged[row][col]:
        flagged[row][col] = False
        buttons[row][col].config(text="", bg=COVERED_COLOR)
    else:
        flagged[row][col] = True
        buttons[row][col].config(text=FLAG_SYMBOL, bg=FLAG_COLOR)

    update_flag_count()


# ------------------------------------------------------------------------
# GRAPHICAL INTERFACE HELPERS
# ------------------------------------------------------------------------
def update_flag_count():
    """
    Recount how many cells are currently flagged and refresh the
    flag counter shown in the info bar.
    """
    flag_total = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if flagged[row][col]:
                flag_total += 1

    flags_label.config(text="Flags: " + str(flag_total))


def set_status(message):
    """Update the short status message shown below the board."""
    status_label.config(text=message)


# ------------------------------------------------------------------------
# GRAPHICAL INTERFACE
# ------------------------------------------------------------------------
def create_widgets():
    """
    Build the title, instructions, info bar, board of cell buttons,
    status area, and reset button, and place them in the main window.
    """
    global buttons, mines_label, flags_label, status_label

    main_frame = tk.Frame(window, bg=BG_COLOR, padx=20, pady=20)
    main_frame.pack(expand=True)

    # --- Title ---
    title_label = tk.Label(
        main_frame, text="MINESWEEPER", font=FONT_TITLE, bg=BG_COLOR, fg=TEXT_COLOR
    )
    title_label.pack(pady=(0, 4))

    # --- Subtitle / instructions ---
    subtitle_text = (
        "Left click: Reveal a cell   |   Right click / Control-click: Place a flag\n"
        "Reveal all safe cells to win."
    )
    subtitle_label = tk.Label(
        main_frame, text=subtitle_text, font=FONT_SUBTITLE, bg=BG_COLOR, fg=TEXT_COLOR
    )
    subtitle_label.pack(pady=(0, 12))

    # --- Info bar: mine count and flag count ---
    info_frame = tk.Frame(main_frame, bg=BG_COLOR)
    info_frame.pack(pady=(0, 10))

    mines_label = tk.Label(
        info_frame,
        text="Mines: " + str(NUMBER_OF_MINES),
        font=FONT_INFO,
        bg=BG_COLOR,
        fg=TEXT_COLOR,
        padx=15,
    )
    mines_label.grid(row=0, column=0)

    flags_label = tk.Label(
        info_frame, text="Flags: 0", font=FONT_INFO, bg=BG_COLOR, fg=TEXT_COLOR, padx=15
    )
    flags_label.grid(row=0, column=1)

    # --- Board ---
    board_frame = tk.Frame(main_frame, bg=PANEL_COLOR, padx=8, pady=8)
    board_frame.pack()

    buttons = []
    for row in range(BOARD_SIZE):
        button_row = []
        for col in range(BOARD_SIZE):
            cell_button = tk.Button(
                board_frame,
                text="",
                width=CELL_SIZE,
                height=int(CELL_SIZE / 2) + 1,
                font=FONT_CELL,
                bg=COVERED_COLOR,
                relief=tk.RAISED,
                bd=2,
                command=lambda row=row, col=col: on_left_click(row, col),
            )
            cell_button.bind(
                "<Button-3>", lambda event, row=row, col=col: on_right_click(row, col)
            )
            cell_button.bind(
                "<Control-Button-1>",
                lambda event, row=row, col=col: on_right_click(row, col),
            )
            cell_button.grid(row=row, column=col, padx=2, pady=2)
            button_row.append(cell_button)
        buttons.append(button_row)

    # --- Status message ---
    status_label = tk.Label(
        main_frame, text="Good luck!", font=FONT_STATUS, bg=BG_COLOR, fg=TEXT_COLOR
    )
    status_label.pack(pady=(12, 8))

    # --- Reset / Play again button ---
    reset_button = tk.Button(
        main_frame,
        text="New Game",
        font=FONT_INFO,
        bg="#27ae60",
        fg="white",
        activebackground="#2ecc71",
        relief=tk.FLAT,
        padx=16,
        pady=6,
        command=reset_game,
    )
    reset_button.pack()


def reset_game():
    """
    Start a brand new game: create a fresh board, place new mines,
    recalculate neighbor counts, clear the revealed/flagged state, and
    reset every button and label back to its starting appearance.
    """
    global board, revealed, flagged, game_over

    board = create_board(BOARD_SIZE)
    place_mines(board, BOARD_SIZE, NUMBER_OF_MINES)
    count_adjacent_mines(board, BOARD_SIZE)

    revealed = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    flagged = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    game_over = False

    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            buttons[row][col].config(
                text="", bg=COVERED_COLOR, relief=tk.RAISED, state="normal"
            )

    update_flag_count()
    set_status("Good luck!")


# ------------------------------------------------------------------------
# PROGRAM ENTRY POINT
# ------------------------------------------------------------------------
window = tk.Tk()
window.title("Minesweeper")
window.configure(bg=BG_COLOR)
window.resizable(False, False)

create_widgets()
reset_game()  # Set up the first game when the program starts

window.mainloop()
