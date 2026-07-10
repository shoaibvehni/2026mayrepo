---
name: testing-live-puzzle
description: Test the LIVE PUZZLE hand gesture puzzle game end-to-end. Use when verifying UI, leaderboard, game flow, or MediaPipe integration changes.
---

# Testing LIVE PUZZLE Game

## Environment Setup

1. Install dependencies: `pip install -r requirements.txt`
2. The game uses MediaPipe Tasks API (0.10.35+). The `hand_landmarker.task` model file auto-downloads on first run from Google's model storage.
3. If MediaPipe import errors occur (e.g., `mp.solutions` not found), the codebase uses the newer `mediapipe.tasks.python.vision.HandLandmarker` API — do NOT use `mp.solutions.hands`.

## Running the Game

```bash
SDL_VIDEODRIVER=x11 DISPLAY=:0 python run.py
```

- The game window opens as a PyGame window (1280x720)
- Without a webcam, the game falls back to generated sample images
- Without a webcam, the capture screen auto-starts a 2-second countdown and generates a sample image automatically (no user input needed)

## UI Navigation Flow

```
Menu → Play → Mode Select → Grid Select → Start → Capturing → Playing → Completion
Menu → Leaderboard
Completion → Skip & Play Again → Mode Select
Completion → (type name + submit) → score saved to leaderboard.json
```

### Key Screens and What to Verify

| Screen | Key Elements |
|--------|-------------|
| Menu | "LIVE PUZZLE" title, Play/Leaderboard/Quit buttons, subtitle |
| Mode Select | "Select Game Mode" title, Classic/Chaos/Time Attack buttons |
| Grid Select | "Select Grid Size" title, "N x N" with arrows, Start/Back |
| Capture | Full-screen bg, "LIVE PUZZLE" title, Phase 1 panel (top-right), countdown |
| Game | "LIVE PUZZLE" title with shadow, timer badge, Phase 2 panel (top-right), LEADERBOARD button (top-left), puzzle grid |
| Completion | "LIVE PUZZLE" title, trophy icon, "COMPLETE!", timer, score, name input, submit arrow, "Skip & Play Again" |
| Leaderboard | "LEADERBOARD" title in gold, table with #/Name/Score/Time/Mode/Grid headers |

## Testing Without a Webcam

- **Hand skeleton rendering**: Cannot be tested without a webcam. The `_draw_hand_skeleton` method only activates when `hand.hand_detected` is True.
- **Hand gestures** (pinch, fist, etc.): Cannot be tested without a webcam.
- **Reaching completion screen quickly**: Temporarily set `TIME_ATTACK_DURATION` in `src/config.py` to a low value (e.g., 5 seconds) to trigger time-up completion. **Remember to revert to 120 after testing.**
- **Auto-capture**: When `use_camera=False`, the capture screen auto-starts a 2s countdown in `_render_capturing()` (main.py lines 423-427).

## Leaderboard Persistence

- Scores are saved to `leaderboard.json` at project root
- File is gitignored
- Delete `leaderboard.json` before testing to verify empty state
- After submitting a name on the completion screen, verify the JSON file contains the correct entry

## Known Issues

- Trophy icon uses Unicode `☗` (U+2617) which may render as a box on some system fonts. This is a cosmetic issue.
- ALSA audio warnings are expected on VMs without sound hardware — they don't affect functionality.
- Camera warnings (V4L2, FFMPEG) are expected on VMs without webcam — the game handles this gracefully.

## Devin Secrets Needed

No secrets are required for testing this application.
