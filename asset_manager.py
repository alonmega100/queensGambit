"""
Asset Manager for Queens Gambit.

Handles loading, uploading, gallery management, and selection
for custom Queen and X mark images. Persists custom image paths in JSON.
"""

import json
import os
import shutil

DEFAULT_QUEEN_FILENAME = "queen.png"
DEFAULT_X_FILENAME = "x.png"


class AssetManager:
    """Manages custom image galleries and selections for Queen and X marks."""

    def __init__(self, storage_dir=None):
        if storage_dir is None:
            storage_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.storage_dir = storage_dir
        self.assets_dir = os.path.join(storage_dir, "assets")
        self.custom_assets_dir = os.path.join(storage_dir, "custom_assets")
        
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.custom_assets_dir, exist_ok=True)

        self._config_path = os.path.join(storage_dir, "asset_config.json")
        
        self.selected_queen = None
        self.selected_x = None
        
        self._load_config()

    def _load_config(self):
        """Load selected assets configuration."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as fh:
                    data = json.load(fh)
                    self.selected_queen = data.get("selected_queen")
                    self.selected_x = data.get("selected_x")
            except Exception:
                pass

    def save_config(self):
        """Save selected assets configuration."""
        try:
            with open(self._config_path, "w") as fh:
                json.dump({
                    "selected_queen": self.selected_queen,
                    "selected_x": self.selected_x,
                }, fh, indent=2)
        except Exception:
            pass

    def get_queen_gallery(self):
        """Return list of available Queen image paths (defaults first, then custom)."""
        gallery = []
        # Check default asset in assets/
        default_p = os.path.join(self.assets_dir, DEFAULT_QUEEN_FILENAME)
        if os.path.exists(default_p):
            gallery.append(default_p)

        # Check custom_assets/
        if os.path.exists(self.custom_assets_dir):
            for fname in sorted(os.listdir(self.custom_assets_dir)):
                if fname.startswith("queen_") and fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    gallery.append(os.path.join(self.custom_assets_dir, fname))
        return gallery

    def get_x_gallery(self):
        """Return list of available X mark image paths (defaults first, then custom)."""
        gallery = []
        default_p = os.path.join(self.assets_dir, DEFAULT_X_FILENAME)
        if os.path.exists(default_p):
            gallery.append(default_p)

        if os.path.exists(self.custom_assets_dir):
            for fname in sorted(os.listdir(self.custom_assets_dir)):
                if fname.startswith("x_") and fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    gallery.append(os.path.join(self.custom_assets_dir, fname))
        return gallery

    def get_active_queen_path(self):
        """Get the currently selected Queen image path or fallback to default."""
        if self.selected_queen and os.path.exists(self.selected_queen):
            return self.selected_queen
        gallery = self.get_queen_gallery()
        return gallery[0] if gallery else None

    def get_active_x_path(self):
        """Get the currently selected X mark image path or None (if drawn procedurally)."""
        if self.selected_x and os.path.exists(self.selected_x):
            return self.selected_x
        gallery = self.get_x_gallery()
        return gallery[0] if gallery else None

    def set_active_queen(self, path):
        """Set the active queen image path."""
        self.selected_queen = path
        self.save_config()

    def set_active_x(self, path):
        """Set the active X image path."""
        self.selected_x = path
        self.save_config()

    def add_custom_image(self, category, source_path):
        """
        Copy a user-selected image into custom_assets with category prefix ('queen' or 'x').
        Returns the path of the saved copy.
        """
        if not os.path.exists(source_path):
            return None
        
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
            
        timestamp_name = f"{category}_{int(os.path.getmtime(source_path))}_{os.path.basename(source_path)}"
        dest_path = os.path.join(self.custom_assets_dir, timestamp_name)
        
        try:
            shutil.copy(source_path, dest_path)
            if category == "queen":
                self.set_active_queen(dest_path)
            elif category == "x":
                self.set_active_x(dest_path)
            return dest_path
        except Exception:
            return None
