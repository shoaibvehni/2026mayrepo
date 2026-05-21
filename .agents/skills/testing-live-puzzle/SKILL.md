---
name: testing-live-puzzle
description: Test the Live Puzzle hand gesture game end-to-end. Use when verifying game UI, menu navigation, puzzle gameplay, or drawing mode changes.
---

# Testing Live Puzzle Game

## Prerequisites

- Python 3.10+ (uses `X | None` union syntax)
- Display server (X11 on Linux with `DISPLAY=:0`)
- No webcam required — game falls back to generated sample images
- No audio hardware required — ALSA warnings are non-fatal

## Setup

```bash
cd /path/to/repo
pip install -r requirements.txt
```

If audio driver causes issues, set `SDL_AUDIODRIVER=dummy` before launching.

## Running the Game

```bash
# From repo root
python run.py

# Or from live-puzzle-game/ subfolder (if it exists)
cd live-puzzle-game && python run.py
```

The game opens a 1280x720 PyGame window titled "LIVE PUZZLE - Hand Gesture Game".

## Testing Without Webcam

When no webcam is available:
- The capture phase auto-generates a colorful gradient image with shapes
- Auto-capture triggers after ~2 seconds (no manual SPACE press needed)
- All menu navigation works via mouse clicks
- Hand gesture controls (pinch, fist, peace sign) won't be testable

## UI Navigation Flow

1. **Main Menu** → Play, Draw, Leaderboard, Quit buttons
2. **Play** → Mode Select (Classic / Chaos / Time Attack) → Grid Select (2x2 to 6x6) → Capture → Playing
3. **Draw** → Drawing canvas with Clear/Undo/Eraser/Back toolbar + color palette
4. **ESC** pauses during gameplay, returns to menu from other screens
5. **Q** returns to menu from gameplay

## Key Things to Verify

- Game window opens with correct title and 1280x720 resolution
- Matrix rain animation renders on menu background
- "Developed by Shoaib" credit text visible on all screens
- Mode select shows 3 colored buttons (blue=Classic, red=Chaos, yellow=Time Attack)
- Grid select shows NxN text and piece count, arrows change size
- Capture phase shows generated sample image with countdown timer
- Playing state shows shuffled puzzle grid with LEADERBOARD button, timer, phase panel
- Drawing mode shows toolbar, 12-color palette, brush size indicator
- Pause screen overlay with Resume/Restart/Menu buttons

## Syntax/Import Verification

```bash
python -c "import py_compile; [py_compile.compile(f'src/{f}', doraise=True) for f in ['config.py','state.py','utils.py','leaderboard.py','drawing.py','sounds.py','puzzle.py','gesture.py','game_modes.py','main.py','renderer.py']]"
```

## Devin Secrets Needed

None — this game runs entirely locally with no external services.
