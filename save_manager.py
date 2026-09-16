"""
Save & Resume Manager for Queens Gambit.

Saves the complete puzzle state (grid, solution, marks, lives, locked cells,
trial-mode state) to a JSON file so the player can resume where they left off.
"""

import json
import os
from puzzle import Puzzle


class SaveManager:
    """Handles saving and loading the active game session."""

    def __init__(self, storage_dir=None):
        if storage_dir is None:
            storage_dir = os.path.dirname(os.path.abspath(__file__))
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._save_file = os.path.join(self.storage_dir, "saved_game.json")

    # ------------------------------------------------------------------
    # Querying

    def has_saved_game(self):
        """Return True when a valid, in-progress saved game file exists."""
        if not os.path.exists(self._save_file):
            return False
        try:
            with open(self._save_file, "r") as fh:
                data = json.load(fh)
            return bool(
                data.get("puzzle")
                and not data.get("game_over")
                and not data.get("game_won")
            )
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Saving

    def save_game(self, grid_widget):
        """
        Serialise the current GridWidget state to disk.

        Always saves the *live* marks (which include trial marks when
        trial mode is active).  Also persists the trial mode flag,
        trial-mark set, and pre-trial snapshot so resuming fully restores
        the trial overlay.
        """
        if not grid_widget or not grid_widget.puzzle:
            return

        if grid_widget.game_over or grid_widget.game_won:
            self.clear_save()
            return

        puzzle = grid_widget.puzzle

        # --- live state (includes trial marks when in trial mode) ---
        serialized_marks = [
            [r, c, m] for (r, c), m in grid_widget.marks.items()
        ]
        serialized_locked = [
            [r, c] for (r, c) in grid_widget._locked_x_cells
        ]
        serialized_penalized = [
            [r, c] for (r, c) in grid_widget._penalized_cells
        ]

        # --- trial mode ---
        trial_mode = grid_widget.trial_mode
        serialized_trial_marks = [
            [r, c] for (r, c) in grid_widget._trial_marks
        ]

        serialized_trial_snapshot = None
        if trial_mode and grid_widget._trial_snapshot is not None:
            snap_marks, snap_locked, snap_penalized = grid_widget._trial_snapshot
            serialized_trial_snapshot = {
                "marks": [[r, c, m] for (r, c), m in snap_marks.items()],
                "locked_x": [[r, c] for (r, c) in snap_locked],
                "penalized": [[r, c] for (r, c) in snap_penalized],
            }

        save_data = {
            "puzzle": {
                "n": puzzle.n,
                "grid": puzzle.grid,
                "solution": [list(pos) for pos in puzzle.solution],
            },
            "marks": serialized_marks,
            "locked_x": serialized_locked,
            "penalized": serialized_penalized,
            "lives": grid_widget.lives,
            "game_over": grid_widget.game_over,
            "game_won": grid_widget.game_won,
            # trial mode fields
            "trial_mode": trial_mode,
            "trial_marks": serialized_trial_marks,
            "trial_snapshot": serialized_trial_snapshot,
        }

        try:
            with open(self._save_file, "w") as fh:
                json.dump(save_data, fh, indent=2)
        except Exception as e:
            print(f"[SaveManager] Error saving game: {e}")

    # ------------------------------------------------------------------
    # Loading

    def load_game(self):
        """
        Load saved game state from disk.

        Returns a dict ready to be passed to GridWidget.restore_state(),
        or None if no valid save exists.
        """
        if not os.path.exists(self._save_file):
            return None

        try:
            with open(self._save_file, "r") as fh:
                data = json.load(fh)

            p_data = data["puzzle"]
            puzzle = Puzzle(
                n=p_data["n"],
                grid=p_data["grid"],
                solution={tuple(pos) for pos in p_data["solution"]},
            )

            marks = {(r, c): m for r, c, m in data.get("marks", [])}
            locked_x = {tuple(rc) for rc in data.get("locked_x", [])}
            penalized = {tuple(rc) for rc in data.get("penalized", [])}
            lives = data.get("lives", 3)

            # Trial mode
            trial_mode = data.get("trial_mode", False)
            trial_marks = {tuple(rc) for rc in data.get("trial_marks", [])}

            raw_snap = data.get("trial_snapshot")
            trial_snapshot = None
            if raw_snap:
                trial_snapshot = (
                    {(r, c): m for r, c, m in raw_snap.get("marks", [])},
                    {tuple(rc) for rc in raw_snap.get("locked_x", [])},
                    {tuple(rc) for rc in raw_snap.get("penalized", [])},
                )

            return {
                "puzzle": puzzle,
                "marks": marks,
                "locked_x": locked_x,
                "penalized": penalized,
                "lives": lives,
                "trial_mode": trial_mode,
                "trial_marks": trial_marks,
                "trial_snapshot": trial_snapshot,
            }
        except Exception as e:
            print(f"[SaveManager] Error loading game: {e}")
            return None

    # ------------------------------------------------------------------
    # Clearing

    def clear_save(self):
        """Delete the saved game file when the game concludes or a new one starts."""
        if os.path.exists(self._save_file):
            try:
                os.remove(self._save_file)
            except Exception:
                pass

