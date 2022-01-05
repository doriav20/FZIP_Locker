from typing import Tuple

import numpy as np
from cv2 import cv2

face_cascade = cv2.CascadeClassifier('./haarcascade_frontalface_alt2.xml')


def detect_face() -> Tuple[np.ndarray, np.ndarray]:
    cap = cv2.VideoCapture(0)
    roi_gray = None
    roi_preview = None
    times = 0
    while times < 5:
        ret, frame = cap.read()
        frame_h = frame.shape[0]
        frame_w = frame.shape[1]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
        for (x, y, w, h) in faces:
            if not (w >= 200 and h >= 200):
                continue
            roi_gray = gray[y:y + h, x:x + w]  # (ycord_start, ycord_end)

            roi_preview = frame[max(y - 50, 0):min(y + h + 50, frame_h), max(x - 50, 0):min(x + w + 50, frame_w)]

            times += 1

        cv2.imshow('Look at the camera', frame)
        if cv2.waitKey(20) == 27:
            roi_gray, roi_preview = None, None
            break

    cap.release()
    cv2.destroyAllWindows()

    return roi_gray, roi_preview
