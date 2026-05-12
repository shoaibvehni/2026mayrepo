"""Hand gesture detection using MediaPipe Tasks API."""

import math
import os

import cv2
import mediapipe as mp
import numpy as np

from src.config import (
    GESTURE_FIST,
    GESTURE_NONE,
    GESTURE_OPEN,
    GESTURE_PEACE,
    GESTURE_PINCH,
    GESTURE_POINT,
    GRAB_HOLD_FRAMES,
    HAND_SMOOTHING,
    PINCH_THRESHOLD,
    RELEASE_HOLD_FRAMES,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

# MediaPipe Tasks API imports
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

# Landmark indices (same as the old HandLandmark enum)
WRIST = 0
THUMB_TIP = 4
INDEX_FINGER_TIP = 8
INDEX_FINGER_MCP = 5
MIDDLE_FINGER_TIP = 12
MIDDLE_FINGER_MCP = 9
RING_FINGER_TIP = 16
RING_FINGER_MCP = 13
PINKY_TIP = 20
PINKY_MCP = 17

# Model path
_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "hand_landmarker.task",
)


class HandTracker:
    """Tracks hand landmarks and recognizes gestures."""

    def __init__(self):
        self._landmarker = None
        if os.path.exists(_MODEL_PATH):
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=_MODEL_PATH),
                running_mode=RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.7,
                min_tracking_confidence=0.6,
            )
            self._landmarker = HandLandmarker.create_from_options(options)

        # Smoothed cursor position
        self._cursor_x = WINDOW_WIDTH // 2
        self._cursor_y = WINDOW_HEIGHT // 2

        # Gesture state tracking
        self._pinch_frames = 0
        self._release_frames = 0
        self._is_grabbing = False
        self._gesture = GESTURE_NONE
        self._landmarks = None
        self._hand_detected = False

        # Trail for visual feedback
        self._trail: list[tuple[int, int]] = []
        self._max_trail = 20

        # Frame timestamp counter for VIDEO mode
        self._frame_ts = 0

    @property
    def cursor_pos(self) -> tuple[int, int]:
        return (self._cursor_x, self._cursor_y)

    @property
    def is_grabbing(self) -> bool:
        return self._is_grabbing

    @property
    def gesture(self) -> str:
        return self._gesture

    @property
    def hand_detected(self) -> bool:
        return self._hand_detected

    @property
    def trail(self) -> list[tuple[int, int]]:
        return list(self._trail)

    def process_frame(self, frame: np.ndarray):
        """Process a camera frame and update gesture state."""
        if self._landmarker is None:
            self._hand_detected = False
            self._gesture = GESTURE_NONE
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_ts += 33  # ~30fps in milliseconds
        result = self._landmarker.detect_for_video(mp_image, self._frame_ts)

        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            self._hand_detected = True
            landmarks = result.hand_landmarks[0]
            self._landmarks = landmarks

            self._update_cursor(landmarks)
            self._detect_gesture(landmarks)
            self._update_grab_state()

            self._trail.append((self._cursor_x, self._cursor_y))
            if len(self._trail) > self._max_trail:
                self._trail.pop(0)
        else:
            self._hand_detected = False
            self._landmarks = None
            self._gesture = GESTURE_NONE
            self._release_frames += 1
            if self._release_frames > RELEASE_HOLD_FRAMES:
                self._is_grabbing = False
            self._trail.clear()

    def _update_cursor(self, landmarks):
        """Update smoothed cursor position from index finger tip."""
        index_tip = landmarks[INDEX_FINGER_TIP]

        # Mirror X so moving hand right moves cursor right
        raw_x = int((1.0 - index_tip.x) * WINDOW_WIDTH)
        raw_y = int(index_tip.y * WINDOW_HEIGHT)

        # Smooth interpolation
        self._cursor_x = int(
            self._cursor_x * HAND_SMOOTHING + raw_x * (1 - HAND_SMOOTHING)
        )
        self._cursor_y = int(
            self._cursor_y * HAND_SMOOTHING + raw_y * (1 - HAND_SMOOTHING)
        )

    def _detect_gesture(self, landmarks):
        """Classify current hand gesture."""
        thumb_tip = landmarks[THUMB_TIP]
        index_tip = landmarks[INDEX_FINGER_TIP]
        middle_tip = landmarks[MIDDLE_FINGER_TIP]
        ring_tip = landmarks[RING_FINGER_TIP]
        pinky_tip = landmarks[PINKY_TIP]

        index_mcp = landmarks[INDEX_FINGER_MCP]
        middle_mcp = landmarks[MIDDLE_FINGER_MCP]
        ring_mcp = landmarks[RING_FINGER_MCP]
        pinky_mcp = landmarks[PINKY_MCP]

        # Calculate distances
        thumb_index_dist = self._distance(thumb_tip, index_tip)

        # Check if fingers are extended
        index_extended = index_tip.y < index_mcp.y
        middle_extended = middle_tip.y < middle_mcp.y
        ring_extended = ring_tip.y < ring_mcp.y
        pinky_extended = pinky_tip.y < pinky_mcp.y

        extended_count = sum(
            [index_extended, middle_extended, ring_extended, pinky_extended]
        )

        # Pinch: thumb and index close together
        if thumb_index_dist < PINCH_THRESHOLD / WINDOW_WIDTH:
            self._gesture = GESTURE_PINCH
        # Fist: no fingers extended
        elif extended_count == 0:
            self._gesture = GESTURE_FIST
        # Point: only index extended
        elif index_extended and not middle_extended and not ring_extended:
            self._gesture = GESTURE_POINT
        # Peace: index and middle extended
        elif index_extended and middle_extended and not ring_extended:
            self._gesture = GESTURE_PEACE
        # Open hand: all fingers extended
        elif extended_count >= 3:
            self._gesture = GESTURE_OPEN
        else:
            self._gesture = GESTURE_NONE

    def _update_grab_state(self):
        """Update grab/release state with hysteresis."""
        if self._gesture == GESTURE_PINCH:
            self._release_frames = 0
            self._pinch_frames += 1
            if self._pinch_frames >= GRAB_HOLD_FRAMES:
                self._is_grabbing = True
        else:
            self._pinch_frames = 0
            self._release_frames += 1
            if self._release_frames >= RELEASE_HOLD_FRAMES:
                self._is_grabbing = False

    @staticmethod
    def _distance(p1, p2) -> float:
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def draw_debug(self, frame: np.ndarray) -> np.ndarray:
        """Draw hand landmarks on camera frame for debug view."""
        if self._landmarks is not None:
            h, w, _ = frame.shape
            for lm in self._landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                color = (0, 255, 0) if not self._is_grabbing else (0, 0, 255)
                cv2.circle(frame, (cx, cy), 3, color, -1)
        return frame

    def release(self):
        """Release MediaPipe resources."""
        if self._landmarker is not None:
            self._landmarker.close()
