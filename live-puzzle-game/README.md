# LIVE PUZZLE - Hand Gesture Puzzle Game

An immersive real-time interactive puzzle game where you solve puzzles using **hand gestures via webcam**. No mouse, no keyboard during gameplay — just your hands in the air. Now with **freehand drawing mode**, **procedural sound effects**, and **cinematic visual effects**.

Built with OpenCV, MediaPipe, NumPy, and PyGame.

**Developed by Shoaib**

---

## Features

### Live Camera Background
The full webcam feed serves as the game background during both capture and gameplay phases, creating an immersive AR-like experience.

### Hand Gesture Controls
| Gesture | Action |
|---------|--------|
| **Pinch** (thumb + index) | Grab puzzle piece |
| **Move hand** | Drag piece through the air |
| **Open hand** | Release/drop piece |
| **Peace sign** | Trigger camera capture |
| **Point** | Cursor indicator / Draw in drawing mode |
| **Hold Fist** | Reset/restart puzzle / Clear canvas |

### Hand Skeleton Visualization
Real-time hand landmark skeleton drawn on screen during gameplay, showing all 21 MediaPipe hand landmarks connected by bones.

### Phase-Based UI
- **Phase 1: CAPTURE** — Instructions panel guides you to capture your puzzle image
- **Phase 2: SOLVE** — Instructions panel shows gesture controls during gameplay

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

### Freehand Drawing Mode (NEW)
A separate creative section where you can draw freely using hand gestures:
- **Point finger** to draw on the canvas
- **Pinch** to cycle through 12 vibrant colors
- **Peace sign** to change brush size
- **Fist** to clear the canvas
- Multiple brush sizes (2px to 24px)
- Eraser mode with toggle
- Undo support (up to 20 levels)
- Keyboard shortcuts: `C` clear, `Z` undo, `E` eraser, arrow keys for color/size
- Live camera background with drawing overlay

### Procedural Sound Effects (NEW)
All sounds are generated procedurally at runtime — no external audio files needed:
- **Grab/Drop sounds** — satisfying pick-up and place effects
- **Correct/Wrong placement** — musical feedback for puzzle solving
- **Victory fanfare** — celebratory chord progression on completion
- **Hacking/Cyber beeps** — sci-fi computer terminal sounds
- **Space whoosh** — ambient spacecraft-style transitions
- **Movie swoosh** — cinematic transition effects
- **Matrix data stream** — digital rain sound effect
- **UI clicks** — responsive button feedback
- **Chaos alarm** — warning beeps before chaos events
- **Drawing tick** — subtle stroke audio feedback
- **Color change** — melodic color switching sound

### Visual Effects (NEW)
- **Matrix rain** — Japanese katakana characters falling on menu backgrounds
- **CRT scanlines** — retro monitor overlay effect
- **Glowing animated title** — pulsing neon title on the main menu
- **"Developed by Shoaib"** credit — shown on every screen

### Puzzle System
- Capture any scene from your webcam as the puzzle image
- Configurable grid size: 2×2 up to 6×6 (4 to 36 pieces)
- Snap-to-grid placement with visual feedback
- Automatic swap when placing a piece on an occupied slot
- Green border = correct position, highlighted border = currently held

### Scoring & Leaderboard
- **100 points** per correct placement
- **Combo bonus**: consecutive correct placements multiply points (+25 per combo level)
- **Time bonus** (Time Attack): remaining seconds × 10
- **Move efficiency bonus**: fewer moves = higher score
- **Chaos multiplier**: 1.5× in Chaos Mode
- **Leaderboard**: Enter your name on completion, scores saved locally

### Visual Feedback
- Full-screen camera background during gameplay
- "LIVE PUZZLE" title with timer badge
- Hand cursor with motion trail
- Hand skeleton overlay with landmark dots
- Phase instructions panel (top-right corner)
- Leaderboard button (top-left corner)
- Particle celebration effects on completion
- Chaos warning countdown with flashing text

---

## Setup

### Requirements
- Python 3.10+
- Webcam (optional — falls back to a generated sample image)

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python run.py
```

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
| **Hold Fist** | Reset puzzle |

### Camera Capture Screen
| Input | Action |
|-------|--------|
| **SPACE** | Start 3-second capture countdown |
| **Peace sign** | Start capture countdown via gesture |
| **ESC** | Go back |

### Drawing Mode
| Input | Action |
|-------|--------|
| **Point finger** | Draw on canvas |
| **Pinch** | Cycle to next color |
| **Peace sign** | Increase brush size |
| **Fist (hold)** | Clear canvas |
| **C** | Clear canvas |
| **Z** | Undo last stroke |
| **E** | Toggle eraser |
| **Left/Right arrows** | Change color |
| **Up/Down arrows** | Change brush size |
| **ESC** | Back to menu |

### Completion Screen
| Input | Action |
|-------|--------|
| **Type name** | Enter your name for the leaderboard |
| **ENTER** | Submit score |
| **Click arrow** | Submit score |
| **Skip & Play Again** | Skip leaderboard entry |

---

## Architecture

```
src/
├── __init__.py       # Package init
├── main.py           # Game loop & controller
├── gesture.py        # MediaPipe hand tracking & gesture recognition
├── puzzle.py         # Puzzle engine (split, shuffle, snap, completion)
├── game_modes.py     # Mode logic (Classic, Chaos, Time Attack)
├── renderer.py       # PyGame rendering (menus, HUD, effects, drawing)
├── state.py          # Game state machine & mode enums
├── config.py         # All constants and configuration
├── leaderboard.py    # Leaderboard persistence & management
├── drawing.py        # Freehand drawing canvas (NEW)
├── sounds.py         # Procedural sound effects engine (NEW)
└── utils.py          # Image utilities & camera helpers
```

### System Flow
1. **Menu** → Select game mode → Select grid size (or enter Drawing mode)
2. **Phase 1: Capture** → Full-screen webcam with capture instructions
3. **Phase 2: Solve** → Image split into grid → Pieces shuffled → Hand tracking active
4. **Solve** → Pinch to grab → Drag to swap → Release to place
5. **Complete** → Score calculated → Enter name → Leaderboard → Play again
6. **Draw** → Freehand drawing with gesture controls on camera background

---

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **OpenCV** | Image processing, camera capture, frame manipulation |
| **MediaPipe** | Real-time hand landmark detection (21 points) |
| **NumPy** | Array operations, image math, procedural audio |
| **PyGame** | Game window, rendering, UI, event handling, audio |

---

## No Camera? No Problem

If no webcam is detected, the game automatically generates a colorful sample image with geometric shapes as the puzzle source. All gesture controls still work if you have a camera for hand tracking but chose not to capture from it.

---

## Credits

**Developed by Shoaib**

---

## License

MIT
