"""
Queens Gambit - Game Grid Widget

Custom Kivy widget that renders the NxN puzzle grid with coloured regions,
handles touch input (single-tap = X mark, double-tap = queen placement),
enforces game rules (lives, auto-complete), and detects win/loss.
"""
LIVES = 100
import os

from kivy.uix.widget import Widget
from kivy.graphics import (
    Color, Rectangle, Line, Ellipse, RoundedRectangle, InstructionGroup,
)
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import (
    ObjectProperty, NumericProperty, BooleanProperty,
)
from kivy.core.image import Image as CoreImage


class GridWidget(Widget):
    """Renders and manages interaction with the Queens Gambit puzzle grid."""

    puzzle = ObjectProperty(None, allownone=True)
    lives = NumericProperty(3)
    game_over = BooleanProperty(False)
    game_won = BooleanProperty(False)
    trial_mode = BooleanProperty(False)

    # ----- lifecycle --------------------------------------------------------

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.marks = {}          # (r,c) -> 'x' | 'queen'
        self._colors = []        # list of RGBA tuples for each region
        self._pending_tap = None
        self._flash_cells = {}   # (r,c) -> remaining flash frames
        self._penalized_cells = set()  # (r,c) cells where player already lost a life
        self._locked_x_cells = set()   # (r,c) cells locked with permanent X
        self._trial_snapshot = None    # snapshot of (marks, locked_x, penalized) before entering trial mode
        self._trial_marks = set()      # cells modified during trial mode
        self._queen_texture = None
        self._x_texture = None
        self.asset_manager = None

        # Redraw when geometry changes
        self._redraw_trigger = Clock.create_trigger(self._redraw, 0)
        self.bind(pos=self._request_redraw, size=self._request_redraw)

        # Callbacks the host screen can set
        self.on_game_over = None
        self.on_game_won = None
        self.on_state_changed = None

        self._load_textures()

    def set_asset_manager(self, asset_manager):
        """Set the asset manager instance and reload textures."""
        self.asset_manager = asset_manager
        self.reload_textures()

    def _load_textures(self):
        """Attempt to load custom queen and X mark textures."""
        if self.asset_manager:
            q_path = self.asset_manager.get_active_queen_path()
            x_path = self.asset_manager.get_active_x_path()
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            q_path = os.path.join(base, "assets", "queen.png")
            x_path = os.path.join(base, "assets", "x.png")

        if q_path and os.path.exists(q_path):
            try:
                self._queen_texture = CoreImage(q_path).texture
            except Exception:
                self._queen_texture = None
        else:
            self._queen_texture = None

        if x_path and os.path.exists(x_path):
            try:
                self._x_texture = CoreImage(x_path).texture
            except Exception:
                self._x_texture = None
        else:
            self._x_texture = None

    def reload_textures(self):
        """Reload textures and trigger a redraw."""
        self._load_textures()
        self._request_redraw()


    # ----- public API -------------------------------------------------------

    def set_puzzle(self, puzzle, colors):
        """Load a new puzzle into the widget."""
        self.puzzle = puzzle
        self._colors = colors
        self.marks = {}
        self.lives = LIVES
        self.game_over = False
        self.game_won = False
        self.trial_mode = False
        self._trial_snapshot = None
        self._trial_marks.clear()
        self._flash_cells.clear()
        self._penalized_cells.clear()
        self._locked_x_cells.clear()
        self._request_redraw()
        self._notify_state_changed()

    def restore_state(self, puzzle, colors, marks, locked_x, penalized, lives,
                      trial_mode=False, trial_marks=None, trial_snapshot=None):
        """Restore a previously saved game state, including trial mode."""
        self.puzzle = puzzle
        self._colors = colors
        self.marks = dict(marks)
        self._locked_x_cells = set(locked_x)
        self._penalized_cells = set(penalized)
        self.lives = lives
        self.game_over = False
        self.game_won = False
        self.trial_mode = trial_mode
        self._trial_marks = set(trial_marks) if trial_marks else set()
        self._trial_snapshot = trial_snapshot
        self._flash_cells.clear()
        self._request_redraw()


    def _notify_state_changed(self):
        """Notify listeners that game state has changed (for autosave)."""
        if self.on_state_changed and not self.game_over and not self.game_won:
            self.on_state_changed()

    def reset(self):
        """Reset marks and lives — keep the same puzzle."""
        self.marks = {}
        self.lives = LIVES
        self.game_over = False
        self.game_won = False
        self.trial_mode = False
        self._trial_snapshot = None
        self._trial_marks.clear()
        self._flash_cells.clear()
        self._penalized_cells.clear()
        self._locked_x_cells.clear()
        self._request_redraw()

    def toggle_trial_mode(self):
        """Toggle trial & error mode. Entering saves a snapshot; exiting reverts trial marks."""
        if self.trial_mode:
            # Exiting trial mode: revert marks to snapshot
            if self._trial_snapshot is not None:
                saved_marks, saved_locked, saved_penalized = self._trial_snapshot
                self.marks = dict(saved_marks)
                self._locked_x_cells = set(saved_locked)
                self._penalized_cells = set(saved_penalized)
            self._trial_snapshot = None
            self._trial_marks.clear()
            self.trial_mode = False
        else:
            # Entering trial mode: save current state snapshot
            self._trial_snapshot = (
                dict(self.marks),
                set(self._locked_x_cells),
                set(self._penalized_cells),
            )
            self._trial_marks.clear()
            self.trial_mode = True
        self._request_redraw()

    # ----- geometry helpers -------------------------------------------------

    def _request_redraw(self, *_args):
        self._redraw_trigger()

    def _metrics(self):
        """Return a dict with grid layout numbers, or None."""
        if not self.puzzle:
            return None
        n = self.puzzle.n
        padding = dp(12)
        available = min(self.width, self.height) - 2 * padding
        if available <= 0:
            return None
        cell = available / n
        gw = cell * n
        return {
            "n": n,
            "cell": cell,
            "ox": self.x + (self.width - gw) / 2,
            "oy": self.y + (self.height - gw) / 2,
        }

    def _cell_screen_pos(self, row, col, m):
        """Bottom-left corner of cell (row, col) in screen coords."""
        x = m["ox"] + col * m["cell"]
        y = m["oy"] + (m["n"] - 1 - row) * m["cell"]
        return x, y

    def _pos_to_cell(self, pos):
        """Map a screen (x, y) to a grid (row, col) or None."""
        m = self._metrics()
        if m is None:
            return None
        col = int((pos[0] - m["ox"]) / m["cell"])
        screen_row = int((pos[1] - m["oy"]) / m["cell"])
        row = m["n"] - 1 - screen_row
        if 0 <= row < m["n"] and 0 <= col < m["n"]:
            return (row, col)
        return None

    # ----- drawing ----------------------------------------------------------

    def _redraw(self, *_args):
        self.canvas.clear()
        m = self._metrics()
        if m is None:
            return

        n = m["n"]
        cs = m["cell"]
        gap = dp(1.5)
        border_w = dp(2.5)

        with self.canvas:
            # ---- background ----
            Color(0.09, 0.09, 0.11, 1)
            Rectangle(pos=self.pos, size=self.size)

            # ---- cells ----
            for r in range(n):
                for c in range(n):
                    x, y = self._cell_screen_pos(r, c, m)
                    ci = self.puzzle.grid[r][c]
                    rgba = (
                        self._colors[ci]
                        if ci < len(self._colors)
                        else (0.5, 0.5, 0.5, 1)
                    )

                    # Flash overlay (incorrect queen attempt)
                    if (r, c) in self._flash_cells:
                        rgba = (0.9, 0.25, 0.25, 1)

                    Color(*rgba)
                    RoundedRectangle(
                        pos=(x + gap, y + gap),
                        size=(cs - 2 * gap, cs - 2 * gap),
                        radius=[dp(4)],
                    )

            # ---- region borders ----
            Color(0.12, 0.12, 0.14, 1)
            for r in range(n):
                for c in range(n):
                    x, y = self._cell_screen_pos(r, c, m)
                    cur = self.puzzle.grid[r][c]

                    # right edge
                    if c < n - 1 and self.puzzle.grid[r][c + 1] != cur:
                        Line(
                            points=[x + cs, y, x + cs, y + cs],
                            width=border_w,
                            cap="round",
                        )
                    # bottom edge (row+1 is visually below → lower y)
                    if r < n - 1 and self.puzzle.grid[r + 1][c] != cur:
                        Line(
                            points=[x, y, x + cs, y],
                            width=border_w,
                            cap="round",
                        )

            # ---- outer frame ----
            if self.trial_mode:
                Color(1, 0.65, 0.15, 0.9)  # Glowing Amber frame during Trial Mode
                Line(
                    rectangle=[m["ox"] - dp(1), m["oy"] - dp(1), cs * n + dp(2), cs * n + dp(2)],
                    width=dp(4),
                )
            else:
                Color(0.12, 0.12, 0.14, 1)
                Line(
                    rectangle=[m["ox"], m["oy"], cs * n, cs * n],
                    width=border_w,
                )

            # ---- marks ----
            for r in range(n):
                for c in range(n):
                    if (r, c) not in self.marks:
                        continue
                    x, y = self._cell_screen_pos(r, c, m)
                    mark = self.marks[(r, c)]
                    is_trial_mark = (r, c) in self._trial_marks

                    if mark == "x":
                        if self._x_texture:
                            Color(1, 0.8, 0.3, 0.95) if is_trial_mark else Color(1, 1, 1, 0.9)
                            xm = cs * 0.22
                            xs = cs - 2 * xm
                            Rectangle(
                                texture=self._x_texture,
                                pos=(x + xm, y + xm),
                                size=(xs, xs),
                            )
                        else:
                            if is_trial_mark:
                                Color(0.95, 0.60, 0.15, 0.90)  # Amber X in trial mode
                            else:
                                Color(0.20, 0.20, 0.25, 0.55)
                            mg = cs * 0.28
                            Line(
                                points=[x + mg, y + mg,
                                        x + cs - mg, y + cs - mg],
                                width=dp(2.5) if is_trial_mark else dp(2),
                                cap="round",
                            )
                            Line(
                                points=[x + mg, y + cs - mg,
                                        x + cs - mg, y + mg],
                                width=dp(2.5) if is_trial_mark else dp(2),
                                cap="round",
                            )

                    elif mark == "queen":
                        if is_trial_mark:
                            # Subtle glowing outline behind trial queens
                            Color(1, 0.7, 0.15, 0.4)
                            qm = cs * 0.10
                            qs = cs - 2 * qm
                            RoundedRectangle(pos=(x + qm, y + qm), size=(qs, qs), radius=[dp(6)])

                        if self._queen_texture:
                            Color(1, 1, 1, 1)
                            qm = cs * 0.15
                            qs = cs - 2 * qm
                            Rectangle(
                                texture=self._queen_texture,
                                pos=(x + qm, y + qm),
                                size=(qs, qs),
                            )
                        else:
                            # Fallback: golden circle
                            Color(1, 0.85, 0.2, 1)
                            qm = cs * 0.22
                            Ellipse(
                                pos=(x + qm, y + qm),
                                size=(cs - 2 * qm, cs - 2 * qm),
                            )

    # ----- touch handling ---------------------------------------------------

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if self.game_over or self.game_won:
            return True

        cell = self._pos_to_cell(touch.pos)
        if cell is None:
            return True

        if touch.is_double_tap:
            if self._pending_tap:
                self._pending_tap.cancel()
                self._pending_tap = None
            self._attempt_queen(cell)
        else:
            if self._pending_tap:
                self._pending_tap.cancel()
            self._pending_tap = Clock.schedule_once(
                lambda _dt, c=cell: self._toggle_x(c), 0.3
            )
        return True

    # ----- game actions -----------------------------------------------------

    def _toggle_x(self, cell):
        """Single-tap: toggle X mark (unless locked by auto-complete or wrong attempt)."""
        self._pending_tap = None
        if cell in self._locked_x_cells and not self.trial_mode:
            return  # Locked X cannot be undone outside trial mode

        if cell in self.marks:
            if self.marks[cell] == "x":
                del self.marks[cell]
                self._trial_marks.discard(cell)
            # Don't toggle away placed queens
        else:
            self.marks[cell] = "x"
            if self.trial_mode:
                self._trial_marks.add(cell)
        self._request_redraw()
        if not self.trial_mode:
            self._notify_state_changed()

    def _is_adjacent_to_placed_queen(self, row, col):
        """Check if (row, col) is within 1 tile distance of any placed queen."""
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if self.marks.get((nr, nc)) == "queen":
                    return True
        return False

    def _attempt_queen(self, cell):
        """Double-tap: try to place a queen or test placement in trial mode."""
        if cell in self.marks and self.marks[cell] == "queen":
            # If in trial mode and it was a trial queen, allow toggling it off
            if self.trial_mode and cell in self._trial_marks:
                del self.marks[cell]
                self._trial_marks.discard(cell)
                self._request_redraw()
            return

        # In trial mode, placing a queen is free with NO life loss and no win trigger
        if self.trial_mode:
            self.marks[cell] = "queen"
            self._trial_marks.add(cell)
            self._auto_complete(cell[0], cell[1])
            self._request_redraw()
            return

        if cell in self._locked_x_cells:
            return  # Already confirmed X — no action and no life loss

        row, col = cell
        if self.puzzle.check_placement(row, col):
            # Correct placement
            self.marks[cell] = "queen"
            self._auto_complete(row, col)
            self._request_redraw()
            self._notify_state_changed()
            self._check_win()
        else:
            # Wrong: automatically mark with X and lock it
            self.marks[cell] = "x"
            self._locked_x_cells.add(cell)

            # Check if this cell is adjacent to an already found queen:
            # or if the player already lost a life on this cell.
            is_near_queen = self._is_adjacent_to_placed_queen(row, col)
            already_penalized = cell in self._penalized_cells

            if not is_near_queen and not already_penalized:
                self._penalized_cells.add(cell)
                self.lives -= 1
                self._flash_cell(cell)
                self._notify_state_changed()
                if self.lives <= 0:
                    self.game_over = True
                    if self.on_game_over:
                        Clock.schedule_once(lambda _dt: self.on_game_over(), 0.4)
            else:
                # Just redraw with the X mark without deducting life
                self._request_redraw()
                self._notify_state_changed()

    def _flash_cell(self, cell):
        """Briefly highlight a cell red to indicate an incorrect guess."""
        self._flash_cells[cell] = True
        self._request_redraw()
        Clock.schedule_once(lambda _dt: self._unflash_cell(cell), 0.45)

    def _unflash_cell(self, cell):
        self._flash_cells.pop(cell, None)
        self._request_redraw()

    # ----- auto-complete ----------------------------------------------------

    def _auto_complete(self, row, col):
        """
        After a correct queen placement, automatically X-out cells
        that can no longer contain queens and lock them:
          1. All 8 surrounding cells (king-distance).
          2. Remaining row cells if this row now has 2 queens.
          3. Remaining column cells if this column now has 2 queens.
          4. Remaining region cells if this colour now has 2 queens.
        """
        n = self.puzzle.n

        # Helper to set and lock X
        def _set_locked_x(r, c):
            if self.marks.get((r, c)) != "queen":
                self.marks[(r, c)] = "x"
                if self.trial_mode:
                    self._trial_marks.add((r, c))
                else:
                    self._locked_x_cells.add((r, c))

        # 1. King-distance neighbours
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < n and 0 <= nc < n:
                    _set_locked_x(nr, nc)

        # 2. Row completion
        row_queens = sum(
            1 for c in range(n) if self.marks.get((row, c)) == "queen"
        )
        if row_queens >= 2:
            for c in range(n):
                _set_locked_x(row, c)

        # 3. Column completion
        col_queens = sum(
            1 for r in range(n) if self.marks.get((r, col)) == "queen"
        )
        if col_queens >= 2:
            for r in range(n):
                _set_locked_x(r, col)

        # 4. Colour-region completion
        color = self.puzzle.grid[row][col]
        color_queens = sum(
            1
            for r in range(n)
            for c in range(n)
            if self.puzzle.grid[r][c] == color
            and self.marks.get((r, c)) == "queen"
        )
        if color_queens >= 2:
            for r in range(n):
                for c in range(n):
                    if self.puzzle.grid[r][c] == color:
                        _set_locked_x(r, c)

    # ----- win detection ----------------------------------------------------

    def _check_win(self):
        placed = frozenset(
            cell for cell, mark in self.marks.items() if mark == "queen"
        )
        if placed == self.puzzle.solution:
            self.game_won = True
            if self.on_game_won:
                Clock.schedule_once(lambda _dt: self.on_game_won(), 0.3)