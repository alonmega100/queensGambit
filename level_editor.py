"""
Queens Gambit - Level Editor Widget
"""
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty


class _PaletteSwatch(Widget):
    selected = BooleanProperty(False)

    def __init__(self, rgba, index, on_select_cb, **kw):
        super().__init__(size_hint=(None, None), size=(dp(44), dp(44)), **kw)
        self._rgba = rgba
        self._index = index
        self._on_select_cb = on_select_cb
        self.bind(pos=self._draw, size=self._draw, selected=self._draw)
        Clock.schedule_once(self._draw, 0)

    def _draw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            if self.selected:
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
                margin = dp(4)
                Color(*self._rgba)
                RoundedRectangle(
                    pos=(self.x + margin, self.y + margin),
                    size=(self.width - 2 * margin, self.height - 2 * margin),
                    radius=[dp(5)],
                )
            else:
                Color(*self._rgba)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._on_select_cb(self._index)
            return True
        return False


class LevelEditorWidget(Widget):
    selected_color = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._n = 8
        self._grid = [[-1] * 8 for _ in range(8)]
        self._colors = []
        self._redraw_trigger = Clock.create_trigger(self._redraw, 0)
        self.bind(pos=self._request_redraw, size=self._request_redraw)

    def setup(self, n, colors):
        self._n = n
        self._colors = list(colors)
        self._grid = [[-1] * n for _ in range(n)]
        self._request_redraw()

    def clear(self):
        self._grid = [[-1] * self._n for _ in range(self._n)]
        self._request_redraw()

    def get_grid(self):
        return [row[:] for row in self._grid]

    def _metrics(self):
        n = self._n
        if n == 0 or self.width <= 0 or self.height <= 0:
            return None
        padding = dp(12)
        available = min(self.width, self.height) - 2 * padding
        if available <= 0:
            return None
        cell = available / n
        gw = cell * n
        return {"n": n, "cell": cell,
                "ox": self.x + (self.width - gw) / 2,
                "oy": self.y + (self.height - gw) / 2}

    def _pos_to_cell(self, pos):
        m = self._metrics()
        if m is None:
            return None
        col = int((pos[0] - m["ox"]) / m["cell"])
        screen_row = int((pos[1] - m["oy"]) / m["cell"])
        row = m["n"] - 1 - screen_row
        if 0 <= row < m["n"] and 0 <= col < m["n"]:
            return (row, col)
        return None

    def _paint(self, touch_pos):
        cell = self._pos_to_cell(touch_pos)
        if cell:
            r, c = cell
            self._grid[r][c] = self.selected_color
            self._request_redraw()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._paint(touch.pos)
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._paint(touch.pos)
        return True

    def _request_redraw(self, *_args):
        self._redraw_trigger()

    def _redraw(self, *_args):
        self.canvas.clear()
        m = self._metrics()
        if m is None:
            return
        n = m["n"]
        cs = m["cell"]
        gap = dp(1.5)
        with self.canvas:
            Color(0.09, 0.09, 0.11, 1)
            Rectangle(pos=self.pos, size=self.size)
            for r in range(n):
                for c in range(n):
                    x = m["ox"] + c * cs
                    y = m["oy"] + (n - 1 - r) * cs
                    ci = self._grid[r][c]
                    if 0 <= ci < len(self._colors):
                        Color(*self._colors[ci])
                    else:
                        shade = 0.19 if (r + c) % 2 == 0 else 0.24
                        Color(shade, shade, shade + 0.03, 1)
                    RoundedRectangle(
                        pos=(x + gap, y + gap),
                        size=(cs - 2 * gap, cs - 2 * gap),
                        radius=[dp(3)],
                    )
            Color(0.40, 0.40, 0.45, 1)
            Line(rectangle=(m["ox"], m["oy"], n * cs, n * cs), width=dp(1.5))
            Color(0.18, 0.18, 0.22, 1)
            for i in range(1, n):
                x = m["ox"] + i * cs
                Line(points=[x, m["oy"], x, m["oy"] + n * cs], width=dp(0.8))
                y = m["oy"] + i * cs
                Line(points=[m["ox"], y, m["ox"] + n * cs, y], width=dp(0.8))
