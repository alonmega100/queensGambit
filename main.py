"""
Queens Gambit - Main Application Entry Point

A Kivy-based puzzle game packaged as an Android APK via Buildozer.
Place 2 queens per coloured region, row, and column on an NxN grid
with no two queens adjacent (including diagonals).
"""

import os
import threading

# ---------------------------------------------------------------------------
# Kivy configuration — must come before any other Kivy import
# ---------------------------------------------------------------------------
os.environ.setdefault("KIVY_LOG_LEVEL", "info")

from kivy.config import Config

Config.set("postproc", "double_tap_time", "300")
Config.set("postproc", "double_tap_distance", "20")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.colorpicker import ColorPicker
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import StringProperty
from kivy.graphics import Color, RoundedRectangle, Rectangle

from kivy.uix.image import Image as KivyImage
from kivy.uix.filechooser import FileChooserIconView

# Game modules — imported before KV so the <GridWidget> rule resolves
from game import GridWidget  # noqa: F401  (used in KV)
from puzzle import generate_puzzle, get_sample_puzzle
from colors import ColorManager, DEFAULT_COLORS
from asset_manager import AssetManager
from save_manager import SaveManager
from level_editor import LevelEditorWidget, _PaletteSwatch  # noqa: F401

# ---------------------------------------------------------------------------
# Window size (desktop testing only)
# ---------------------------------------------------------------------------
from kivy.core.window import Window

_IS_ANDROID = False
try:
    import android  # noqa: F401

    _IS_ANDROID = True
except ImportError:
    Window.size = (420, 750)


# ═══════════════════════════════════════════════════════════════════════════
# KV Layout
# ═══════════════════════════════════════════════════════════════════════════

KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

# -- reusable rounded button ------------------------------------------------
<RoundedButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    bold: True
    font_size: sp(16)
    canvas.before:
        Color:
            rgba: (0.26, 0.26, 0.31, 1) if self.state == 'normal' else (0.36, 0.36, 0.41, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<SizeButton@ToggleButton>:
    group: 'grid_size'
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    bold: True
    font_size: sp(15)
    canvas.before:
        Color:
            rgba: (0.45, 0.32, 0.65, 1) if self.state == 'down' else (0.26, 0.26, 0.31, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

# ═══════════════════════════════════════════════════════════════════════════
# Menu Screen
# ═══════════════════════════════════════════════════════════════════════════
<MenuScreen>:
    name: 'menu'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        padding: [dp(30), dp(50), dp(30), dp(30)]
        spacing: dp(12)
        size: root.size
        pos: root.pos

        Widget:
            size_hint_y: 0.05

        Image:
            source: 'assets/logo.png'
            size_hint_y: 0.22

        Label:
            text: 'Queens Gambit'
            font_size: sp(30)
            size_hint_y: 0.07
            color: 0.95, 0.95, 0.95, 1
            bold: True

        Label:
            text: 'Place the queens. No neighbours allowed.'
            font_size: sp(13)
            size_hint_y: 0.04
            color: 0.55, 0.55, 0.60, 1

        Widget:
            size_hint_y: 0.07

        Label:
            text: 'GRID SIZE'
            font_size: sp(12)
            size_hint_y: 0.03
            color: 0.55, 0.55, 0.60, 1
            bold: True

        BoxLayout:
            size_hint_y: 0.07
            spacing: dp(8)
            padding: [dp(8), 0]

            SizeButton:
                text: '8\\u00d78'
                on_press: root.select_size(8)
                id: btn_8

            SizeButton:
                text: '9\\u00d79'
                on_press: root.select_size(9)
                id: btn_9

            SizeButton:
                text: '10\\u00d710'
                state: 'down'
                on_press: root.select_size(10)
                id: btn_10

            SizeButton:
                text: '11\\u00d711'
                on_press: root.select_size(11)
                id: btn_11

        Widget:
            size_hint_y: 0.06

        RoundedButton:
            text: 'Play'
            font_size: sp(22)
            size_hint_y: 0.09
            size_hint_x: 0.6
            pos_hint: {'center_x': 0.5}
            on_press: root.start_game()
            canvas.before:
                Color:
                    rgba: (0.45, 0.30, 0.68, 1) if self.state == 'normal' else (0.55, 0.40, 0.78, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]

        RoundedButton:
            id: resume_btn
            text: '\u25b6  Resume'
            font_size: sp(18)
            size_hint_y: 0.08
            size_hint_x: 0.6
            pos_hint: {'center_x': 0.5}
            opacity: 0
            disabled: True
            on_press: root.resume_game()
            canvas.before:
                Color:
                    rgba: (0.22, 0.50, 0.32, 1) if self.state == 'normal' else (0.30, 0.62, 0.42, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]

        Label:
            id: status_label
            text: ''
            font_size: sp(13)
            size_hint_y: 0.04
            color: 0.65, 0.65, 0.70, 1

        Widget:
            size_hint_y: 0.03

        BoxLayout:
            size_hint_y: 0.065
            spacing: dp(10)
            padding: [dp(16), 0]

            RoundedButton:
                text: 'Settings'
                font_size: sp(13)
                on_press: root.go_settings()

            RoundedButton:
                text: '\\u270f  Create'
                font_size: sp(13)
                on_press: root.go_level_editor()
                canvas.before:
                    Color:
                        rgba: (0.25, 0.14, 0.50, 1) if self.state == 'normal' else (0.35, 0.22, 0.62, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]

        Widget:
            size_hint_y: 0.03

# ═══════════════════════════════════════════════════════════════════════════
# Game Screen
# ═══════════════════════════════════════════════════════════════════════════
<GameScreen>:
    name: 'game'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        size: root.size
        pos: root.pos
        padding: [dp(6), dp(8)]
        spacing: dp(4)

        # -- top bar --
        BoxLayout:
            size_hint_y: 0.055
            spacing: dp(6)

            RoundedButton:
                text: '\\u2190'
                size_hint_x: 0.12
                font_size: sp(20)
                on_press: root.go_back()

            Label:
                text: 'Queens Gambit'
                font_size: sp(16)
                color: 0.88, 0.88, 0.88, 1
                bold: True
                size_hint_x: 0.45

            BoxLayout:
                id: lives_box
                orientation: 'horizontal'
                size_hint_x: 0.43
                spacing: dp(4)
                alignment: 'right'
                padding: [0, dp(4)]

        # -- grid --
        GridWidget:
            id: grid_widget
            size_hint_y: 0.835

        # -- bottom bar --
        BoxLayout:
            size_hint_y: 0.055
            spacing: dp(6)
            padding: [dp(10), 0]

            RoundedButton:
                id: trial_btn
                text: '[Trial ON]' if grid_widget.trial_mode else 'Trial & Error'
                font_size: sp(13)
                bold: True
                color: (1, 0.9, 0.4, 1) if grid_widget.trial_mode else (1, 1, 1, 1)
                on_press: root.toggle_trial_mode()
                canvas.before:
                    Color:
                        rgba: (0.75, 0.45, 0.10, 1) if grid_widget.trial_mode else ((0.26, 0.26, 0.31, 1) if self.state == 'normal' else (0.36, 0.36, 0.41, 1))
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]

            RoundedButton:
                text: '\\u2699 Theme'
                font_size: sp(12)
                on_press: root.open_theme_popup()

            RoundedButton:
                text: '\\U0001f4be Quit'
                font_size: sp(12)
                on_press: root.save_and_quit()
                canvas.before:
                    Color:
                        rgba: (0.55, 0.18, 0.18, 1) if self.state == 'normal' else (0.68, 0.25, 0.25, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]

# ═══════════════════════════════════════════════════════════════════════════
# Settings Screen
# ═══════════════════════════════════════════════════════════════════════════
<SettingsScreen>:
    name: 'settings'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        size: root.size
        pos: root.pos
        padding: [dp(12), dp(12)]
        spacing: dp(8)

        # -- header --
        BoxLayout:
            size_hint_y: 0.07
            spacing: dp(8)

            RoundedButton:
                text: '\\u2190'
                size_hint_x: 0.15
                font_size: sp(20)
                on_press: root.go_back()

            Label:
                text: 'Game Settings'
                font_size: sp(18)
                color: 0.9, 0.9, 0.9, 1
                bold: True

        # -- settings content scrollview --
        ScrollView:
            size_hint_y: 0.93
            do_scroll_x: False

            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(16)
                padding: [dp(4), dp(4)]

                # Section 1: Queen Gallery
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(30)
                        Label:
                            text: 'Queen Icon Gallery'
                            font_size: sp(16)
                            bold: True
                            color: 1, 0.85, 0.3, 1
                            halign: 'left'
                            text_size: self.size

                        Button:
                            text: '+ Upload Queen'
                            size_hint_x: None
                            width: dp(120)
                            font_size: sp(12)
                            background_normal: ''
                            background_color: 0.35, 0.25, 0.55, 1
                            on_press: root.upload_image('queen')

                    ScrollView:
                        size_hint_y: None
                        height: dp(85)
                        do_scroll_y: False
                        BoxLayout:
                            id: queen_gallery_box
                            orientation: 'horizontal'
                            size_hint_x: None
                            width: self.minimum_width
                            spacing: dp(10)
                            padding: [dp(4), dp(4)]

                # Section 2: X Mark Gallery
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(30)
                        Label:
                            text: 'X Mark Gallery'
                            font_size: sp(16)
                            bold: True
                            color: 0.4, 0.75, 0.9, 1
                            halign: 'left'
                            text_size: self.size

                        Button:
                            text: '+ Upload X'
                            size_hint_x: None
                            width: dp(120)
                            font_size: sp(12)
                            background_normal: ''
                            background_color: 0.35, 0.25, 0.55, 1
                            on_press: root.upload_image('x')

                    ScrollView:
                        size_hint_y: None
                        height: dp(85)
                        do_scroll_y: False
                        BoxLayout:
                            id: x_gallery_box
                            orientation: 'horizontal'
                            size_hint_x: None
                            width: self.minimum_width
                            spacing: dp(10)
                            padding: [dp(4), dp(4)]

                # Section 3: Colour Palette
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

                    Label:
                        text: 'Region Colours'
                        font_size: sp(16)
                        bold: True
                        color: 0.9, 0.9, 0.9, 1
                        size_hint_y: None
                        height: dp(30)
                        halign: 'left'
                        text_size: self.size

                    BoxLayout:
                        id: colors_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(6)

                    RoundedButton:
                        text: 'Reset Colours to Default'
                        size_hint_y: None
                        height: dp(40)
                        font_size: sp(13)
                        on_press: root.reset_colors()


# ═══════════════════════════════════════════════════════════════════════════
# Level Editor Screen
# ═══════════════════════════════════════════════════════════════════════════
<LevelEditorScreen>:
    name: 'level_editor'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        size: root.size
        pos: root.pos
        padding: [dp(6), dp(8)]
        spacing: dp(4)

        # -- header --
        BoxLayout:
            size_hint_y: 0.055
            spacing: dp(6)

            RoundedButton:
                text: '\\u2190'
                size_hint_x: 0.12
                font_size: sp(20)
                on_press: root.go_back()

            Label:
                text: 'Level Editor'
                font_size: sp(16)
                color: 0.88, 0.88, 0.88, 1
                bold: True

            RoundedButton:
                text: 'Clear'
                size_hint_x: 0.22
                font_size: sp(13)
                on_press: root.clear_grid()

        # -- size selector --
        BoxLayout:
            size_hint_y: 0.06
            spacing: dp(6)
            padding: [dp(4), 0]

            Label:
                text: 'Size:'
                size_hint_x: 0.18
                color: 0.65, 0.65, 0.70, 1
                font_size: sp(13)
                halign: 'right'
                text_size: self.size

            SizeButton:
                id: le_8
                text: '8\\u00d78'
                group: 'le_size'
                on_press: root.set_size(8)

            SizeButton:
                id: le_9
                text: '9\\u00d79'
                group: 'le_size'
                on_press: root.set_size(9)

            SizeButton:
                id: le_10
                text: '10\\u00d710'
                state: 'down'
                group: 'le_size'
                on_press: root.set_size(10)

            SizeButton:
                id: le_11
                text: '11\\u00d711'
                group: 'le_size'
                on_press: root.set_size(11)

        # -- colour palette --
        ScrollView:
            size_hint_y: 0.09
            do_scroll_y: False
            BoxLayout:
                id: palette_box
                orientation: 'horizontal'
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(8)
                padding: [dp(6), dp(4)]

        # -- status / instructions --
        Label:
            id: editor_status
            text: 'Select a colour \\u2192 tap or drag cells to paint.  Use all N colours!'
            size_hint_y: 0.04
            font_size: sp(11)
            color: 0.60, 0.60, 0.65, 1
            halign: 'center'
            text_size: self.size

        # -- paint canvas --
        LevelEditorWidget:
            id: editor_widget
            size_hint_y: 0.685

        # -- solve button --
        RoundedButton:
            text: '\\u2705  Solve & Play'
            size_hint_y: 0.06
            font_size: sp(15)
            bold: True
            on_press: root.solve_and_play()
            canvas.before:
                Color:
                    rgba: (0.18, 0.46, 0.28, 1) if self.state == 'normal' else (0.26, 0.56, 0.36, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12)]

"""





# ═══════════════════════════════════════════════════════════════════════════
# Screens
# ═══════════════════════════════════════════════════════════════════════════

class MenuScreen(Screen):
    """Title / difficulty-select screen."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.selected_size = 10

    def on_enter(self):
        """Refresh Resume button visibility each time we come back to the menu."""
        app = App.get_running_app()
        has_save = app.save_manager.has_saved_game() if app.save_manager else False
        btn = self.ids.resume_btn
        btn.opacity = 1 if has_save else 0
        btn.disabled = not has_save

    def select_size(self, size):
        self.selected_size = size

    def start_game(self):
        self.ids.status_label.text = "Generating puzzle\u2026"
        app = App.get_running_app()
        app.start_new_game(self.selected_size)

    def resume_game(self):
        app = App.get_running_app()
        app.resume_saved_game()

    def go_settings(self):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "settings"

    def go_level_editor(self):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "level_editor"


class GameScreen(Screen):
    """Main gameplay screen."""

    def __init__(self, **kw):
        super().__init__(**kw)

    # -- setup ---------------------------------------------------------------

    def setup_game(self, puzzle, color_manager, asset_manager):
        grid = self.ids.grid_widget
        grid.set_asset_manager(asset_manager)
        colors = color_manager.get_palette(puzzle.n)
        grid.set_puzzle(puzzle, colors)
        grid.on_game_over = self._on_game_over
        grid.on_game_won = self._on_game_won
        grid.bind(lives=self._sync_lives)
        self._sync_lives()

    # -- lives display -------------------------------------------------------

    def _sync_lives(self, *_args):
        grid = self.ids.grid_widget
        box = self.ids.lives_box
        box.clear_widgets()

        current_lives = grid.lives
        total_lives = min(3, current_lives)  # show standard 3 hearts max (or counter if infinite)

        if current_lives > 5:
            # High / infinite debug lives display
            heart_img = KivyImage(
                source="assets/heart.png",
                size_hint=(None, None), size=(dp(24), dp(24)),
            )
            lbl = Label(
                text=f"x{current_lives}",
                font_size=sp(16), bold=True, color=(1, 0.3, 0.3, 1),
                size_hint_x=None, width=dp(45),
            )
            box.add_widget(heart_img)
            box.add_widget(lbl)
        else:
            for i in range(current_lives):
                heart_img = KivyImage(
                    source="assets/heart.png",
                    size_hint=(None, None), size=(dp(24), dp(24)),
                )
                box.add_widget(heart_img)

    # -- popups --------------------------------------------------------------

    def _styled_popup(self, title, message, buttons):
        """Build a dark-themed popup with *buttons* list of (label, callback)."""
        content = BoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=[dp(20), dp(15)],
        )
        content.add_widget(Label(
            text=message, font_size=sp(17),
            color=(0.92, 0.92, 0.92, 1), size_hint_y=0.45,
        ))
        btn_box = BoxLayout(spacing=dp(10), size_hint_y=0.45)
        popup = Popup(
            title=title, content=content,
            size_hint=(0.82, 0.33), auto_dismiss=False,
            separator_color=(0.45, 0.32, 0.65, 1),
            background_color=(0.12, 0.12, 0.15, 1),
        )
        for label, cb in buttons:
            btn = Button(
                text=label, font_size=sp(15),
                background_normal="", background_color=(0.28, 0.28, 0.33, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_press=lambda _b, _cb=cb: (popup.dismiss(), _cb()))
            btn_box.add_widget(btn)
        content.add_widget(btn_box)
        popup.open()

    def _on_game_over(self):
        self._styled_popup(
            "Game Over",
            "You ran out of lives!",
            [("Main Menu", self.go_back)],
        )

    def _on_game_won(self):
        self._styled_popup(
            "\u2728 Congratulations!",
            "Puzzle solved!",
            [("Main Menu", self.go_back)],
        )

    # -- actions -------------------------------------------------------------

    def open_theme_popup(self):
        """Open a popup during the game to quickly select Queen and X mark themes."""
        app = App.get_running_app()
        am = app.asset_manager

        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

        # --- Queen Selection Row ---
        content.add_widget(Label(
            text="Queen Icon", font_size=sp(15), bold=True,
            color=(1, 0.85, 0.3, 1), size_hint_y=None, height=dp(24),
            halign="left", text_size=(dp(300), dp(24)),
        ))
        
        q_scroll = ScrollView(size_hint_y=None, height=dp(75), do_scroll_y=False)
        q_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_x=None)
        q_box.bind(minimum_width=q_box.setter("width"))

        active_q = am.get_active_queen_path()
        for img_path in am.get_queen_gallery():
            is_sel = (img_path == active_q)
            btn = Button(
                size_hint=(None, None), size=(dp(60), dp(60)),
                background_normal="",
                background_color=(0.4, 0.7, 0.4, 1) if is_sel else (0.18, 0.18, 0.22, 1),
            )
            img = KivyImage(source=img_path, fit_mode="contain")
            btn.add_widget(img)
            def _select_q(_b, p=img_path):
                am.set_active_queen(p)
                self.ids.grid_widget.reload_textures()
                popup.dismiss()
                self.open_theme_popup()
            btn.bind(on_press=_select_q)
            q_box.add_widget(btn)
        q_scroll.add_widget(q_box)
        content.add_widget(q_scroll)

        # --- X Mark Selection Row ---
        content.add_widget(Label(
            text="X Mark Style", font_size=sp(15), bold=True,
            color=(0.4, 0.75, 0.9, 1), size_hint_y=None, height=dp(24),
            halign="left", text_size=(dp(300), dp(24)),
        ))

        x_scroll = ScrollView(size_hint_y=None, height=dp(75), do_scroll_y=False)
        x_box = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_x=None)
        x_box.bind(minimum_width=x_box.setter("width"))

        active_x = am.get_active_x_path()
        
        # Procedural default X
        proc_btn = Button(
            text="Default\n[X]", size_hint=(None, None), size=(dp(60), dp(60)),
            background_normal="",
            background_color=(0.3, 0.4, 0.5, 1) if active_x is None else (0.18, 0.18, 0.22, 1),
            color=(1, 1, 1, 1), font_size=sp(11), bold=(active_x is None),
        )
        def _select_proc_x(_b):
            am.set_active_x(None)
            self.ids.grid_widget.reload_textures()
            popup.dismiss()
            self.open_theme_popup()
        proc_btn.bind(on_press=_select_proc_x)
        x_box.add_widget(proc_btn)

        for img_path in am.get_x_gallery():
            is_sel = (img_path == active_x)
            btn = Button(
                size_hint=(None, None), size=(dp(60), dp(60)),
                background_normal="",
                background_color=(0.4, 0.7, 0.4, 1) if is_sel else (0.18, 0.18, 0.22, 1),
            )
            img = KivyImage(source=img_path, fit_mode="contain")
            btn.add_widget(img)
            def _select_x(_b, p=img_path):
                am.set_active_x(p)
                self.ids.grid_widget.reload_textures()
                popup.dismiss()
                self.open_theme_popup()
            btn.bind(on_press=_select_x)
            x_box.add_widget(btn)
        x_scroll.add_widget(x_box)
        content.add_widget(x_scroll)

        # Close button
        close_btn = Button(
            text="Done", size_hint_y=None, height=dp(38),
            font_size=sp(14), background_normal="",
            background_color=(0.28, 0.28, 0.33, 1), color=(1, 1, 1, 1),
        )
        content.add_widget(close_btn)

        popup = Popup(
            title="Change Look & Theme",
            content=content,
            size_hint=(0.92, 0.65),
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def toggle_trial_mode(self):
        """Toggle trial and error mode on the grid widget."""
        self.ids.grid_widget.toggle_trial_mode()

    def save_and_quit(self):
        """Save current game state and return to the main menu."""
        app = App.get_running_app()
        app.save_manager.save_game(self.ids.grid_widget)
        self.go_back()

    def go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"


class SettingsScreen(Screen):
    """Per-colour and asset customisation screen."""

    def on_enter(self):
        app = App.get_running_app()
        self._build_galleries(app.asset_manager)
        self._build_list(app.color_manager)

    def _build_galleries(self, am):
        self._build_gallery('queen', am)
        self._build_gallery('x', am)

    def _build_gallery(self, category, am):
        box = self.ids.queen_gallery_box if category == 'queen' else self.ids.x_gallery_box
        box.clear_widgets()

        if category == 'queen':
            gallery = am.get_queen_gallery()
            active = am.get_active_queen_path()
        else:
            gallery = am.get_x_gallery()
            active = am.get_active_x_path()

        # If X mark has no custom image, add a placeholder button for procedural X
        if category == 'x':
            is_proc_active = active is None
            proc_card = Button(
                text="Default\n[X]",
                size_hint=(None, None),
                size=(dp(70), dp(70)),
                background_normal="",
                background_color=(0.3, 0.4, 0.5, 1) if is_proc_active else (0.18, 0.18, 0.22, 1),
                color=(1, 1, 1, 1),
                font_size=sp(12),
                bold=is_proc_active,
            )
            proc_card.bind(on_press=lambda _b: self._select_asset('x', None))
            box.add_widget(proc_card)

        for img_path in gallery:
            is_selected = (img_path == active)
            btn = Button(
                size_hint=(None, None),
                size=(dp(70), dp(70)),
                background_normal="",
                background_color=(0.4, 0.7, 0.4, 1) if is_selected else (0.15, 0.15, 0.18, 1),
                padding=[dp(4), dp(4)],
            )
            
            # Thumbnail container inside button
            img = KivyImage(
                source=img_path,
                fit_mode="contain",
                size_hint=(1, 1),
            )
            btn.add_widget(img)
            btn.bind(on_press=lambda _b, cat=category, p=img_path: self._select_asset(cat, p))
            box.add_widget(btn)

    def _select_asset(self, category, path):
        app = App.get_running_app()
        am = app.asset_manager
        if category == 'queen':
            am.set_active_queen(path)
        else:
            am.set_active_x(path)
        
        self._build_galleries(am)
        
        # Update active game screen if instantiated
        if self.manager.has_screen('game'):
            grid = self.manager.get_screen('game').ids.grid_widget
            grid.reload_textures()

    def upload_image(self, category):
        """Open a FileChooser popup to select an image from local storage."""
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        
        # Initial directory path
        start_path = os.path.expanduser("~")
        fc = FileChooserIconView(path=start_path, filters=["*.png", "*.jpg", "*.jpeg", "*.webp"])
        content.add_widget(fc)

        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        cancel_btn = Button(text="Cancel", font_size=sp(14))
        select_btn = Button(
            text="Select Image", font_size=sp(14),
            background_normal="", background_color=(0.35, 0.25, 0.65, 1), color=(1, 1, 1, 1)
        )
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(select_btn)
        content.add_widget(btn_box)

        popup = Popup(
            title=f"Upload {category.title()} Image",
            content=content,
            size_hint=(0.95, 0.85),
        )

        cancel_btn.bind(on_press=popup.dismiss)

        def _do_select(_btn):
            if fc.selection:
                selected_file = fc.selection[0]
                app = App.get_running_app()
                am = app.asset_manager
                saved_path = am.add_custom_image(category, selected_file)
                if saved_path:
                    self._select_asset(category, saved_path)
                popup.dismiss()

        select_btn.bind(on_press=_do_select)
        popup.open()

    def _build_list(self, cm):
        box = self.ids.colors_box
        box.clear_widgets()

        for i in range(len(DEFAULT_COLORS)):
            row = BoxLayout(
                size_hint_y=None, height=dp(48),
                spacing=dp(10), padding=[dp(4), 0],
            )

            swatch = _ColorSwatch(rgba=cm.get_color(i))
            label = Label(
                text=f"Colour {i + 1}",
                size_hint_x=0.45,
                color=(0.82, 0.82, 0.82, 1),
                font_size=sp(14),
            )
            edit_btn = Button(
                text="Edit", size_hint_x=0.28,
                font_size=sp(13),
                background_normal="",
                background_color=(0.26, 0.26, 0.31, 1),
                color=(1, 1, 1, 1),
            )
            edit_btn.bind(on_press=lambda _b, idx=i: self._pick_color(idx))

            row.add_widget(swatch)
            row.add_widget(label)
            row.add_widget(edit_btn)
            box.add_widget(row)

    def _pick_color(self, index):
        app = App.get_running_app()
        cm = app.color_manager

        picker = ColorPicker(color=list(cm.get_color(index)))

        outer = BoxLayout(orientation="vertical", spacing=dp(8))
        outer.add_widget(picker)

        save_btn = Button(
            text="Save", size_hint_y=None, height=dp(44),
            font_size=sp(16),
            background_normal="",
            background_color=(0.40, 0.30, 0.65, 1),
            color=(1, 1, 1, 1),
        )
        outer.add_widget(save_btn)

        popup = Popup(
            title=f"Edit Colour {index + 1}",
            content=outer,
            size_hint=(0.95, 0.80),
        )

        def _save(_btn):
            cm.set_color(index, picker.color)
            popup.dismiss()
            self._build_list(cm)

        save_btn.bind(on_press=_save)
        popup.open()

    def reset_colors(self):
        app = App.get_running_app()
        app.color_manager.reset()
        self._build_list(app.color_manager)

    def go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "menu"




class _ColorSwatch(Widget):
    """Small coloured rectangle used in the settings list."""

    def __init__(self, rgba=(0.5, 0.5, 0.5, 1), **kw):
        super().__init__(size_hint_x=0.18, **kw)
        self._rgba = rgba
        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_once(self._draw, 0)

    def _draw(self, *_args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*self._rgba)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])


class LevelEditorScreen(Screen):
    """Screen where the user paints color regions and the game auto-solves queen positions."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._n = 10
        self._selected_color = 0
        self._solving = False
        self._swatches = []  # list of _PaletteSwatch widgets

    def on_enter(self):
        """Initialise / reinitialise the editor each time the screen is shown."""
        app = App.get_running_app()
        self._n = 10
        self.ids.le_10.state = 'down'
        self._selected_color = 0
        self._solving = False
        self.ids.editor_status.text = 'Select a colour \u2192 tap or drag cells to paint.  Use all N colours!'
        self._build_palette(app.color_manager)
        self.ids.editor_widget.setup(self._n, app.color_manager.get_palette(self._n))

    # -- palette ---------------------------------------------------------------

    def _build_palette(self, cm):
        box = self.ids.palette_box
        box.clear_widgets()
        self._swatches = []
        colors = cm.get_palette(self._n)
        for i, rgba in enumerate(colors):
            swatch = _PaletteSwatch(
                rgba=rgba, index=i,
                on_select_cb=self._select_color,
            )
            swatch.selected = (i == self._selected_color)
            box.add_widget(swatch)
            self._swatches.append(swatch)

    def _select_color(self, idx):
        self._selected_color = idx
        self.ids.editor_widget.selected_color = idx
        for i, sw in enumerate(self._swatches):
            sw.selected = (i == idx)

    # -- size / clear ----------------------------------------------------------

    def set_size(self, n):
        if n == self._n:
            return
        self._n = n
        self._selected_color = 0
        self._solving = False
        self.ids.editor_status.text = 'Select a colour \u2192 tap or drag cells to paint.  Use all N colours!'
        app = App.get_running_app()
        self._build_palette(app.color_manager)
        self.ids.editor_widget.setup(n, app.color_manager.get_palette(n))

    def clear_grid(self):
        self.ids.editor_widget.clear()
        self.ids.editor_status.text = 'Select a colour \u2192 tap or drag cells to paint.  Use all N colours!'

    # -- solve & play ----------------------------------------------------------

    def solve_and_play(self):
        if self._solving:
            return
        from puzzle import validate_editor_grid, solve_puzzle

        grid = self.ids.editor_widget.get_grid()
        is_valid, error = validate_editor_grid(grid, self._n)
        if not is_valid:
            self.ids.editor_status.text = '\u26a0  ' + error
            return

        self._solving = True
        self.ids.editor_status.text = '\u23f3 Solving\u2026'

        def _run():
            puzzle = solve_puzzle(grid, self._n)
            Clock.schedule_once(lambda _dt: self._on_solved(puzzle), 0)

        threading.Thread(target=_run, daemon=True).start()

    def _on_solved(self, puzzle):
        self._solving = False
        if puzzle is None:
            self.ids.editor_status.text = (
                '\u274c No valid solution found. '
                'Try connecting your regions differently.'
            )
            return
        self.ids.editor_status.text = '\u2705 Solution found!'
        app = App.get_running_app()
        Clock.schedule_once(lambda _dt: app.start_custom_game(puzzle), 0.3)

    def go_back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'menu'


# ═══════════════════════════════════════════════════════════════════════════
# Application
# ═══════════════════════════════════════════════════════════════════════════

class QueensGambitApp(App):
    """Root application class."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.color_manager = None
        self.asset_manager = None
        self.save_manager = None
        self.current_size = 10
        self.title = "Queens Gambit"

    def build(self):
        self.color_manager = ColorManager(self.user_data_dir)
        self.asset_manager = AssetManager(self.user_data_dir)
        self.save_manager = SaveManager(self.user_data_dir)
        Builder.load_string(KV)

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(MenuScreen())
        sm.add_widget(GameScreen())
        sm.add_widget(SettingsScreen())
        sm.add_widget(LevelEditorScreen())

        # Handle Android back button / desktop Escape
        Window.bind(on_keyboard=self._on_keyboard)
        return sm

    # -- keyboard / back-button ----------------------------------------------

    def _on_keyboard(self, _window, key, *_args):
        if key == 27:  # Escape / Android back
            current = self.root.current
            if current == "game":
                self.root.get_screen("game").go_back()
                return True
            if current == "settings":
                self.root.get_screen("settings").go_back()
                return True
            if current == "level_editor":
                self.root.get_screen("level_editor").go_back()
                return True
        return False

    # -- puzzle generation ---------------------------------------------------

    def start_new_game(self, n):
        self.current_size = n

        # Try to generate; fall back to sample puzzle
        def _generate():
            puzzle = generate_puzzle(n, max_time=15)
            if puzzle is None:
                puzzle = get_sample_puzzle()
            Clock.schedule_once(lambda _dt: self._puzzle_ready(puzzle))

        threading.Thread(target=_generate, daemon=True).start()

    def start_sample_game(self):
        """Immediately start with the hardcoded sample puzzle."""
        puzzle = get_sample_puzzle()
        self._puzzle_ready(puzzle)

    def _puzzle_ready(self, puzzle):
        menu = self.root.get_screen("menu")
        menu.ids.status_label.text = ""

        # Clear any old save so we start fresh
        self.save_manager.clear_save()

        game = self.root.get_screen("game")
        game.setup_game(puzzle, self.color_manager, self.asset_manager)

        # Hook up autosave
        grid = game.ids.grid_widget
        grid.on_state_changed = lambda: self.save_manager.save_game(grid)

        self.root.transition = SlideTransition(direction="left")
        self.root.current = "game"

    def resume_saved_game(self):
        """Load the saved game and resume it on the GameScreen."""
        data = self.save_manager.load_game()
        if not data:
            return

        puzzle = data["puzzle"]
        colors = self.color_manager.get_palette(puzzle.n)

        game = self.root.get_screen("game")
        game.setup_game(puzzle, self.color_manager, self.asset_manager)

        # Restore saved state (including trial mode) on top of the fresh setup
        grid = game.ids.grid_widget
        grid.restore_state(
            puzzle=puzzle,
            colors=colors,
            marks=data["marks"],
            locked_x=data["locked_x"],
            penalized=data["penalized"],
            lives=data["lives"],
            trial_mode=data.get("trial_mode", False),
            trial_marks=data.get("trial_marks", set()),
            trial_snapshot=data.get("trial_snapshot"),
        )
        # Sync lives display after restore
        game._sync_lives()

        # Hook up autosave
        grid.on_state_changed = lambda: self.save_manager.save_game(grid)

        self.root.transition = SlideTransition(direction="left")
        self.root.current = "game"

    def start_custom_game(self, puzzle):
        """Launch the game with a user-created puzzle from the level editor."""
        self.save_manager.clear_save()

        game = self.root.get_screen("game")
        game.setup_game(puzzle, self.color_manager, self.asset_manager)

        # Hook up autosave
        grid = game.ids.grid_widget
        grid.on_state_changed = lambda: self.save_manager.save_game(grid)

        self.root.transition = SlideTransition(direction="left")
        self.root.current = "game"


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    QueensGambitApp().run()
