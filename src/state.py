"""Game state machine."""

from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    MODE_SELECT = auto()
    GRID_SELECT = auto()
    CAPTURING = auto()
    PLAYING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    LEADERBOARD = auto()


class GameMode(Enum):
    CLASSIC = "Classic Mode"
    CHAOS = "Chaos Mode"
    TIME_ATTACK = "Time Attack"


class StateManager:
    """Manages game state transitions."""

    def __init__(self):
        self.state = GameState.MENU
        self.mode = GameMode.CLASSIC
        self.grid_size = 3
        self.previous_state: GameState | None = None

    def transition(self, new_state: GameState):
        self.previous_state = self.state
        self.state = new_state

    def set_mode(self, mode: GameMode):
        self.mode = mode

    def set_grid_size(self, size: int):
        self.grid_size = max(2, min(6, size))

    def go_back(self):
        if self.previous_state is not None:
            self.state, self.previous_state = self.previous_state, self.state
