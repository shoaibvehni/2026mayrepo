"""PyGame rendering engine for the puzzle game."""

import random

import cv2
import numpy as np
import pygame

from src.config import (
    BUTTON_HEIGHT,
    BUTTON_MARGIN,
    BUTTON_WIDTH,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_CHAOS,
    COLOR_CORRECT,
    COLOR_GOLD,
    COLOR_GRID,
    COLOR_HAND_TRAIL,
    COLOR_HIGHLIGHT,
    COLOR_LANDMARK,
    COLOR_SKELETON,
    COLOR_TEXT,
    COLOR_TIMER,

    FPS,
    HUD_FONT_SIZE,
    MENU_FONT_SIZE,
    PHASE_PANEL_WIDTH,
    TITLE_FONT_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.game_modes import ModeController
from src.gesture import HAND_CONNECTIONS, HandTracker
from src.leaderboard import load_leaderboard
from src.puzzle import PuzzleBoard
from src.state import GameMode, GameState, StateManager


class Button:
    """Simple clickable button."""

    def __init__(self, text: str, x: int, y: int, width: int = BUTTON_WIDTH, height: int = BUTTON_HEIGHT):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False
        self.color = COLOR_ACCENT
        self.hover_color = COLOR_HIGHLIGHT

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_TEXT, self.rect, 2, border_radius=10)
        text_surf = font.render(self.text, True, COLOR_BG)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class Renderer:
    """Handles all PyGame rendering."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("LIVE PUZZLE")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", TITLE_FONT_SIZE, bold=True)
        self.menu_font = pygame.font.SysFont("Arial", MENU_FONT_SIZE, bold=True)
        self.hud_font = pygame.font.SysFont("Arial", HUD_FONT_SIZE)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.phase_font = pygame.font.SysFont("Arial", 16)
        self.timer_font = pygame.font.SysFont("Arial", 32, bold=True)

        # Camera feed surface
        self.camera_surface = None

        # Particle effects
        self._particles: list[dict] = []

    def clear(self):
        self.screen.fill(COLOR_BG)

    def draw_menu(self, state_manager: StateManager, buttons: list[Button]):
        """Draw main menu."""
        self.clear()

        # Title
        title = self.title_font.render("LIVE PUZZLE", True, COLOR_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        # Subtitle
        sub = self.hud_font.render(
            "Solve puzzles with your hands in the air", True, COLOR_ACCENT
        )
        sub_rect = sub.get_rect(center=(WINDOW_WIDTH // 2, 220))
        self.screen.blit(sub, sub_rect)

        # Buttons
        for btn in buttons:
            btn.draw(self.screen, self.menu_font)

        # Footer
        footer = self.small_font.render(
            "Show your hand to the camera to control | Pinch to grab | Open hand to release",
            True,
            COLOR_GRID,
        )
        footer_rect = footer.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40))
        self.screen.blit(footer, footer_rect)

    def draw_mode_select(self, buttons: list[Button]):
        """Draw mode selection screen."""
        self.clear()

        title = self.menu_font.render("Select Game Mode", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

    def draw_grid_select(self, current_size: int, buttons: list[Button]):
        """Draw grid size selection screen."""
        self.clear()

        title = self.menu_font.render("Select Grid Size", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        size_text = self.title_font.render(
            f"{current_size} x {current_size}", True, COLOR_HIGHLIGHT
        )
        size_rect = size_text.get_rect(center=(WINDOW_WIDTH // 2, 250))
        self.screen.blit(size_text, size_rect)

        pieces_text = self.hud_font.render(
            f"({current_size * current_size} pieces)", True, COLOR_ACCENT
        )
        pieces_rect = pieces_text.get_rect(center=(WINDOW_WIDTH // 2, 310))
        self.screen.blit(pieces_text, pieces_rect)

        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

    def draw_capturing(self, frame: np.ndarray, countdown: int):
        """Draw camera capture screen with full-screen camera."""
        # Full-screen camera background
        if frame is not None:
            bg_surface = self._frame_to_surface(frame, WINDOW_WIDTH, WINDOW_HEIGHT)
            self.screen.blit(bg_surface, (0, 0))

            # Dark overlay for readability
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, (0, 0))
        else:
            self.clear()

        # "LIVE PUZZLE" title at top center
        title = self.menu_font.render("LIVE PUZZLE", True, COLOR_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 30))
        self.screen.blit(title, title_rect)

        # Phase panel top-right
        self._draw_phase_panel("PHASE 1: CAPTURE", [
            "1. Form a Frame with two hands",
            "2. Pinch both hands for 3sec",
        ])

        # Countdown overlay
        if countdown > 0:
            # Timer badge
            badge_w, badge_h = 100, 40
            badge_x = WINDOW_WIDTH // 2 - badge_w // 2
            badge_y = 60
            badge_surface = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
            badge_surface.fill((0, 0, 0, 180))
            self.screen.blit(badge_surface, (badge_x, badge_y))
            pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (badge_x, badge_y, badge_w, badge_h), 2, border_radius=15)

            count_text = self.timer_font.render(f"0:{countdown:02d}", True, COLOR_HIGHLIGHT)
            count_rect = count_text.get_rect(center=(WINDOW_WIDTH // 2, badge_y + badge_h // 2))
            self.screen.blit(count_text, count_rect)
        else:
            # Instructions
            inst = self.hud_font.render(
                "Press SPACE to capture or show PEACE sign",
                True,
                COLOR_TEXT,
            )
            inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            self.screen.blit(inst, inst_rect)

    def draw_game(
        self,
        board: PuzzleBoard,
        hand: HandTracker,
        mode_ctrl: ModeController,
        camera_frame: np.ndarray | None,
    ):
        """Draw the main game screen with full-screen camera background."""
        # Full-screen camera as background
        if camera_frame is not None:
            bg_surface = self._frame_to_surface(camera_frame, WINDOW_WIDTH, WINDOW_HEIGHT)
            self.screen.blit(bg_surface, (0, 0))

            # Slight dark overlay for piece visibility
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60))
            self.screen.blit(overlay, (0, 0))
        else:
            self.clear()

        # "LIVE PUZZLE" title at top center
        title_shadow = self.menu_font.render("LIVE PUZZLE", True, COLOR_BG)
        self.screen.blit(title_shadow, (WINDOW_WIDTH // 2 - title_shadow.get_width() // 2 + 2, 7))
        title = self.menu_font.render("LIVE PUZZLE", True, COLOR_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 25))
        self.screen.blit(title, title_rect)

        # Timer badge below title
        self._draw_timer_badge(mode_ctrl)

        # Phase panel top-right
        self._draw_phase_panel("PHASE 2: SOLVE", [
            "1. Pinch to Pick up",
            "2. Drag & Drop to Swap",
            "Hold Fist to Reset",
        ])

        # Leaderboard button top-left
        self._draw_leaderboard_button()

        # Draw board background (semi-transparent)
        grid_rect = board.get_grid_rect()
        grid_bg = pygame.Surface((grid_rect.width, grid_rect.height), pygame.SRCALPHA)
        grid_bg.fill((60, 60, 80, 80))
        self.screen.blit(grid_bg, (grid_rect.x, grid_rect.y))

        # Draw grid lines
        for i in range(board.grid_size + 1):
            x = board.board_x + i * board.piece_width
            pygame.draw.line(
                self.screen,
                (200, 200, 200, 100),
                (x, board.board_y),
                (x, board.board_y + board.board_height),
                1,
            )
            y = board.board_y + i * board.piece_height
            pygame.draw.line(
                self.screen,
                (200, 200, 200, 100),
                (board.board_x, y),
                (board.board_x + board.board_width, y),
                1,
            )

        # Draw pieces
        for piece in board.pieces:
            self.screen.blit(piece.surface, (int(piece.x), int(piece.y)))

            # Highlight border
            border_color = None
            if piece is board.held_piece:
                border_color = COLOR_HIGHLIGHT
            elif piece.is_correct:
                border_color = COLOR_CORRECT

            if border_color:
                pygame.draw.rect(
                    self.screen,
                    border_color,
                    piece.rect,
                    3,
                    border_radius=2,
                )

        # Draw hand skeleton
        if hand.hand_detected:
            self._draw_hand_skeleton(hand)
            self._draw_hand_cursor(hand)

        # Draw chaos warning
        if mode_ctrl.mode == GameMode.CHAOS and mode_ctrl.chaos_warning:
            self._draw_chaos_warning(mode_ctrl.chaos_countdown)

        # Draw particles
        self._update_particles()

    def draw_completed(
        self,
        board: PuzzleBoard,
        mode_ctrl: ModeController,
        buttons: list[Button],
        player_name: str,
        name_active: bool,
    ):
        """Draw completion screen matching video style."""
        # Dark background
        self.screen.fill((10, 10, 20))

        # Semi-transparent overlay with puzzle image faded in background
        if board.original_image is not None:
            bg = self._frame_to_surface(board.original_image, WINDOW_WIDTH, WINDOW_HEIGHT)
            bg.set_alpha(40)
            self.screen.blit(bg, (0, 0))

        # "LIVE PUZZLE" title
        title = self.menu_font.render("LIVE PUZZLE", True, COLOR_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 40))
        self.screen.blit(title, title_rect)

        # Trophy icon (text-based)
        trophy = self.title_font.render("\u2617", True, COLOR_GOLD)
        trophy_rect = trophy.get_rect(center=(WINDOW_WIDTH // 2, 130))
        self.screen.blit(trophy, trophy_rect)

        # "COMPLETE!"
        complete_text = self.menu_font.render("COMPLETE!", True, COLOR_HIGHLIGHT)
        complete_rect = complete_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(complete_text, complete_rect)

        # Timer
        elapsed = mode_ctrl.elapsed
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        time_str = f"{minutes}:{seconds:02d}"
        time_icon = self.hud_font.render(f"\u23f1 {time_str}", True, COLOR_TIMER)
        time_rect = time_icon.get_rect(center=(WINDOW_WIDTH // 2, 250))
        self.screen.blit(time_icon, time_rect)

        # Score
        final_score = mode_ctrl.calculate_final_score()
        score_text = self.hud_font.render(f"Score: {final_score}", True, COLOR_TEXT)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 290))
        self.screen.blit(score_text, score_rect)

        # "Enter your name for the leaderboard"
        prompt = self.hud_font.render("Enter your name for the leaderboard", True, COLOR_TEXT)
        prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, 350))
        self.screen.blit(prompt, prompt_rect)

        # Name input field
        input_w, input_h = 300, 50
        input_x = WINDOW_WIDTH // 2 - input_w // 2
        input_y = 380
        border_color = COLOR_HIGHLIGHT if name_active else COLOR_GRID
        pygame.draw.rect(self.screen, (30, 30, 50), (input_x, input_y, input_w, input_h), border_radius=8)
        pygame.draw.rect(self.screen, border_color, (input_x, input_y, input_w, input_h), 2, border_radius=8)

        # Name text or cursor
        display_name = player_name if player_name else ""
        name_surf = self.hud_font.render(display_name, True, COLOR_TEXT)
        self.screen.blit(name_surf, (input_x + 15, input_y + 12))

        # Blinking cursor
        if name_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = input_x + 15 + name_surf.get_width() + 2
            pygame.draw.line(self.screen, COLOR_TEXT, (cursor_x, input_y + 10), (cursor_x, input_y + 40), 2)

        # Submit arrow button
        arrow_size = 50
        arrow_x = input_x + input_w + 10
        arrow_y = input_y
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (arrow_x, arrow_y, arrow_size, arrow_size), border_radius=8)
        arrow_text = self.hud_font.render("\u2192", True, COLOR_BG)
        arrow_rect = arrow_text.get_rect(center=(arrow_x + arrow_size // 2, arrow_y + arrow_size // 2))
        self.screen.blit(arrow_text, arrow_rect)

        # Buttons
        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

        # Spawn celebration particles
        if len(self._particles) < 50:
            self._spawn_celebration()
        self._update_particles()

    def draw_leaderboard(self, buttons: list[Button]):
        """Draw leaderboard screen."""
        self.clear()

        title = self.menu_font.render("LEADERBOARD", True, COLOR_GOLD)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)

        entries = load_leaderboard()

        # Table header
        header_y = 110
        headers = ["#", "Name", "Score", "Time", "Mode", "Grid"]
        col_positions = [100, 200, 420, 560, 700, 900]
        for i, h in enumerate(headers):
            h_surf = self.hud_font.render(h, True, COLOR_ACCENT)
            self.screen.blit(h_surf, (col_positions[i], header_y))

        # Divider
        pygame.draw.line(self.screen, COLOR_GRID, (80, header_y + 35), (WINDOW_WIDTH - 80, header_y + 35), 1)

        # Entries
        for idx, entry in enumerate(entries[:10]):
            y = header_y + 50 + idx * 40
            color = COLOR_GOLD if idx == 0 else COLOR_TEXT
            rank_surf = self.hud_font.render(str(idx + 1), True, color)
            name_surf = self.hud_font.render(entry.get("name", "???"), True, color)
            score_surf = self.hud_font.render(str(entry.get("score", 0)), True, color)
            time_surf = self.hud_font.render(f"{entry.get('time', 0)}s", True, color)
            mode_surf = self.hud_font.render(entry.get("mode", ""), True, color)
            grid_surf = self.hud_font.render(f"{entry.get('grid', 3)}x{entry.get('grid', 3)}", True, color)

            self.screen.blit(rank_surf, (col_positions[0], y))
            self.screen.blit(name_surf, (col_positions[1], y))
            self.screen.blit(score_surf, (col_positions[2], y))
            self.screen.blit(time_surf, (col_positions[3], y))
            self.screen.blit(mode_surf, (col_positions[4], y))
            self.screen.blit(grid_surf, (col_positions[5], y))

        if not entries:
            empty = self.hud_font.render("No entries yet. Be the first!", True, COLOR_GRID)
            empty_rect = empty.get_rect(center=(WINDOW_WIDTH // 2, 300))
            self.screen.blit(empty, empty_rect)

        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

    def draw_paused(self, buttons: list[Button]):
        """Draw pause overlay."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(title, title_rect)

        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

    def _draw_hand_skeleton(self, hand: HandTracker):
        """Draw hand landmark skeleton on the game view."""
        pixels = hand.landmark_pixels
        if len(pixels) < 21:
            return

        # Draw connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(pixels) and end_idx < len(pixels):
                pygame.draw.line(
                    self.screen,
                    COLOR_SKELETON,
                    pixels[start_idx],
                    pixels[end_idx],
                    2,
                )

        # Draw landmarks
        for px, py in pixels:
            pygame.draw.circle(self.screen, COLOR_LANDMARK, (px, py), 4)
            pygame.draw.circle(self.screen, COLOR_SKELETON, (px, py), 4, 1)

    def _draw_hand_cursor(self, hand: HandTracker):
        """Draw hand cursor with trail."""
        # Trail
        trail = hand.trail
        for i in range(1, len(trail)):
            radius = max(1, int(3 * i / len(trail)))
            color = (
                COLOR_HAND_TRAIL[0],
                COLOR_HAND_TRAIL[1],
                COLOR_HAND_TRAIL[2],
            )
            pygame.draw.circle(self.screen, color, trail[i], radius)

        # Cursor
        cx, cy = hand.cursor_pos
        if hand.is_grabbing:
            pygame.draw.circle(self.screen, COLOR_HIGHLIGHT, (cx, cy), 18, 3)
            pygame.draw.circle(self.screen, COLOR_HIGHLIGHT, (cx, cy), 6)
        else:
            pygame.draw.circle(self.screen, COLOR_ACCENT, (cx, cy), 14, 2)
            pygame.draw.circle(self.screen, COLOR_ACCENT, (cx, cy), 4)

    def _draw_timer_badge(self, mode_ctrl: ModeController):
        """Draw timer badge below the LIVE PUZZLE title."""
        if mode_ctrl.mode == GameMode.TIME_ATTACK:
            remaining = mode_ctrl.remaining_time
            minutes = int(remaining) // 60
            seconds = int(remaining) % 60
            time_str = f"{minutes}:{seconds:02d}"
            color = COLOR_TIMER if remaining > 30 else COLOR_CHAOS
        else:
            elapsed = mode_ctrl.elapsed
            minutes = int(elapsed) // 60
            seconds = int(elapsed) % 60
            time_str = f"{minutes}:{seconds:02d}"
            color = COLOR_HIGHLIGHT

        badge_w, badge_h = 110, 36
        badge_x = WINDOW_WIDTH // 2 - badge_w // 2
        badge_y = 52
        badge_surface = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        badge_surface.fill((0, 0, 0, 180))
        self.screen.blit(badge_surface, (badge_x, badge_y))
        pygame.draw.rect(self.screen, color, (badge_x, badge_y, badge_w, badge_h), 2, border_radius=15)

        icon_text = self.timer_font.render(f"\u23f1 {time_str}", True, color)
        icon_rect = icon_text.get_rect(center=(WINDOW_WIDTH // 2, badge_y + badge_h // 2))
        self.screen.blit(icon_text, icon_rect)

    def _draw_phase_panel(self, phase_title: str, instructions: list[str]):
        """Draw phase instructions panel in top-right corner."""
        panel_w = PHASE_PANEL_WIDTH
        line_h = 22
        panel_h = 40 + len(instructions) * line_h + 10
        panel_x = WINDOW_WIDTH - panel_w - 15
        panel_y = 10

        # Panel background
        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_bg.fill((20, 20, 40, 200))
        self.screen.blit(panel_bg, (panel_x, panel_y))
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

        # Phase title
        title_surf = self.phase_font.render(phase_title, True, COLOR_GOLD)
        self.screen.blit(title_surf, (panel_x + 10, panel_y + 8))

        # Divider
        pygame.draw.line(
            self.screen, COLOR_GRID,
            (panel_x + 10, panel_y + 30),
            (panel_x + panel_w - 10, panel_y + 30),
            1,
        )

        # Instructions
        for i, line in enumerate(instructions):
            line_surf = self.phase_font.render(line, True, COLOR_TEXT)
            self.screen.blit(line_surf, (panel_x + 15, panel_y + 38 + i * line_h))

    def _draw_leaderboard_button(self):
        """Draw a leaderboard button in top-left corner."""
        btn_w, btn_h = 140, 32
        btn_x, btn_y = 10, 10

        btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        btn_bg.fill((20, 20, 40, 200))
        self.screen.blit(btn_bg, (btn_x, btn_y))
        pygame.draw.rect(self.screen, COLOR_GOLD, (btn_x, btn_y, btn_w, btn_h), 1, border_radius=6)

        label = self.phase_font.render("\u2617 LEADERBOARD", True, COLOR_GOLD)
        label_rect = label.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2))
        self.screen.blit(label, label_rect)

    def _draw_chaos_warning(self, countdown: float):
        """Draw chaos mode warning."""
        alpha = int(abs(np.sin(countdown * 3)) * 200)
        warning_text = self.menu_font.render(
            f"CHAOS IN {countdown:.1f}s!", True, COLOR_CHAOS
        )
        warning_rect = warning_text.get_rect(
            center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 60)
        )
        self.screen.blit(warning_text, warning_rect)

    def _spawn_celebration(self):
        """Spawn particles for celebration."""
        for _ in range(5):
            self._particles.append(
                {
                    "x": random.randint(0, WINDOW_WIDTH),
                    "y": random.randint(0, WINDOW_HEIGHT),
                    "vx": random.uniform(-3, 3),
                    "vy": random.uniform(-5, -1),
                    "life": random.randint(30, 90),
                    "color": random.choice(
                        [COLOR_HIGHLIGHT, COLOR_CORRECT, COLOR_ACCENT, COLOR_TIMER]
                    ),
                    "size": random.randint(3, 8),
                }
            )

    def _update_particles(self):
        """Update and draw particles."""
        alive = []
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.1  # gravity
            p["life"] -= 1
            if p["life"] > 0:
                pygame.draw.circle(
                    self.screen,
                    p["color"],
                    (int(p["x"]), int(p["y"])),
                    p["size"],
                )
                alive.append(p)
        self._particles = alive

    @staticmethod
    def _frame_to_surface(
        frame: np.ndarray, width: int, height: int
    ) -> pygame.Surface:
        """Convert OpenCV BGR frame to PyGame surface."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (width, height))
        # Rotate for pygame
        frame_rotated = np.rot90(frame_resized)
        frame_flipped = np.flipud(frame_rotated)
        return pygame.surfarray.make_surface(frame_flipped)

    def flip(self):
        """Update the display."""
        pygame.display.flip()
        self.clock.tick(FPS)

    def quit(self):
        pygame.quit()
