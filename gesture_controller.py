"""
Hand tracking for direction, speed boost, and dropping hand-walls.

Direction uses the wrist-to-index vector (more stable than swipe).
Peace sign (index + middle up) drops a hand-wall at the palm's mapped cell.
"""

from typing import Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from config import GRID_COLS, GRID_ROWS


class GestureController:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
            model_complexity=0,
        )
        self.current_direction: Optional[str] = None
        self._peace_held = False
        self._last_grid_cell: Optional[Tuple[int, int]] = None

    def close(self):
        self.hands.close()

    def detect(self, frame: np.ndarray) -> dict:
        """
        Returns:
            direction: UP/DOWN/LEFT/RIGHT or None
            pinch: speed boost
            drop_wall: True once when a peace sign is first held
            grid_cell: (x, y) under the palm, or None
            annotated: BGR frame
            has_hand: whether a hand is visible
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True
        annotated = frame.copy()

        direction = None
        pinch = False
        drop_wall = False
        grid_cell = None
        has_hand = False

        if results.multi_hand_landmarks:
            has_hand = True
            hand = results.multi_hand_landmarks[0]
            self.mp_drawing.draw_landmarks(
                annotated,
                hand,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(80, 220, 160), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(80, 160, 255), thickness=2),
            )

            lm = hand.landmark
            wrist = lm[self.mp_hands.HandLandmark.WRIST]
            index_tip = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_tip = lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            ring_tip = lm[self.mp_hands.HandLandmark.RING_FINGER_TIP]
            pinky_tip = lm[self.mp_hands.HandLandmark.PINKY_TIP]
            thumb_tip = lm[self.mp_hands.HandLandmark.THUMB_TIP]
            index_pip = lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
            middle_pip = lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
            ring_pip = lm[self.mp_hands.HandLandmark.RING_FINGER_PIP]
            pinky_pip = lm[self.mp_hands.HandLandmark.PINKY_PIP]

            dx = index_tip.x - wrist.x
            dy = index_tip.y - wrist.y
            if np.hypot(dx, dy) > 0.12:
                if abs(dx) > abs(dy):
                    direction = "RIGHT" if dx > 0 else "LEFT"
                else:
                    direction = "DOWN" if dy > 0 else "UP"
                self.current_direction = direction

            thumb = np.array([thumb_tip.x, thumb_tip.y])
            index = np.array([index_tip.x, index_tip.y])
            pinch = float(np.linalg.norm(thumb - index)) < 0.055

            index_up = index_tip.y < index_pip.y - 0.02
            middle_up = middle_tip.y < middle_pip.y - 0.02
            ring_down = ring_tip.y > ring_pip.y - 0.01
            pinky_down = pinky_tip.y > pinky_pip.y - 0.01
            peace = index_up and middle_up and ring_down and pinky_down and not pinch

            palm_x = (wrist.x + lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x) / 2
            palm_y = (wrist.y + lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y) / 2
            grid_cell = (
                int(np.clip(palm_x * GRID_COLS, 0, GRID_COLS - 1)),
                int(np.clip(palm_y * GRID_ROWS, 0, GRID_ROWS - 1)),
            )
            self._last_grid_cell = grid_cell

            if peace and not self._peace_held:
                drop_wall = True
                self._peace_held = True
            elif not peace:
                self._peace_held = False

            h, w = annotated.shape[:2]
            cx, cy = int(palm_x * w), int(palm_y * h)
            cv2.circle(annotated, (cx, cy), 10, (255, 180, 60), 2)

            label = self.current_direction or "—"
            cv2.putText(
                annotated,
                f"{label}  {'BOOST' if pinch else ''}  {'WALL' if peace else ''}",
                (12, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (80, 255, 200),
                2,
            )
        else:
            self._peace_held = False

        return {
            "direction": self.current_direction if has_hand else None,
            "pinch": pinch,
            "drop_wall": drop_wall,
            "grid_cell": grid_cell,
            "annotated": annotated,
            "has_hand": has_hand,
        }

    def reset(self):
        self.current_direction = None
        self._peace_held = False
        self._last_grid_cell = None
