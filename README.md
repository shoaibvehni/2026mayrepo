# Hand Gesture Puzzle Game

An immersive real-time interactive puzzle game where you solve puzzles using **hand gestures via webcam**. No mouse, no keyboard during gameplay — just your hands in the air.

Built with OpenCV, MediaPipe, NumPy, and PyGame.

> **Live Demo Page:** [gesture-puzzle-landing-fajnrtin.devinapps.com](https://gesture-puzzle-landing-fajnrtin.devinapps.com)

---

## Quick Start (One-Click Install & Play)

### Windows
1. Download or clone this repo
2. Double-click **`install_and_play.bat`**
3. Done — the game will install everything and launch automatically

### Linux / macOS
```bash
git clone https://github.com/shoaibvehni/2026mayrepo.git
cd 2026mayrepo
chmod +x install_and_play.sh
./install_and_play.sh
```

### Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download hand tracking model (optional, for webcam gesture control)
mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

# 3. Run the game
python run.py
```

> **Note:** A webcam is optional. Without one, the game generates a colorful sample image and uses mouse/keyboard controls.

---

## Features

### Hand Gesture Controls
| Gesture | Action |
|---------|--------|
| **Pinch** (thumb + index) | Grab puzzle piece |
| **Move hand** | Drag piece through the air |
| **Open hand** | Release/drop piece |
| **Peace sign** | Trigger camera capture |
| **Point** | Cursor indicator |

### Game Modes

#### Classic Mode
Standard puzzle solving. Capture an image from your webcam, the system splits it into an N×N grid, shuffles the pieces, and you solve it by grabbing and swapping pieces with hand gestures.

#### Chaos Mode
The system fights back. Every few seconds, a chaos event triggers:
- **Random swap**: Two pieces swap positions
- **Wandering pieces**: Some pieces drift away from their grid slots
- **Row/column shuffle**: An entire row or column gets reshuffled

A warning countdown appears before each chaos event. Correct placements are protected from chaos. Score multiplier: 1.5x.

#### Time Attack Mode
Race against a 120-second timer. Bonus points for remaining time. The timer turns red when below 30 seconds.

### Puzzle System
- Capture any scene from your webcam as the puzzle image
- Configurable grid size: 2×2 up to 6×6 (4 to 36 pieces)
- Snap-to-grid placement with visual feedback
- Automatic swap when placing a piece on an occupied slot
- Green border = correct position, highlighted border = currently held

### Scoring
- **100 points** per correct placement
- **Combo bonus**: consecutive correct placements multiply points (+25 per combo level)
- **Time bonus** (Time Attack): remaining seconds × 10
- **Move efficiency bonus**: fewer moves = higher score
- **Chaos multiplier**: 1.5× in Chaos Mode

### Visual Feedback
- Hand cursor with motion trail
- Gesture label display
- Live camera preview during gameplay
- Particle celebration effects on completion
- Chaos warning countdown with flashing text

---

## Controls

### Menu Navigation
- **Mouse click** on buttons to navigate menus
- **ESC** to go back

### During Gameplay
| Key | Action |
|-----|--------|
| **ESC** | Pause/Resume |
| **R** | Restart puzzle |
| **Q** | Quit to menu |
| **Hand gestures** | All piece interaction |

### Camera Capture Screen
| Input | Action |
|-------|--------|
| **SPACE** | Start 3-second capture countdown |
| **Peace sign** | Start capture countdown via gesture |
| **ESC** | Go back |

---

## Architecture

```
src/
├── __init__.py       # Package init
├── main.py           # Game loop & controller
├── gesture.py        # MediaPipe hand tracking & gesture recognition
├── puzzle.py         # Puzzle engine (split, shuffle, snap, completion)
├── game_modes.py     # Mode logic (Classic, Chaos, Time Attack)
├── renderer.py       # PyGame rendering (menus, HUD, effects)
├── state.py          # Game state machine & mode enums
├── config.py         # All constants and configuration
└── utils.py          # Image utilities & camera helpers
```

### System Flow
1. **Menu** → Select game mode → Select grid size
2. **Capture** → Webcam image captured (or sample generated)
3. **Play** → Image split into grid → Pieces shuffled → Hand tracking active
4. **Solve** → Pinch to grab → Drag to swap → Release to place
5. **Complete** → Score calculated → Celebration effects → Play again

---

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **OpenCV** | Image processing, camera capture, frame manipulation |
| **MediaPipe** | Real-time hand landmark detection (21 points) |
| **NumPy** | Array operations, image math |
| **PyGame** | Game window, rendering, UI, event handling |

---

## No Camera? No Problem

If no webcam is detected, the game automatically generates a colorful sample image with geometric shapes as the puzzle source. All gesture controls still work if you have a camera for hand tracking but chose not to capture from it.

---

## License

MIT
