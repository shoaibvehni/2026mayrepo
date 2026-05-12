---
name: testing-gesture-puzzle
description: End-to-end testing of the Hand Gesture Puzzle Game PyGame UI. Use when verifying game launch, menu flows, game modes, keyboard controls, or the no-camera fallback.
---

# Testing the Hand Gesture Puzzle Game

## Prerequisites

- Python 3.10+ with dependencies: `pip install -r requirements.txt`
- The `models/hand_landmarker.task` file must exist (7.5MB MediaPipe model). If missing, download:
  ```bash
  mkdir -p models && curl -L -o models/hand_landmarker.task \
    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
  ```
- X11 display available (`DISPLAY=:0`)

## Launching the Game

```bash
cd /home/ubuntu/repos/2026mayrepo
DISPLAY=:0 SDL_VIDEODRIVER=x11 python run.py &
```

Use `wmctrl -a "Hand Gesture Puzzle Game"` to bring the window to the foreground.

The game window is 1280x720 but may render at a scaled resolution depending on the display. Button coordinates need to be calculated relative to the actual rendered window position.

## No-Webcam Fallback

When no webcam is available (common on VMs), the game:
- Skips camera preview
- Auto-generates a colorful gradient image with shapes and "PUZZLE" text
- Shows a 2-second countdown on the capture screen, then auto-transitions to the game board
- Hand gesture controls are disabled; pieces cannot be moved without a camera

This means **puzzle completion and piece dragging cannot be tested** without a webcam. Focus testing on UI flows, menu navigation, and keyboard controls.

## Key Test Flows

### 1. Main Menu
- Verify "GESTURE PUZZLE" title, "Play" and "Quit" buttons, subtitle text, footer with gesture hints

### 2. Menu Navigation
- Play → Mode Select (3 buttons: Classic Mode, Chaos Mode, Time Attack + Back)
- Select a mode → Grid Select (arrows to change size 2x2–6x6, Start, Back)
- Grid arrows update the displayed size and piece count text

### 3. Game Board (Classic Mode)
- After auto-capture (~2s), game board shows shuffled pieces in an NxN grid
- HUD: mode label, Moves counter, Correct count, Score
- Timer counting up at bottom-right
- Control hints: "ESC=Pause | R=Restart | Q=Quit"

### 4. Keyboard Controls
- **ESC** during gameplay: Shows "PAUSED" overlay with Resume/Restart/Menu buttons
- **R** during gameplay: Reshuffles pieces, resets Moves/Score/Correct to 0, resets timer
- **Q** during gameplay: Returns to main menu
- **ESC** from Grid Select: Returns to main menu

### 5. Time Attack Mode
- Shows large countdown timer at top center (starts at 120s)
- Timer color is yellow/gold when >30s remaining
- HUD shows "Time Attack" as mode label

### 6. Back Navigation
- Back button from Mode Select → Main Menu
- Back button from Grid Select → Mode Select (or ESC → Main Menu)

## Known Limitations

- **Hand gesture input** requires a physical webcam; cannot be tested on headless VMs
- **Chaos Mode disruptions** (random swaps, piece wandering) trigger during extended gameplay and may require longer play sessions to observe
- **Puzzle completion** requires moving pieces via hand gestures
- MediaPipe may change APIs between versions; the game uses `mp.tasks.vision.HandLandmarker` (Tasks API). If `mp.solutions.hands` errors appear, the API has likely changed again

## Devin Secrets Needed

No secrets required for testing. The game runs entirely locally.
