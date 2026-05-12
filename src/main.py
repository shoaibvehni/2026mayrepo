"""Main entry point for the Hand Gesture Puzzle Game."""

import sys
import time

import cv2
import numpy as np
import pygame

from src.config import (
    BUTTON_HEIGHT,
    BUTTON_MARGIN,
    BUTTON_WIDTH,
    COLOR_ACCENT,
    COLOR_CHAOS,
    COLOR_HIGHLIGHT,
    COLOR_TIMER,
    GESTURE_PEACE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.game_modes import ModeController
from src.gesture import HandTracker
from src.puzzle import PuzzleBoard
from src.renderer import Button, Renderer
from src.state import GameMode, GameState, StateManager
from src.utils import capture_from_camera, generate_sample_image


class Game:
    """Main game controller."""

    def __init__(self):
        self.renderer = Renderer()
        self.state_manager = StateManager()
        self.hand_tracker = HandTracker()
        self.board = PuzzleBoard()
        self.mode_controller: ModeController | None = None

        # Camera
        self.camera = capture_from_camera()
        self.camera_frame: np.ndarray | None = None
        self.use_camera = self.camera is not None

        # Capture state
        self._capture_countdown = 0
        self._capture_start_time = 0.0
        self._captured_image: np.ndarray | None = None

        # UI buttons (created per screen)
        self._buttons: list[Button] = []

        # Grab state tracking
        self._was_grabbing = False

        self.running = True

    def run(self):
        """Main game loop."""
        while self.running:
            self._handle_events()
            self._update()
            self._render()
            self.renderer.flip()

        self._cleanup()

    def _handle_events(self):
        """Handle PyGame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_click(event.pos)

    def _handle_key(self, key: int):
        """Handle keyboard input."""
        state = self.state_manager.state

        if key == pygame.K_ESCAPE:
            if state == GameState.PLAYING:
                self.state_manager.transition(GameState.PAUSED)
            elif state == GameState.PAUSED:
                self.state_manager.transition(GameState.PLAYING)
            elif state in (GameState.MODE_SELECT, GameState.GRID_SELECT):
                self.state_manager.transition(GameState.MENU)
            elif state == GameState.CAPTURING:
                self.state_manager.transition(GameState.GRID_SELECT)

        elif key == pygame.K_SPACE:
            if state == GameState.CAPTURING:
                self._start_capture_countdown()

        elif key == pygame.K_r:
            if state == GameState.PLAYING:
                self._restart_puzzle()

        elif key == pygame.K_q:
            if state in (GameState.PLAYING, GameState.PAUSED, GameState.COMPLETED):
                self.state_manager.transition(GameState.MENU)

    def _handle_click(self, pos: tuple[int, int]):
        """Handle mouse clicks on buttons."""
        for btn in self._buttons:
            if btn.contains(pos):
                self._on_button_click(btn.text)
                break

    def _on_button_click(self, text: str):
        """Handle button actions."""
        state = self.state_manager.state

        if state == GameState.MENU:
            if text == "Play":
                self.state_manager.transition(GameState.MODE_SELECT)
            elif text == "Quit":
                self.running = False

        elif state == GameState.MODE_SELECT:
            if text == "Classic Mode":
                self.state_manager.set_mode(GameMode.CLASSIC)
                self.state_manager.transition(GameState.GRID_SELECT)
            elif text == "Chaos Mode":
                self.state_manager.set_mode(GameMode.CHAOS)
                self.state_manager.transition(GameState.GRID_SELECT)
            elif text == "Time Attack":
                self.state_manager.set_mode(GameMode.TIME_ATTACK)
                self.state_manager.transition(GameState.GRID_SELECT)
            elif text == "Back":
                self.state_manager.transition(GameState.MENU)

        elif state == GameState.GRID_SELECT:
            if text == "<<":
                self.state_manager.set_grid_size(self.state_manager.grid_size - 1)
            elif text == ">>":
                self.state_manager.set_grid_size(self.state_manager.grid_size + 1)
            elif text == "Start":
                self.state_manager.transition(GameState.CAPTURING)
            elif text == "Back":
                self.state_manager.transition(GameState.MODE_SELECT)

        elif state == GameState.PAUSED:
            if text == "Resume":
                self.state_manager.transition(GameState.PLAYING)
            elif text == "Restart":
                self._restart_puzzle()
                self.state_manager.transition(GameState.PLAYING)
            elif text == "Menu":
                self.state_manager.transition(GameState.MENU)

        elif state == GameState.COMPLETED:
            if text == "Play Again":
                self.state_manager.transition(GameState.MODE_SELECT)
            elif text == "Menu":
                self.state_manager.transition(GameState.MENU)

    def _update(self):
        """Update game logic."""
        # Read camera frame
        if self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                self.camera_frame = frame

        state = self.state_manager.state

        if state == GameState.CAPTURING:
            self._update_capturing()
        elif state == GameState.PLAYING:
            self._update_playing()

    def _update_capturing(self):
        """Update capture countdown."""
        if self._capture_countdown > 0:
            elapsed = time.time() - self._capture_start_time
            remaining = self._capture_countdown - elapsed
            if remaining <= 0:
                # Capture the image
                if self.camera_frame is not None:
                    self._captured_image = self.camera_frame.copy()
                else:
                    self._captured_image = generate_sample_image()
                self._start_game()
                return
        else:
            # Check for peace gesture to trigger capture
            if self.camera_frame is not None:
                self.hand_tracker.process_frame(self.camera_frame)
                if self.hand_tracker.gesture == GESTURE_PEACE:
                    self._start_capture_countdown()

    def _update_playing(self):
        """Update game play logic."""
        if self.camera_frame is not None:
            self.hand_tracker.process_frame(self.camera_frame)

        # Update mode controller
        if self.mode_controller is not None:
            self.mode_controller.update()

            # Check time up
            if self.mode_controller.time_up:
                self.state_manager.transition(GameState.COMPLETED)
                return

        # Handle grab/release with hand
        currently_grabbing = self.hand_tracker.is_grabbing
        cx, cy = self.hand_tracker.cursor_pos

        if currently_grabbing and not self._was_grabbing:
            # Started grabbing
            self.board.try_grab(cx, cy)
        elif currently_grabbing and self._was_grabbing:
            # Dragging
            self.board.drag(cx, cy)
        elif not currently_grabbing and self._was_grabbing:
            # Released
            if self.board.held_piece is not None:
                was_correct_before = self.board.held_piece.is_correct
                self.board.release()
                # Check if placement was correct
                if self.mode_controller is not None:
                    # Find the piece we just released (it's at end of list)
                    last_piece = self.board.pieces[-1]
                    self.mode_controller.on_piece_placed(last_piece.is_correct)

        self._was_grabbing = currently_grabbing

        # Check completion
        if self.board.completed:
            self.state_manager.transition(GameState.COMPLETED)

    def _start_capture_countdown(self):
        """Start 3-second countdown before capture."""
        self._capture_countdown = 3
        self._capture_start_time = time.time()

    def _start_game(self):
        """Initialize puzzle and start the game."""
        grid_size = self.state_manager.grid_size

        if self._captured_image is not None:
            self.board = PuzzleBoard(grid_size)
            self.board.create_from_image(self._captured_image)
        else:
            self.board = PuzzleBoard(grid_size)
            img = generate_sample_image()
            self.board.create_from_image(img)

        self.board.shuffle()
        self.mode_controller = ModeController(self.state_manager.mode, self.board)
        self._was_grabbing = False
        self.state_manager.transition(GameState.PLAYING)

    def _restart_puzzle(self):
        """Restart current puzzle."""
        self.board.shuffle()
        self.mode_controller = ModeController(self.state_manager.mode, self.board)
        self._was_grabbing = False

    def _render(self):
        """Render current state."""
        state = self.state_manager.state

        if state == GameState.MENU:
            self._render_menu()
        elif state == GameState.MODE_SELECT:
            self._render_mode_select()
        elif state == GameState.GRID_SELECT:
            self._render_grid_select()
        elif state == GameState.CAPTURING:
            self._render_capturing()
        elif state == GameState.PLAYING:
            self._render_playing()
        elif state == GameState.PAUSED:
            self._render_paused()
        elif state == GameState.COMPLETED:
            self._render_completed()

    def _render_menu(self):
        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        self._buttons = [
            Button("Play", center_x, 320),
            Button("Quit", center_x, 320 + BUTTON_HEIGHT + BUTTON_MARGIN),
        ]
        self.renderer.draw_menu(self.state_manager, self._buttons)

    def _render_mode_select(self):
        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        y_start = 200
        gap = BUTTON_HEIGHT + BUTTON_MARGIN

        mode_buttons = [
            ("Classic Mode", COLOR_ACCENT),
            ("Chaos Mode", COLOR_CHAOS),
            ("Time Attack", COLOR_TIMER),
        ]

        self._buttons = []
        for i, (label, color) in enumerate(mode_buttons):
            btn = Button(label, center_x, y_start + i * gap)
            btn.color = color
            self._buttons.append(btn)

        self._buttons.append(
            Button("Back", center_x, y_start + len(mode_buttons) * gap + 20)
        )
        self.renderer.draw_mode_select(self._buttons)

    def _render_grid_select(self):
        center_x = WINDOW_WIDTH // 2
        arrow_w = 80

        self._buttons = [
            Button("<<", center_x - 200, 240, arrow_w, BUTTON_HEIGHT),
            Button(">>", center_x + 120, 240, arrow_w, BUTTON_HEIGHT),
            Button("Start", center_x - BUTTON_WIDTH // 2, 400),
            Button("Back", center_x - BUTTON_WIDTH // 2, 400 + BUTTON_HEIGHT + BUTTON_MARGIN),
        ]
        self.renderer.draw_grid_select(self.state_manager.grid_size, self._buttons)

    def _render_capturing(self):
        countdown = 0
        if self._capture_countdown > 0:
            elapsed = time.time() - self._capture_start_time
            countdown = max(0, int(self._capture_countdown - elapsed) + 1)

        frame = self.camera_frame
        if frame is None:
            # No camera — use sample image as preview
            frame = generate_sample_image()

        self.renderer.draw_capturing(frame, countdown)

        if not self.use_camera:
            # Auto-start with sample image after brief delay
            if self._capture_countdown == 0:
                self._captured_image = generate_sample_image()
                self._capture_countdown = 2
                self._capture_start_time = time.time()

    def _render_playing(self):
        self._buttons = []
        if self.mode_controller is not None:
            self.renderer.draw_game(
                self.board,
                self.hand_tracker,
                self.mode_controller,
                self.camera_frame,
            )

    def _render_paused(self):
        # First draw the game underneath
        if self.mode_controller is not None:
            self.renderer.draw_game(
                self.board,
                self.hand_tracker,
                self.mode_controller,
                self.camera_frame,
            )

        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        self._buttons = [
            Button("Resume", center_x, 320),
            Button("Restart", center_x, 320 + BUTTON_HEIGHT + BUTTON_MARGIN),
            Button("Menu", center_x, 320 + 2 * (BUTTON_HEIGHT + BUTTON_MARGIN)),
        ]
        self.renderer.draw_paused(self._buttons)

    def _render_completed(self):
        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        self._buttons = [
            Button("Play Again", center_x, 530),
            Button("Menu", center_x, 530 + BUTTON_HEIGHT + BUTTON_MARGIN),
        ]
        if self.mode_controller is not None:
            self.renderer.draw_completed(
                self.board, self.mode_controller, self._buttons
            )

    def _cleanup(self):
        """Release resources."""
        self.hand_tracker.release()
        if self.camera is not None:
            self.camera.release()
        self.renderer.quit()


def main():
    """Entry point."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
