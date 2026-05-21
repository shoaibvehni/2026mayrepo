"""Utility functions for the puzzle game."""

import os

import cv2
import numpy as np


def load_image(path: str) -> np.ndarray | None:
    """Load an image from file path."""
    if not os.path.exists(path):
        return None
    img = cv2.imread(path)
    if img is None:
        return None
    return img


def generate_sample_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Generate a colorful sample image for puzzle use without a camera."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Create a colorful gradient pattern
    for y in range(height):
        for x in range(width):
            r = int(127 + 127 * np.sin(x * 0.02))
            g = int(127 + 127 * np.sin(y * 0.02 + 2.0))
            b = int(127 + 127 * np.sin((x + y) * 0.015 + 4.0))
            img[y, x] = [b, g, r]

    # Add some geometric shapes for visual distinction
    cv2.circle(img, (width // 4, height // 4), 60, (0, 200, 255), -1)
    cv2.circle(img, (3 * width // 4, height // 4), 45, (255, 100, 0), -1)
    cv2.rectangle(
        img,
        (width // 3, 2 * height // 3 - 40),
        (width // 3 + 80, 2 * height // 3 + 40),
        (0, 255, 100),
        -1,
    )
    cv2.putText(
        img,
        "PUZZLE",
        (width // 2 - 100, height // 2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (255, 255, 255),
        3,
    )

    # Add triangle
    pts = np.array(
        [
            [3 * width // 4, 2 * height // 3 - 50],
            [3 * width // 4 - 50, 2 * height // 3 + 40],
            [3 * width // 4 + 50, 2 * height // 3 + 40],
        ],
        np.int32,
    )
    cv2.fillPoly(img, [pts], (200, 50, 255))

    return img


def capture_from_camera(camera_id: int = 0) -> cv2.VideoCapture | None:
    """Open camera and return VideoCapture object."""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))
