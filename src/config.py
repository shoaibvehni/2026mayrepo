"""Game configuration constants."""

# Window
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 30

# Puzzle grid
DEFAULT_GRID_SIZE = 3  # 3x3 grid
MIN_GRID_SIZE = 2
MAX_GRID_SIZE = 6

# Gesture detection
PINCH_THRESHOLD = 40  # pixels distance for pinch detection
GRAB_HOLD_FRAMES = 3  # frames to confirm grab
RELEASE_HOLD_FRAMES = 2  # frames to confirm release
HAND_SMOOTHING = 0.6  # interpolation factor for smooth hand movement

# Puzzle mechanics
SNAP_THRESHOLD = 0.4  # fraction of piece size for snap distance
PIECE_PADDING = 2  # pixels between pieces

# Game modes
CHAOS_SHUFFLE_INTERVAL = 8.0  # seconds between chaos shuffles
CHAOS_MOVE_SPEED = 2.0  # pixels per frame for wandering pieces
TIME_ATTACK_DURATION = 120  # seconds for time attack mode

# Colors (RGB)
COLOR_BG = (20, 20, 30)
COLOR_GRID = (60, 60, 80)
COLOR_HIGHLIGHT = (0, 255, 180)
COLOR_CORRECT = (0, 200, 100)
COLOR_WRONG = (200, 60, 60)
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (100, 180, 255)
COLOR_CHAOS = (255, 60, 60)
COLOR_TIMER = (255, 200, 50)
COLOR_OVERLAY = (0, 0, 0, 180)
COLOR_HAND_TRAIL = (0, 255, 180, 100)

# UI
MENU_FONT_SIZE = 48
HUD_FONT_SIZE = 28
TITLE_FONT_SIZE = 72
BUTTON_WIDTH = 300
BUTTON_HEIGHT = 60
BUTTON_MARGIN = 20

# Gesture labels
GESTURE_OPEN = "open"
GESTURE_PINCH = "pinch"
GESTURE_FIST = "fist"
GESTURE_POINT = "point"
GESTURE_PEACE = "peace"
GESTURE_NONE = "none"
