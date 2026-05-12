"""PyGame rendering engine for the puzzle game."""

import math
import os
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
    COLOR_GRID,
    COLOR_HAND_TRAIL,
    COLOR_HIGHLIGHT,
    COLOR_TEXT,
    COLOR_TIMER,
    COLOR_WRONG,
    FPS,
    HUD_FONT_SIZE,
    MENU_FONT_SIZE,
    TITLE_FONT_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.game_modes import ModeController
from src.gesture import HandTracker
from src.puzzle import PuzzleBoard
from src.state import GameMode, GameState, StateManager

_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
)


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
        pygame.display.set_caption("Hand Gesture Puzzle Game")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", TITLE_FONT_SIZE, bold=True)
        self.menu_font = pygame.font.SysFont("Arial", MENU_FONT_SIZE, bold=True)
        self.hud_font = pygame.font.SysFont("Arial", HUD_FONT_SIZE)
        self.small_font = pygame.font.SysFont("Arial", 20)

        # Camera feed surface
        self.camera_surface = None

        # Particle effects
        self._particles: list[dict] = []

        # About screen state
        self._about_tick = 0
        self._about_orbs: list[dict] = []
        self._dev_photo: pygame.Surface | None = None
        self._load_dev_photo()

    def reset_about_animation(self):
        """Reset about screen animation state for fresh entrance."""
        self._about_tick = 0
        self._about_orbs = []

    def clear(self):
        self.screen.fill(COLOR_BG)

    def draw_menu(self, state_manager: StateManager, buttons: list[Button]):
        """Draw main menu."""
        self.clear()

        # Title
        title = self.title_font.render("GESTURE PUZZLE", True, COLOR_HIGHLIGHT)
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
        """Draw camera capture screen."""
        self.clear()

        # Convert and display camera feed
        if frame is not None:
            cam_surface = self._frame_to_surface(frame, WINDOW_WIDTH - 100, WINDOW_HEIGHT - 200)
            cam_rect = cam_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
            self.screen.blit(cam_surface, cam_rect)

        # Countdown overlay
        if countdown > 0:
            count_text = self.title_font.render(str(countdown), True, COLOR_HIGHLIGHT)
            count_rect = count_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            # Shadow
            shadow = self.title_font.render(str(countdown), True, COLOR_BG)
            self.screen.blit(shadow, (count_rect.x + 3, count_rect.y + 3))
            self.screen.blit(count_text, count_rect)

        # Instructions
        inst = self.hud_font.render(
            "Press SPACE to capture or show PEACE sign",
            True,
            COLOR_TEXT,
        )
        inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, 40))
        self.screen.blit(inst, inst_rect)

    def draw_game(
        self,
        board: PuzzleBoard,
        hand: HandTracker,
        mode_ctrl: ModeController,
        camera_frame: np.ndarray | None,
    ):
        """Draw the main game screen."""
        self.clear()

        # Draw small camera preview in corner
        if camera_frame is not None:
            cam_w, cam_h = 200, 150
            cam_surface = self._frame_to_surface(camera_frame, cam_w, cam_h)
            self.screen.blit(cam_surface, (WINDOW_WIDTH - cam_w - 10, 10))
            pygame.draw.rect(
                self.screen,
                COLOR_GRID,
                (WINDOW_WIDTH - cam_w - 10, 10, cam_w, cam_h),
                2,
            )

        # Draw board background
        grid_rect = board.get_grid_rect()
        pygame.draw.rect(self.screen, COLOR_GRID, grid_rect, 0, border_radius=4)

        # Draw grid lines
        for i in range(board.grid_size + 1):
            x = board.board_x + i * board.piece_width
            pygame.draw.line(
                self.screen,
                COLOR_BG,
                (x, board.board_y),
                (x, board.board_y + board.board_height),
                1,
            )
            y = board.board_y + i * board.piece_height
            pygame.draw.line(
                self.screen,
                COLOR_BG,
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

        # Draw hand cursor and trail
        if hand.hand_detected:
            self._draw_hand_cursor(hand)

        # Draw HUD
        self._draw_hud(board, mode_ctrl)

        # Draw chaos warning
        if mode_ctrl.mode == GameMode.CHAOS and mode_ctrl.chaos_warning:
            self._draw_chaos_warning(mode_ctrl.chaos_countdown)

        # Draw particles
        self._update_particles()

    def draw_completed(self, board: PuzzleBoard, mode_ctrl: ModeController, buttons: list[Button]):
        """Draw completion screen."""
        self.clear()

        # Final score
        final_score = mode_ctrl.calculate_final_score()

        title = self.title_font.render("PUZZLE COMPLETE!", True, COLOR_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 120))
        self.screen.blit(title, title_rect)

        # Stats
        stats = [
            f"Mode: {mode_ctrl.mode.value}",
            f"Grid: {board.grid_size}x{board.grid_size}",
            f"Moves: {board.moves}",
            f"Time: {mode_ctrl.elapsed:.1f}s",
            f"Score: {final_score}",
        ]

        for i, stat in enumerate(stats):
            text = self.menu_font.render(stat, True, COLOR_TEXT)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 230 + i * 55))
            self.screen.blit(text, text_rect)

        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

        # Spawn celebration particles
        if len(self._particles) < 50:
            self._spawn_celebration()

        self._update_particles()

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

    def _load_dev_photo(self):
        """Load developer photo from assets directory and apply circular mask."""
        path = os.path.join(_ASSETS_DIR, "developer.png")
        if not os.path.exists(path):
            return

        img = pygame.image.load(path)
        mask_size = 180
        img = pygame.transform.smoothscale(img, (mask_size, mask_size))

        masked = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
        masked.fill((0, 0, 0, 0))
        # Draw circular mask then blit photo through it
        mask_surf = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
        mask_surf.fill((0, 0, 0, 0))
        pygame.draw.circle(mask_surf, (255, 255, 255, 255), (mask_size // 2, mask_size // 2), mask_size // 2)
        masked.blit(img, (0, 0))
        # Remove pixels outside the circle
        for y_px in range(mask_size):
            for x_px in range(mask_size):
                dx = x_px - mask_size // 2
                dy = y_px - mask_size // 2
                if dx * dx + dy * dy > (mask_size // 2) ** 2:
                    masked.set_at((x_px, y_px), (0, 0, 0, 0))

        self._dev_photo = masked

    def draw_about(self, buttons: list["Button"]):
        """Draw the About Developer screen with unique animations."""
        self.clear()
        self._about_tick += 1
        t = self._about_tick

        # --- Animated background: flowing gradient bars ---
        for i in range(20):
            offset = (t * 1.5 + i * 40) % (WINDOW_HEIGHT + 80) - 40
            alpha_val = int(25 + 15 * math.sin(t * 0.03 + i))
            bar_surf = pygame.Surface((WINDOW_WIDTH, 6), pygame.SRCALPHA)
            bar_surf.fill((0, 255, 180, alpha_val))
            self.screen.blit(bar_surf, (0, int(offset)))

        # --- Floating orbs ---
        if len(self._about_orbs) < 12:
            self._about_orbs.append({
                "x": random.randint(0, WINDOW_WIDTH),
                "y": random.randint(0, WINDOW_HEIGHT),
                "r": random.randint(15, 50),
                "dx": random.uniform(-0.8, 0.8),
                "dy": random.uniform(-0.5, 0.5),
                "color": random.choice([
                    COLOR_HIGHLIGHT, COLOR_ACCENT, COLOR_TIMER,
                    (180, 80, 255), (255, 120, 200),
                ]),
                "phase": random.uniform(0, math.pi * 2),
            })

        for orb in self._about_orbs:
            orb["x"] = (orb["x"] + orb["dx"]) % WINDOW_WIDTH
            orb["y"] = (orb["y"] + orb["dy"]) % WINDOW_HEIGHT
            pulse = 1.0 + 0.3 * math.sin(t * 0.05 + orb["phase"])
            radius = int(orb["r"] * pulse)
            orb_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(orb_surf, (*orb["color"][:3], 40), (radius, radius), radius)
            pygame.draw.circle(orb_surf, (*orb["color"][:3], 80), (radius, radius), radius // 2)
            self.screen.blit(orb_surf, (int(orb["x"]) - radius, int(orb["y"]) - radius))

        # --- Section title with glow effect ---
        title_text = "ABOUT THE DEVELOPER"
        glow_intensity = int(180 + 75 * math.sin(t * 0.04))
        glow_color = (0, glow_intensity, int(glow_intensity * 0.7))
        title_surf = self.title_font.render(title_text, True, glow_color)
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 60))
        # Glow shadow
        glow_shadow = self.title_font.render(title_text, True, (0, 80, 60))
        self.screen.blit(glow_shadow, (title_rect.x + 2, title_rect.y + 2))
        self.screen.blit(title_surf, title_rect)

        # --- Decorative line under title ---
        line_w = 300 + int(50 * math.sin(t * 0.03))
        line_x = WINDOW_WIDTH // 2 - line_w // 2
        pygame.draw.line(self.screen, COLOR_HIGHLIGHT, (line_x, 100), (line_x + line_w, 100), 2)

        # --- Developer photo with animated ring ---
        photo_cx, photo_cy = 220, 280
        mask_size = 180
        if self._dev_photo is not None:
            photo_rect = self._dev_photo.get_rect(center=(photo_cx, photo_cy))
            self.screen.blit(self._dev_photo, photo_rect)

            # Rotating ring around photo
            ring_radius = mask_size // 2 + 12
            for angle_i in range(36):
                angle = math.radians(angle_i * 10 + t * 2)
                dot_x = photo_cx + int(ring_radius * math.cos(angle))
                dot_y = photo_cy + int(ring_radius * math.sin(angle))
                dot_alpha = int(100 + 155 * abs(math.sin(angle + t * 0.05)))
                dot_color = COLOR_HIGHLIGHT if angle_i % 3 == 0 else COLOR_ACCENT
                dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, (*dot_color[:3], dot_alpha), (4, 4), 4)
                self.screen.blit(dot_surf, (dot_x - 4, dot_y - 4))
        else:
            # Placeholder circle if no photo
            pygame.draw.circle(self.screen, COLOR_GRID, (photo_cx, photo_cy), 90, 3)
            no_photo = self.hud_font.render("No Photo", True, COLOR_GRID)
            self.screen.blit(no_photo, no_photo.get_rect(center=(photo_cx, photo_cy)))

        # --- Developer info text with staggered fade-in ---
        info_x = 400
        info_lines = [
            ("Shoaib Vehni", self.menu_font, COLOR_HIGHLIGHT),
            ("Game Developer & CV Engineer", self.hud_font, COLOR_ACCENT),
            ("", None, None),
            ("Tech Stack:", self.hud_font, COLOR_TIMER),
            ("Python  |  OpenCV  |  MediaPipe", self.small_font, COLOR_TEXT),
            ("PyGame  |  NumPy  |  Hand Tracking", self.small_font, COLOR_TEXT),
            ("", None, None),
            ("Built with real-time computer vision", self.small_font, COLOR_ACCENT),
            ("and gesture-based interaction design", self.small_font, COLOR_ACCENT),
        ]

        for i, (line, font, color) in enumerate(info_lines):
            if font is None:
                continue
            # Staggered reveal animation: each line slides in from right
            delay = i * 8
            progress = min(1.0, max(0.0, (t - delay) / 30.0))
            slide_x = int(info_x + 100 * (1.0 - progress))
            alpha = int(255 * progress)

            text_surf = font.render(line, True, color)
            alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
            alpha_surf.blit(text_surf, (0, 0))
            alpha_surf.set_alpha(alpha)
            self.screen.blit(alpha_surf, (slide_x, 170 + i * 35))

        # --- Animated skill bars ---
        skills = [
            ("Computer Vision", 0.95, COLOR_HIGHLIGHT),
            ("Game Development", 0.88, COLOR_ACCENT),
            ("Hand Tracking", 0.92, (180, 80, 255)),
            ("UI/UX Design", 0.80, COLOR_TIMER),
        ]

        bar_x, bar_y_start = 100, 490
        bar_w, bar_h = 500, 16
        for i, (skill_name, level, color) in enumerate(skills):
            y = bar_y_start + i * 40
            # Fill animation
            fill_delay = 40 + i * 15
            fill_progress = min(1.0, max(0.0, (t - fill_delay) / 40.0))
            fill_w = int(bar_w * level * fill_progress)

            label = self.small_font.render(skill_name, True, COLOR_TEXT)
            self.screen.blit(label, (bar_x, y - 16))

            # Background bar
            pygame.draw.rect(self.screen, COLOR_GRID, (bar_x, y, bar_w, bar_h), border_radius=4)
            # Filled portion
            if fill_w > 0:
                pygame.draw.rect(self.screen, color, (bar_x, y, fill_w, bar_h), border_radius=4)
            # Percentage
            pct_text = self.small_font.render(f"{int(level * 100 * fill_progress)}%", True, COLOR_TEXT)
            self.screen.blit(pct_text, (bar_x + bar_w + 12, y - 2))

        # --- Buttons ---
        for btn in buttons:
            btn.draw(self.screen, self.hud_font)

        # --- Animated corner accents ---
        corner_len = 30 + int(10 * math.sin(t * 0.06))
        corners = [
            ((10, 10), (10 + corner_len, 10), (10, 10 + corner_len)),
            ((WINDOW_WIDTH - 10, 10), (WINDOW_WIDTH - 10 - corner_len, 10), (WINDOW_WIDTH - 10, 10 + corner_len)),
            ((10, WINDOW_HEIGHT - 10), (10 + corner_len, WINDOW_HEIGHT - 10), (10, WINDOW_HEIGHT - 10 - corner_len)),
            ((WINDOW_WIDTH - 10, WINDOW_HEIGHT - 10), (WINDOW_WIDTH - 10 - corner_len, WINDOW_HEIGHT - 10), (WINDOW_WIDTH - 10, WINDOW_HEIGHT - 10 - corner_len)),
        ]
        for corner, h_end, v_end in corners:
            pygame.draw.line(self.screen, COLOR_HIGHLIGHT, corner, h_end, 2)
            pygame.draw.line(self.screen, COLOR_HIGHLIGHT, corner, v_end, 2)

    def _draw_hand_cursor(self, hand: HandTracker):
        """Draw hand cursor with trail."""
        # Trail
        trail = hand.trail
        for i in range(1, len(trail)):
            alpha = int(255 * i / len(trail))
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

        # Gesture label
        label = self.small_font.render(hand.gesture.upper(), True, COLOR_ACCENT)
        self.screen.blit(label, (cx + 20, cy - 10))

    def _draw_hud(self, board: PuzzleBoard, mode_ctrl: ModeController):
        """Draw heads-up display."""
        # Mode label
        mode_text = self.hud_font.render(mode_ctrl.mode.value, True, COLOR_ACCENT)
        self.screen.blit(mode_text, (15, 10))

        # Moves
        moves_text = self.hud_font.render(
            f"Moves: {board.moves}", True, COLOR_TEXT
        )
        self.screen.blit(moves_text, (15, 45))

        # Progress
        progress = f"{board.correct_count}/{board.total_pieces}"
        prog_text = self.hud_font.render(
            f"Correct: {progress}", True, COLOR_CORRECT
        )
        self.screen.blit(prog_text, (15, 80))

        # Score
        score_text = self.hud_font.render(
            f"Score: {mode_ctrl.score}", True, COLOR_HIGHLIGHT
        )
        self.screen.blit(score_text, (15, 115))

        # Combo
        if mode_ctrl.combo > 1:
            combo_text = self.hud_font.render(
                f"Combo x{mode_ctrl.combo}!", True, COLOR_TIMER
            )
            self.screen.blit(combo_text, (15, 150))

        # Timer for Time Attack
        if mode_ctrl.mode == GameMode.TIME_ATTACK:
            remaining = mode_ctrl.remaining_time
            color = COLOR_TIMER if remaining > 30 else COLOR_CHAOS
            timer_text = self.menu_font.render(
                f"{remaining:.1f}s", True, color
            )
            timer_rect = timer_text.get_rect(
                midtop=(WINDOW_WIDTH // 2, 5)
            )
            self.screen.blit(timer_text, timer_rect)

        # Time elapsed for other modes
        else:
            time_text = self.hud_font.render(
                f"Time: {mode_ctrl.elapsed:.1f}s", True, COLOR_TEXT
            )
            self.screen.blit(time_text, (WINDOW_WIDTH - 200, WINDOW_HEIGHT - 35))

        # Controls hint
        hint = self.small_font.render(
            "ESC=Pause | R=Restart | Q=Quit", True, COLOR_GRID
        )
        self.screen.blit(hint, (15, WINDOW_HEIGHT - 30))

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
                alpha = min(255, p["life"] * 4)
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
