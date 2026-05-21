"""Main entry point for the Hand Gesture Puzzle Game."""

import time

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
    GESTURE_FIST,
    GESTURE_PEACE,
    GESTURE_PINCH,
    GESTURE_POINT,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.drawing import DrawingCanvas
from src.game_modes import ModeController
from src.gesture import HandTracker
from src.leaderboard import save_entry
from src.puzzle import PuzzleBoard
from src.renderer import Button, Renderer
from src.sounds import SoundEngine
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
        self.sound = SoundEngine()

        # Drawing canvas
        self.drawing_canvas = DrawingCanvas()
        self._drawing_was_pointing = False
        self._drawing_gesture_cooldown = 0

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

        # Completion screen state
        self._player_name = ""
        self._name_input_active = True
        self._score_saved = False

        # Menu intro sound played once
        self._intro_played = False

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
                self._handle_key(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_click(event.pos)

    def _handle_key(self, event: pygame.event.Event):
        """Handle keyboard input."""
        state = self.state_manager.state
        key = event.key

        # Handle text input for completion screen
        if state == GameState.COMPLETED and self._name_input_active:
            if key == pygame.K_RETURN:
                self._submit_score()
                return
            elif key == pygame.K_BACKSPACE:
                self._player_name = self._player_name[:-1]
                return
            elif key == pygame.K_ESCAPE:
                self._name_input_active = False
                return
            else:
                if event.unicode and event.unicode.isprintable() and len(self._player_name) < 20:
                    self._player_name += event.unicode
                return

        if key == pygame.K_ESCAPE:
            if state == GameState.PLAYING:
                self.state_manager.transition(GameState.PAUSED)
            elif state == GameState.PAUSED:
                self.state_manager.transition(GameState.PLAYING)
            elif state in (GameState.MODE_SELECT, GameState.GRID_SELECT):
                self.state_manager.transition(GameState.MENU)
                self.sound.play("swoosh")
            elif state == GameState.CAPTURING:
                self.state_manager.transition(GameState.GRID_SELECT)
            elif state == GameState.LEADERBOARD:
                self.state_manager.transition(GameState.MENU)
            elif state == GameState.DRAWING:
                self.drawing_canvas.end_stroke()
                self.state_manager.transition(GameState.MENU)
                self.sound.play("swoosh")

        elif key == pygame.K_SPACE:
            if state == GameState.CAPTURING:
                self._start_capture_countdown()

        elif key == pygame.K_r:
            if state == GameState.PLAYING:
                self._restart_puzzle()
                self.sound.play("reset")

        elif key == pygame.K_q:
            if state in (GameState.PLAYING, GameState.PAUSED, GameState.COMPLETED):
                self.state_manager.transition(GameState.MENU)
                self.sound.play("swoosh")

        # Drawing mode keyboard shortcuts
        elif state == GameState.DRAWING:
            if key == pygame.K_c:
                self.drawing_canvas.clear()
                self.sound.play("erase")
            elif key == pygame.K_z:
                self.drawing_canvas.undo()
            elif key == pygame.K_e:
                self.drawing_canvas.toggle_eraser()
            elif key == pygame.K_RIGHT:
                self.drawing_canvas.next_color()
                self.sound.play("color_change")
            elif key == pygame.K_LEFT:
                self.drawing_canvas.prev_color()
                self.sound.play("color_change")
            elif key == pygame.K_UP:
                self.drawing_canvas.increase_brush()
            elif key == pygame.K_DOWN:
                self.drawing_canvas.decrease_brush()

    def _handle_click(self, pos: tuple[int, int]):
        """Handle mouse clicks on buttons."""
        state = self.state_manager.state

        # Check leaderboard button click during gameplay
        if state == GameState.PLAYING:
            if 10 <= pos[0] <= 150 and 10 <= pos[1] <= 42:
                self.state_manager.transition(GameState.LEADERBOARD)
                return

        # Check submit arrow button on completion screen
        if state == GameState.COMPLETED and self._name_input_active:
            input_w = 300
            input_x = WINDOW_WIDTH // 2 - input_w // 2
            arrow_x = input_x + input_w + 10
            arrow_y = 380
            if arrow_x <= pos[0] <= arrow_x + 50 and arrow_y <= pos[1] <= arrow_y + 50:
                self._submit_score()
                return

            # Click on input field to activate
            if input_x <= pos[0] <= input_x + input_w and 380 <= pos[1] <= 430:
                self._name_input_active = True
                return

        for btn in self._buttons:
            if btn.contains(pos):
                self.sound.play("click")
                self._on_button_click(btn.text)
                break

    def _on_button_click(self, text: str):
        """Handle button actions."""
        state = self.state_manager.state

        if state == GameState.MENU:
            if text == "Play":
                self.state_manager.transition(GameState.MODE_SELECT)
                self.sound.play("swoosh")
            elif text == "Draw":
                self.drawing_canvas = DrawingCanvas()
                self.state_manager.transition(GameState.DRAWING)
                self.sound.play("space_whoosh")
            elif text == "Leaderboard":
                self.state_manager.transition(GameState.LEADERBOARD)
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
                self.sound.play("hack_beep")
            elif text == "Back":
                self.state_manager.transition(GameState.MODE_SELECT)

        elif state == GameState.PAUSED:
            if text == "Resume":
                self.state_manager.transition(GameState.PLAYING)
            elif text == "Restart":
                self._restart_puzzle()
                self.state_manager.transition(GameState.PLAYING)
                self.sound.play("reset")
            elif text == "Menu":
                self.state_manager.transition(GameState.MENU)

        elif state == GameState.COMPLETED:
            if text == "Skip & Play Again":
                self._reset_completion_state()
                self.state_manager.transition(GameState.MODE_SELECT)
            elif text == "Menu":
                self._reset_completion_state()
                self.state_manager.transition(GameState.MENU)

        elif state == GameState.LEADERBOARD:
            if text == "Back":
                if self.state_manager.previous_state == GameState.PLAYING:
                    self.state_manager.transition(GameState.PLAYING)
                else:
                    self.state_manager.transition(GameState.MENU)

        elif state == GameState.DRAWING:
            if text == "Clear":
                self.drawing_canvas.clear()
                self.sound.play("erase")
            elif text == "Undo":
                self.drawing_canvas.undo()
            elif text == "Eraser":
                self.drawing_canvas.toggle_eraser()
            elif text == "Back":
                self.drawing_canvas.end_stroke()
                self.state_manager.transition(GameState.MENU)
                self.sound.play("swoosh")

    def _submit_score(self):
        """Submit score to leaderboard."""
        if self._player_name.strip() and self.mode_controller is not None and not self._score_saved:
            save_entry(
                name=self._player_name.strip(),
                score=self.mode_controller.calculate_final_score(),
                time_sec=self.mode_controller.elapsed,
                mode=self.state_manager.mode.value,
                grid_size=self.state_manager.grid_size,
            )
            self._score_saved = True
            self._name_input_active = False
            self.sound.play("correct")

    def _reset_completion_state(self):
        """Reset completion screen state for next game."""
        self._player_name = ""
        self._name_input_active = True
        self._score_saved = False

    def _update(self):
        """Update game logic."""
        # Read camera frame
        if self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                self.camera_frame = frame

        state = self.state_manager.state

        if state == GameState.MENU:
            if not self._intro_played:
                self.sound.play("matrix", 0.3)
                self._intro_played = True
        elif state == GameState.CAPTURING:
            self._update_capturing()
        elif state == GameState.PLAYING:
            self._update_playing()
        elif state == GameState.DRAWING:
            self._update_drawing()

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
                self.sound.play("hack_beep")
                return
        else:
            # Check for peace gesture to trigger capture
            if self.camera_frame is not None:
                self.hand_tracker.process_frame(self.camera_frame)
                if self.hand_tracker.gesture == GESTURE_PEACE:
                    self._start_capture_countdown()
                    self.sound.play("tick")

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
                self.sound.play("alarm")
                return

        # Check fist reset
        if self.hand_tracker.fist_reset_triggered:
            self._restart_puzzle()
            self.sound.play("reset")
            return

        # Handle grab/release with hand
        currently_grabbing = self.hand_tracker.is_grabbing
        cx, cy = self.hand_tracker.cursor_pos

        if currently_grabbing and not self._was_grabbing:
            # Started grabbing
            if self.board.try_grab(cx, cy):
                self.sound.play("grab")
        elif currently_grabbing and self._was_grabbing:
            # Dragging
            self.board.drag(cx, cy)
        elif not currently_grabbing and self._was_grabbing:
            # Released
            if self.board.held_piece is not None:
                self.board.release()
                self.sound.play("drop")
                # Check if placement was correct
                if self.mode_controller is not None:
                    last_piece = self.board.pieces[-1]
                    self.mode_controller.on_piece_placed(last_piece.is_correct)
                    if last_piece.is_correct:
                        self.sound.play("correct", 0.6)
                    else:
                        self.sound.play("wrong", 0.4)

        self._was_grabbing = currently_grabbing

        # Check completion
        if self.board.completed:
            self._reset_completion_state()
            self.state_manager.transition(GameState.COMPLETED)
            self.sound.play("victory")

    def _update_drawing(self):
        """Update drawing mode with hand gestures."""
        if self.camera_frame is not None:
            self.hand_tracker.process_frame(self.camera_frame)

        if self._drawing_gesture_cooldown > 0:
            self._drawing_gesture_cooldown -= 1

        gesture = self.hand_tracker.gesture
        cx, cy = self.hand_tracker.cursor_pos

        if gesture == GESTURE_POINT:
            # Point finger = draw
            if not self._drawing_was_pointing:
                self.drawing_canvas.start_stroke()
            tick = self.drawing_canvas.draw_at(cx, cy)
            if tick:
                self.sound.play("draw_tick", 0.3)
            self._drawing_was_pointing = True
        else:
            if self._drawing_was_pointing:
                self.drawing_canvas.end_stroke()
            self._drawing_was_pointing = False

            if self._drawing_gesture_cooldown == 0:
                if gesture == GESTURE_PINCH:
                    self.drawing_canvas.next_color()
                    self.sound.play("color_change")
                    self._drawing_gesture_cooldown = 15
                elif gesture == GESTURE_PEACE:
                    self.drawing_canvas.increase_brush()
                    self._drawing_gesture_cooldown = 10
                elif gesture == GESTURE_FIST:
                    if self.hand_tracker.fist_reset_triggered:
                        self.drawing_canvas.clear()
                        self.sound.play("erase")
                        self._drawing_gesture_cooldown = 30

    def _start_capture_countdown(self):
        """Start 3-second countdown before capture."""
        self._capture_countdown = 3
        self._capture_start_time = time.time()
        self.sound.play("tick")

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
        self.sound.play("space_whoosh", 0.5)

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
        elif state == GameState.LEADERBOARD:
            self._render_leaderboard()
        elif state == GameState.DRAWING:
            self._render_drawing()

    def _render_menu(self):
        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        y_start = 280
        gap = BUTTON_HEIGHT + BUTTON_MARGIN
        self._buttons = [
            Button("Play", center_x, y_start),
            Button("Draw", center_x, y_start + gap),
            Button("Leaderboard", center_x, y_start + 2 * gap),
            Button("Quit", center_x, y_start + 3 * gap),
        ]
        # Style the Draw button differently
        self._buttons[1].color = COLOR_HIGHLIGHT
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
            frame = generate_sample_image()

        self.renderer.draw_capturing(frame, countdown)

        if not self.use_camera:
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
            Button("Skip & Play Again", center_x, 460),
        ]
        if self.mode_controller is not None:
            self.renderer.draw_completed(
                self.board,
                self.mode_controller,
                self._buttons,
                self._player_name,
                self._name_input_active,
            )

    def _render_leaderboard(self):
        center_x = WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2
        self._buttons = [
            Button("Back", center_x, WINDOW_HEIGHT - 80),
        ]
        self.renderer.draw_leaderboard(self._buttons)

    def _render_drawing(self):
        btn_w = 100
        btn_h = 36
        btn_y = 50
        gap = btn_w + 10
        start_x = 10

        self._buttons = [
            Button("Clear", start_x, btn_y, btn_w, btn_h),
            Button("Undo", start_x + gap, btn_y, btn_w, btn_h),
            Button("Eraser", start_x + 2 * gap, btn_y, btn_w, btn_h),
            Button("Back", WINDOW_WIDTH - btn_w - 10, btn_y, btn_w, btn_h),
        ]

        self.renderer.draw_drawing_mode(
            self.drawing_canvas,
            self.hand_tracker,
            self.camera_frame,
            self._buttons,
        )

    def _cleanup(self):
        """Release resources."""
        self.hand_tracker.release()
        if self.camera is not None:
            self.camera.release()
        self.sound.stop_all()
        self.renderer.quit()


def main():
    """Entry point."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
