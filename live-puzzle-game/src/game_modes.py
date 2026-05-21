"""Game mode logic: Classic, Chaos, Time Attack."""

import random
import time

from src.config import (
    CHAOS_MOVE_SPEED,
    CHAOS_SHUFFLE_INTERVAL,
    PIECE_PADDING,
    TIME_ATTACK_DURATION,
)
from src.puzzle import PuzzleBoard
from src.state import GameMode


class ModeController:
    """Controls game mode-specific behavior."""

    def __init__(self, mode: GameMode, board: PuzzleBoard):
        self.mode = mode
        self.board = board
        self.start_time = time.time()
        self.elapsed = 0.0
        self.time_limit = TIME_ATTACK_DURATION if mode == GameMode.TIME_ATTACK else 0
        self.time_up = False
        self.score = 0
        self.combo = 0

        # Chaos mode state
        self._last_chaos_time = time.time()
        self._chaos_warning = False
        self._chaos_countdown = 0.0
        self._wandering_pieces: list[int] = []

    def update(self):
        """Update mode-specific logic each frame."""
        self.elapsed = time.time() - self.start_time

        if self.mode == GameMode.TIME_ATTACK:
            self._update_time_attack()
        elif self.mode == GameMode.CHAOS:
            self._update_chaos()

    def _update_time_attack(self):
        """Check time limit for Time Attack mode."""
        remaining = self.time_limit - self.elapsed
        if remaining <= 0:
            self.time_up = True

    def _update_chaos(self):
        """Chaos mode: periodically disturb pieces."""
        now = time.time()
        time_since_chaos = now - self._last_chaos_time

        # Warning before chaos event
        if time_since_chaos > CHAOS_SHUFFLE_INTERVAL - 2.0:
            self._chaos_warning = True
            self._chaos_countdown = max(0, CHAOS_SHUFFLE_INTERVAL - time_since_chaos)

        if time_since_chaos >= CHAOS_SHUFFLE_INTERVAL:
            self._trigger_chaos()
            self._last_chaos_time = now
            self._chaos_warning = False

        # Move wandering pieces
        self._move_wandering_pieces()

    def _trigger_chaos(self):
        """Execute a chaos event."""
        if self.board.held_piece is not None:
            return

        event = random.choice(["swap", "wander", "rotate_shuffle"])

        if event == "swap":
            # Swap two random non-correct pieces
            movable = [
                p for p in self.board.pieces if not p.is_correct
            ]
            if len(movable) >= 2:
                a, b = random.sample(movable, 2)
                a.current_row, b.current_row = b.current_row, a.current_row
                a.current_col, b.current_col = b.current_col, a.current_col
                # Update positions
                for p in [a, b]:
                    gx = self.board.board_x + p.current_col * self.board.piece_width + PIECE_PADDING // 2
                    gy = self.board.board_y + p.current_row * self.board.piece_height + PIECE_PADDING // 2
                    p.move_to(gx, gy)
                    p.is_correct = (
                        p.current_row == p.correct_row
                        and p.current_col == p.correct_col
                    )

        elif event == "wander":
            # Make some pieces drift from their grid positions
            movable = [p for p in self.board.pieces if not p.is_correct]
            count = min(3, len(movable))
            if count > 0:
                wanderers = random.sample(movable, count)
                self._wandering_pieces = [p.piece_id for p in wanderers]
                for p in wanderers:
                    p.velocity_x = random.uniform(-CHAOS_MOVE_SPEED, CHAOS_MOVE_SPEED)
                    p.velocity_y = random.uniform(-CHAOS_MOVE_SPEED, CHAOS_MOVE_SPEED)

        elif event == "rotate_shuffle":
            # Shuffle a row or column
            movable = [p for p in self.board.pieces if not p.is_correct]
            if len(movable) >= 2:
                if random.random() < 0.5:
                    # Shuffle a row
                    row = random.randint(0, self.board.grid_size - 1)
                    row_pieces = [
                        p for p in self.board.pieces
                        if p.current_row == row and not p.is_correct
                    ]
                    if len(row_pieces) >= 2:
                        cols = [p.current_col for p in row_pieces]
                        random.shuffle(cols)
                        for p, col in zip(row_pieces, cols):
                            p.current_col = col
                            gx = self.board.board_x + col * self.board.piece_width + PIECE_PADDING // 2
                            gy = self.board.board_y + p.current_row * self.board.piece_height + PIECE_PADDING // 2
                            p.move_to(gx, gy)
                            p.is_correct = (
                                p.current_row == p.correct_row
                                and p.current_col == p.correct_col
                            )

    def _move_wandering_pieces(self):
        """Animate wandering pieces and snap them back after a while."""
        to_remove = []
        for pid in self._wandering_pieces:
            piece = next((p for p in self.board.pieces if p.piece_id == pid), None)
            if piece is None:
                to_remove.append(pid)
                continue

            piece.x += piece.velocity_x
            piece.y += piece.velocity_y

            # Bounce off board boundaries
            if piece.x < self.board.board_x or piece.x + piece.piece_width > self.board.board_x + self.board.board_width:
                piece.velocity_x *= -1
            if piece.y < self.board.board_y or piece.y + piece.piece_height > self.board.board_y + self.board.board_height:
                piece.velocity_y *= -1

            # Slow down and snap back
            piece.velocity_x *= 0.98
            piece.velocity_y *= 0.98
            if abs(piece.velocity_x) < 0.1 and abs(piece.velocity_y) < 0.1:
                # Snap back to grid
                gx = self.board.board_x + piece.current_col * self.board.piece_width + PIECE_PADDING // 2
                gy = self.board.board_y + piece.current_row * self.board.piece_height + PIECE_PADDING // 2
                piece.move_to(gx, gy)
                piece.velocity_x = 0
                piece.velocity_y = 0
                to_remove.append(pid)

        for pid in to_remove:
            if pid in self._wandering_pieces:
                self._wandering_pieces.remove(pid)

    def on_piece_placed(self, is_correct: bool):
        """Called when a piece is placed. Updates score and combo."""
        if is_correct:
            self.combo += 1
            base_score = 100
            combo_bonus = self.combo * 25
            time_bonus = 0

            if self.mode == GameMode.TIME_ATTACK:
                remaining = max(0, self.time_limit - self.elapsed)
                time_bonus = int(remaining * 2)

            self.score += base_score + combo_bonus + time_bonus
        else:
            self.combo = 0

    @property
    def remaining_time(self) -> float:
        if self.mode != GameMode.TIME_ATTACK:
            return -1
        return max(0, self.time_limit - self.elapsed)

    @property
    def chaos_warning(self) -> bool:
        return self._chaos_warning

    @property
    def chaos_countdown(self) -> float:
        return self._chaos_countdown

    def calculate_final_score(self) -> int:
        """Calculate final score on puzzle completion."""
        base = self.score
        time_bonus = 0
        move_bonus = 0

        if self.mode == GameMode.TIME_ATTACK:
            time_bonus = int(self.remaining_time * 10)

        optimal_moves = self.board.total_pieces
        if self.board.moves <= optimal_moves * 2:
            move_bonus = (optimal_moves * 2 - self.board.moves) * 50

        if self.mode == GameMode.CHAOS:
            base = int(base * 1.5)  # chaos multiplier

        return base + time_bonus + move_bonus
