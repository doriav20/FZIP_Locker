import os
from typing import Tuple

import numpy as np
from cv2 import cv2

from operation_result import OperationResultType
from db_manager import get_model
from details_generator import generate_unique_id


def create_model(roi_3: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> Tuple[OperationResultType, str]:
    try:
        x_train = []
        y_labels = []
        for roi_gray in roi_3:
            x_train.append(roi_gray)
            y_labels.append(0)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(x_train, np.array(y_labels))

        model_path = f'./trainer_{generate_unique_id(16)}.yml'
        recognizer.save(model_path)

        return OperationResultType.SUCCEEDED, model_path
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


def scan_with_model(email: str, roi: np.ndarray) -> OperationResultType:
    model_path = ''
    try:
        model = get_model(email)
        if not model:
            return OperationResultType.UNKNOWN_ERROR

        model_path = f'./trainer_{generate_unique_id(16)}.yml'
        with open(model_path, 'wb') as file:
            file.write(model)

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(model_path)
        _, confidence = recognizer.predict(roi)
        os.remove(model_path)

        confidence = 100 - confidence
        print(confidence)
        if confidence >= 62:
            return OperationResultType.SUCCEEDED
        else:
            return OperationResultType.DETAILS_ERROR
    except:
        try:
            if os.path.exists(model_path):
                os.remove(model_path)
        except:
            pass
        return OperationResultType.UNKNOWN_ERROR
