"""
================================================================================
 MINESWEEPER - Introduction to Programming Project
================================================================================
This program implements a simple graphical version of the classic Minesweeper
game using Python's Tkinter library for the interface and NumPy for storing
the internal game board.

How the game works:
    - The player is shown a grid of covered cells (buttons).
    - A number of mines are hidden randomly under some of the cells.
    - The player clicks a cell to "select" it.
        - If the cell has a mine, the game ends immediately (GAME OVER).
        - If the cell is safe, it shows how many mines are touching it
          (the eight neighboring cells: up, down, left, right, and the
          four diagonals).
    - The player wins by revealing every safe cell without clicking a mine.
    - The player can right-click a covered cell to place or remove a flag
      as a reminder of where they think a mine might be.

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
BOARD_SIZE = 10         # The board is BOARD_SIZE x BOARD_SIZE (5x5)
NUMBER_OF_MINES = 16    # How many mines are hidden on the board

MINE_VALUE = -1          # How a mine is represented inside the NumPy array

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
#             cell with a flag (right-click).
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

    We build a list of every possible (row, col) position, shuffle the
    possibilities using random.sample, and take the first num_mines of
    them. This guarantees the mine positions are unique (no duplicates).
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
            # Check all 8 neighboring positions around (row, col)
            for row_offset in [-1, 0, 1]:
                for col_offset in [-1, 0, 1]:
                    if row_offset == 0 and col_offset == 0:
                        continue  # Skip the cell itself, not a neighbor

                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset

                    # Make sure the neighbor position is actually on the
                    # board before checking it (avoids errors at edges
                    # and corners).
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
    button.config(relief=tk.SUNKEN, state="disabled", disabledforeground="black")

    if value == 0:
        # No mines nearby: show a blank cell
        button.config(text="", bg="light gray")
    else:
        button.config(text=str(value), bg="light gray")


def reveal_all_mines():
    """
    Show every mine on the board. Called when the player loses so they
    can see where all the mines were.
    """
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] == MINE_VALUE:
                buttons[row][col].config(text="*", bg="red")


def check_win():
    """
    Check whether the player has won the game.

    The player wins when every SAFE cell has been revealed. This means
    the number of revealed cells must equal the total number of cells
    minus the number of mines:

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
        # The player clicked a mine: game over
        buttons[row][col].config(text="*", bg="dark red")
        reveal_all_mines()
        game_over = True
        messagebox.showinfo("Game Over", "You hit a mine! GAME OVER.")
    else:
        reveal_cell(row, col)
        if check_win():
            game_over = True
            messagebox.showinfo("You Win!", "Congratulations, YOU WIN!")


def on_right_click(row, col):
    """
    Handle a right-click on the cell at (row, col): toggle a flag on or
    off. Flags mark cells the player suspects contain a mine, and cannot
    be placed on already-revealed cells.
    """
    if game_over or revealed[row][col]:
        return  # Invalid selection: do nothing

    if flagged[row][col]:
        flagged[row][col] = False
        buttons[row][col].config(text="", bg="light gray")
    else:
        flagged[row][col] = True
        buttons[row][col].config(text="F", bg="yellow")


# ------------------------------------------------------------------------
# GRAPHICAL INTERFACE
# ------------------------------------------------------------------------
def create_widgets():
    """
    Build the row of instructions, the grid of cell buttons, and the
    reset button, and place them in the main window.
    """
    global buttons

    # --- Instructions label ---
    instructions_text = (
        "How to play: Left-click a cell to reveal it. "
        "A number shows how many mines touch that cell. "
        "Right-click a cell to flag/unflag it. "
        "Avoid the mines and reveal every safe cell to win!"
    )
    instructions_label = tk.Label(
        window, text=instructions_text, wraplength=350, justify="left", pady=10
    )
    instructions_label.grid(row=0, column=0, columnspan=BOARD_SIZE)

    # --- Grid of buttons representing the board ---
    board_frame = tk.Frame(window)
    board_frame.grid(row=1, column=0, columnspan=BOARD_SIZE)

    buttons = []
    for row in range(BOARD_SIZE):
        button_row = []
        for col in range(BOARD_SIZE):
            # Using a default-argument trick (row=row, col=col) so each
            # button remembers its own position when clicked.
            cell_button = tk.Button(
                board_frame,
                text="",
                width=4,
                height=2,
                bg="light gray",
                command=lambda row=row, col=col: on_left_click(row, col),
            )
            cell_button.bind(
                "<Button-3>", lambda event, row=row, col=col: on_right_click(row, col)
            )
            cell_button.bind(
                "<Control-Button-1>", lambda event, row=row, col=col: on_right_click(row, col)
            )
            cell_button.grid(row=row, column=col)
            button_row.append(cell_button)
            
        buttons.append(button_row)

    # --- Reset / Play again button ---
    reset_button = tk.Button(window, text="Reset / Play Again", command=reset_game)
    reset_button.grid(row=2, column=0, columnspan=BOARD_SIZE, pady=10)


def reset_game():
    """
    Start a brand new game: create a fresh board, place new mines,
    recalculate neighbor counts, clear the revealed/flagged state, and
    reset every button back to its starting appearance.
    """
    global board, revealed, flagged, game_over

    #board = create_board(BOARD_SIZE)
    #place_mines(board, BOARD_SIZE, NUMBER_OF_MINES)
    #count_adjacent_mines(board, BOARD_SIZE)
    board = create_board(BOARD_SIZE)
    mine_positions = place_mines(board, BOARD_SIZE, NUMBER_OF_MINES)
    print("Mine positions:", mine_positions)
    count_adjacent_mines(board, BOARD_SIZE)


    revealed = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    flagged = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    game_over = False

    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            buttons[row][col].config(
                text="", bg="light gray", relief=tk.RAISED, state="normal"
            )


# ------------------------------------------------------------------------
# PROGRAM ENTRY POINT
# ------------------------------------------------------------------------
window = tk.Tk()
window.title("Minesweeper")

create_widgets()
reset_game()  # Set up the first game when the program starts

window.mainloop()
