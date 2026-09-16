"""
Queens Gambit - Color Management

Default pastel palette inspired by the LinkedIn/Apple Queens game aesthetic.
Supports per-color customisation with JSON persistence.
"""

import json
import os

# RGBA tuples — 12 high-contrast, highly distinguishable colours for grid regions
DEFAULT_COLORS = [
    (0.85, 0.25, 0.25, 1.0),   # 0  Vibrant Crimson Red
    (0.20, 0.50, 0.90, 1.0),   # 1  Bright Cobalt Blue
    (0.95, 0.75, 0.15, 1.0),   # 2  Vibrant Gold / Yellow
    (0.25, 0.75, 0.35, 1.0),   # 3  Emerald Green
    (0.70, 0.30, 0.85, 1.0),   # 4  Vibrant Purple
    (0.95, 0.50, 0.15, 1.0),   # 5  Bright Orange
    (0.20, 0.80, 0.80, 1.0),   # 6  Cyan / Aqua
    (0.90, 0.35, 0.65, 1.0),   # 7  Magenta Pink
    (0.55, 0.35, 0.20, 1.0),   # 8  Warm Brown / Bronze
    (0.70, 0.85, 0.20, 1.0),   # 9  Lime Green
    (0.40, 0.40, 0.90, 1.0),   # 10 Royal Indigo Blue
    (0.90, 0.70, 0.60, 1.0),   # 11 Peach / Coral
]



def darken(rgba, factor=0.6):
    """Return a darker version of *rgba* for use as a border colour."""
    return (rgba[0] * factor, rgba[1] * factor, rgba[2] * factor, rgba[3])


class ColorManager:
    """Manages colour palettes with optional on-disk persistence."""

    def __init__(self, storage_dir=None):
        """
        Args:
            storage_dir: Directory for the JSON config file.
                         Defaults to the same folder as this module.
        """
        if storage_dir is None:
            storage_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(storage_dir, exist_ok=True)
        self._config_path = os.path.join(storage_dir, "color_config.json")
        self.colors = list(DEFAULT_COLORS)
        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self):
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r") as fh:
                    data = json.load(fh)
                if "colors" in data and isinstance(data["colors"], list):
                    self.colors = [tuple(c) for c in data["colors"]]
        except (json.JSONDecodeError, IOError, TypeError):
            self.colors = list(DEFAULT_COLORS)

    def save(self):
        """Persist current palette to disk."""
        try:
            with open(self._config_path, "w") as fh:
                json.dump({"colors": [list(c) for c in self.colors]}, fh)
        except IOError:
            pass

    # -- accessors -----------------------------------------------------------

    def get_color(self, index):
        """Get the RGBA tuple for *index*, wrapping if out of range."""
        return self.colors[index % len(self.colors)]

    def set_color(self, index, rgba):
        """Set a custom colour at *index* and save."""
        while len(self.colors) <= index:
            self.colors.append(
                DEFAULT_COLORS[len(self.colors) % len(DEFAULT_COLORS)]
            )
        self.colors[index] = tuple(rgba)
        self.save()

    def reset(self):
        """Reset every colour to the built-in default."""
        self.colors = list(DEFAULT_COLORS)
        self.save()

    def get_palette(self, n):
        """Return a list of *n* RGBA tuples for the current puzzle."""
        return [self.get_color(i) for i in range(n)]
