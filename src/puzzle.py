"""Puzzle engine: image splitting, shuffling, snap-to-grid, completion."""

import random

import cv2
import numpy as np
import pygame

from src.config import PIECE_PADDING, SNAP_THRESHOLD, WINDOW_HEIGHT, WINDOW_WIDTH


class PuzzlePiece:
    """A single puzzle piece."""

    def __init__(
        self,
        piece_id: int,
        image: np.ndarray,
        correct_row: int,
        correct_col: int,
        piece_width: int,
        piece_height: int,
    ):
        self.piece_id = piece_id
        self.image = image
        self.correct_row = correct_row
        self.correct_col = correct_col
        self.piece_width = piece_width
        self.piece_height = piece_height

        # Current position (pixel coordinates)
        self.x = 0.0
        self.y = 0.0

        # Current grid position
        self.current_row = correct_row
        self.current_col = correct_col

        self.is_placed = False
        self.is_correct = False
        self.rotation = 0  # degrees (0, 90, 180, 270)

        # For chaos mode movement
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        # PyGame surface (created lazily)
        self._surface = None

    @property
    def surface(self) -> pygame.Surface:
        if self._surface is None:
            self._surface = self._create_surface()
        return self._surface

    def _create_surface(self) -> pygame.Surface:
        """Convert OpenCV image to PyGame surface."""
        img_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        img_rgb = np.rot90(img_rgb)
        img_rgb = np.flipud(img_rgb)
        surface = pygame.surfarray.make_surface(img_rgb)
        return pygame.transform.scale(surface, (self.piece_width, self.piece_height))

    def invalidate_surface(self):
        """Force surface recreation (after rotation etc.)."""
        self._surface = None

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.piece_width / 2, self.y + self.piece_height / 2)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.piece_width, self.piece_height)

    def contains_point(self, px: int, py: int) -> bool:
        return (
            self.x <= px <= self.x + self.piece_width
            and self.y <= py <= self.y + self.piece_height
        )

    def move_to(self, x: float, y: float):
        self.x = x
        self.y = y

    def center_on(self, cx: float, cy: float):
        self.x = cx - self.piece_width / 2
        self.y = cy - self.piece_height / 2


class PuzzleBoard:
    """Manages the puzzle grid, pieces, and game logic."""

    def __init__(self, grid_size: int = 3):
        self.grid_size = grid_size
        self.pieces: list[PuzzlePiece] = []
        self.board_x = 0
        self.board_y = 0
        self.board_width = 0
        self.board_height = 0
        self.piece_width = 0
        self.piece_height = 0
        self.original_image = None
        self._held_piece: PuzzlePiece | None = None
        self.moves = 0
        self.completed = False

    def create_from_image(self, image: np.ndarray):
        """Split image into grid pieces and set up the board."""
        self.original_image = image.copy()
        h, w = image.shape[:2]

        # Calculate board area (centered, leaving space for UI)
        max_board_w = int(WINDOW_WIDTH * 0.7)
        max_board_h = int(WINDOW_HEIGHT * 0.8)

        # Maintain aspect ratio
        scale = min(max_board_w / w, max_board_h / h)
        self.board_width = int(w * scale)
        self.board_height = int(h * scale)
        self.board_x = (WINDOW_WIDTH - self.board_width) // 2
        self.board_y = (WINDOW_HEIGHT - self.board_height) // 2 + 30

        self.piece_width = self.board_width // self.grid_size
        self.piece_height = self.board_height // self.grid_size

        # Resize image to match board
        resized = cv2.resize(image, (self.board_width, self.board_height))

        # Split into pieces
        self.pieces.clear()
        piece_id = 0
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                y1 = row * self.piece_height
                y2 = y1 + self.piece_height
                x1 = col * self.piece_width
                x2 = x1 + self.piece_width

                piece_img = resized[y1:y2, x1:x2].copy()
                piece = PuzzlePiece(
                    piece_id=piece_id,
                    image=piece_img,
                    correct_row=row,
                    correct_col=col,
                    piece_width=self.piece_width - PIECE_PADDING,
                    piece_height=self.piece_height - PIECE_PADDING,
                )
                self.pieces.append(piece)
                piece_id += 1

        self._place_pieces_on_grid()

    def _place_pieces_on_grid(self):
        """Position all pieces at their current grid positions."""
        for piece in self.pieces:
            gx = self.board_x + piece.current_col * self.piece_width + PIECE_PADDING // 2
            gy = self.board_y + piece.current_row * self.piece_height + PIECE_PADDING // 2
            piece.move_to(gx, gy)

    def shuffle(self):
        """Randomly shuffle piece grid positions."""
        positions = [
            (piece.current_row, piece.current_col) for piece in self.pieces
        ]
        random.shuffle(positions)

        for piece, (row, col) in zip(self.pieces, positions):
            piece.current_row = row
            piece.current_col = col
            piece.is_correct = (
                row == piece.correct_row and col == piece.correct_col
            )
            piece.is_placed = False

        self._place_pieces_on_grid()
        self.moves = 0
        self.completed = False

    def try_grab(self, cursor_x: int, cursor_y: int) -> bool:
        """Try to grab a piece at cursor position."""
        if self._held_piece is not None:
            return True

        # Check pieces in reverse order (top pieces first)
        for piece in reversed(self.pieces):
            if piece.contains_point(cursor_x, cursor_y):
                self._held_piece = piece
                # Move to end of list to render on top
                self.pieces.remove(piece)
                self.pieces.append(piece)
                return True
        return False

    def drag(self, cursor_x: int, cursor_y: int):
        """Move the held piece to follow cursor."""
        if self._held_piece is not None:
            self._held_piece.center_on(cursor_x, cursor_y)

    def release(self) -> bool:
        """Release held piece, snap to nearest grid slot. Returns True if snapped."""
        if self._held_piece is None:
            return False

        piece = self._held_piece
        self._held_piece = None

        # Find nearest grid slot
        rel_x = piece.center[0] - self.board_x
        rel_y = piece.center[1] - self.board_y

        target_col = int(rel_x / self.piece_width)
        target_row = int(rel_y / self.piece_height)

        target_col = max(0, min(self.grid_size - 1, target_col))
        target_row = max(0, min(self.grid_size - 1, target_row))

        # Check snap distance
        snap_x = self.board_x + target_col * self.piece_width + self.piece_width / 2
        snap_y = self.board_y + target_row * self.piece_height + self.piece_height / 2

        dist = (
            (piece.center[0] - snap_x) ** 2 + (piece.center[1] - snap_y) ** 2
        ) ** 0.5
        snap_dist = min(self.piece_width, self.piece_height) * SNAP_THRESHOLD

        if dist <= snap_dist:
            # Find piece currently at target position and swap
            for other in self.pieces:
                if other is not piece and other.current_row == target_row and other.current_col == target_col:
                    # Swap grid positions
                    other.current_row = piece.current_row
                    other.current_col = piece.current_col
                    other_gx = self.board_x + other.current_col * self.piece_width + PIECE_PADDING // 2
                    other_gy = self.board_y + other.current_row * self.piece_height + PIECE_PADDING // 2
                    other.move_to(other_gx, other_gy)
                    other.is_correct = (
                        other.current_row == other.correct_row
                        and other.current_col == other.correct_col
                    )
                    break

            piece.current_row = target_row
            piece.current_col = target_col
            self.moves += 1

        # Snap piece to its grid position
        gx = self.board_x + piece.current_col * self.piece_width + PIECE_PADDING // 2
        gy = self.board_y + piece.current_row * self.piece_height + PIECE_PADDING // 2
        piece.move_to(gx, gy)
        piece.is_correct = (
            piece.current_row == piece.correct_row
            and piece.current_col == piece.correct_col
        )

        self._check_completion()
        return True

    def _check_completion(self):
        """Check if all pieces are in correct positions."""
        self.completed = all(p.is_correct for p in self.pieces)

    @property
    def held_piece(self) -> PuzzlePiece | None:
        return self._held_piece

    @property
    def correct_count(self) -> int:
        return sum(1 for p in self.pieces if p.is_correct)

    @property
    def total_pieces(self) -> int:
        return len(self.pieces)

    def get_grid_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.board_x, self.board_y, self.board_width, self.board_height
        )

    def create_from_default(self):
        """Create puzzle from a generated gradient image (no camera needed)."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        for y in range(480):
            for x in range(640):
                img[y, x] = [
                    int(255 * x / 640),
                    int(255 * y / 480),
                    int(255 * (1 - x / 640)),
                ]
        self.create_from_image(img)
