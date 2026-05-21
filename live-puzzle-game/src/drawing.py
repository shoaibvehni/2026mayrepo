"""Freehand drawing canvas controlled by hand gestures."""

import pygame

from src.config import WINDOW_WIDTH, WINDOW_HEIGHT


# Drawing colors palette
DRAW_COLORS = [
    ("Red", (255, 60, 60)),
    ("Green", (60, 255, 100)),
    ("Blue", (80, 140, 255)),
    ("Yellow", (255, 230, 50)),
    ("Cyan", (0, 255, 220)),
    ("Magenta", (255, 60, 200)),
    ("Orange", (255, 160, 40)),
    ("White", (240, 240, 240)),
    ("Purple", (160, 80, 255)),
    ("Pink", (255, 130, 180)),
    ("Lime", (180, 255, 60)),
    ("Neon Blue", (30, 200, 255)),
]

BRUSH_SIZES = [2, 4, 6, 10, 16, 24]

ERASER_COLOR = (0, 0, 0, 0)


class DrawingCanvas:
    """A full-screen drawing canvas controlled by hand gestures."""

    def __init__(self):
        self.surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self.surface.fill((0, 0, 0, 0))

        self.color_index = 0
        self.brush_index = 2
        self.is_erasing = False

        self._prev_point: tuple[int, int] | None = None
        self._drawing = False

        # Undo stack (store surface copies)
        self._undo_stack: list[pygame.Surface] = []
        self._max_undo = 20

        # Stroke counter for sound throttling
        self._stroke_tick = 0

    @property
    def current_color(self) -> tuple[int, int, int]:
        return DRAW_COLORS[self.color_index][1]

    @property
    def current_color_name(self) -> str:
        return DRAW_COLORS[self.color_index][0]

    @property
    def brush_size(self) -> int:
        return BRUSH_SIZES[self.brush_index]

    def next_color(self):
        """Cycle to next color."""
        self.color_index = (self.color_index + 1) % len(DRAW_COLORS)
        self.is_erasing = False

    def prev_color(self):
        """Cycle to previous color."""
        self.color_index = (self.color_index - 1) % len(DRAW_COLORS)
        self.is_erasing = False

    def increase_brush(self):
        """Increase brush size."""
        self.brush_index = min(self.brush_index + 1, len(BRUSH_SIZES) - 1)

    def decrease_brush(self):
        """Decrease brush size."""
        self.brush_index = max(self.brush_index - 1, 0)

    def toggle_eraser(self):
        """Toggle eraser mode."""
        self.is_erasing = not self.is_erasing

    def start_stroke(self):
        """Begin a new stroke (save undo state)."""
        if not self._drawing:
            self._save_undo()
            self._drawing = True
            self._prev_point = None

    def end_stroke(self):
        """End the current stroke."""
        self._drawing = False
        self._prev_point = None

    def draw_at(self, x: int, y: int) -> bool:
        """Draw at position. Returns True if a tick sound should play."""
        if not self._drawing:
            return False

        should_tick = False
        self._stroke_tick += 1

        if self.is_erasing:
            pygame.draw.circle(
                self.surface, (0, 0, 0, 0), (x, y), self.brush_size * 2
            )
            eraser_rect = pygame.Rect(
                x - self.brush_size * 2, y - self.brush_size * 2,
                self.brush_size * 4, self.brush_size * 4,
            )
            self.surface.fill((0, 0, 0, 0), eraser_rect)
        else:
            color = self.current_color + (255,)
            if self._prev_point is not None:
                dx = x - self._prev_point[0]
                dy = y - self._prev_point[1]
                dist = max(1, int((dx ** 2 + dy ** 2) ** 0.5))
                for i in range(dist):
                    frac = i / dist
                    px = int(self._prev_point[0] + dx * frac)
                    py = int(self._prev_point[1] + dy * frac)
                    pygame.draw.circle(self.surface, color, (px, py), self.brush_size)
                if self._stroke_tick % 8 == 0:
                    should_tick = True
            else:
                pygame.draw.circle(self.surface, color, (x, y), self.brush_size)
                should_tick = True

        self._prev_point = (x, y)
        return should_tick

    def clear(self):
        """Clear the entire canvas."""
        self._save_undo()
        self.surface.fill((0, 0, 0, 0))

    def undo(self):
        """Undo the last stroke."""
        if self._undo_stack:
            self.surface = self._undo_stack.pop()

    def _save_undo(self):
        """Save current surface state for undo."""
        self._undo_stack.append(self.surface.copy())
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    def get_surface(self) -> pygame.Surface:
        """Return the drawing surface for rendering."""
        return self.surface
