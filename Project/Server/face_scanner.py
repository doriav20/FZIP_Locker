import numpy as np
from cv2 import cv2
import random
from db_manager import store_model, get_model
from Common.details_generator import generate_unique_id

Images = [np.ndarray, np.ndarray, np.ndarray]  # Type alias


def create_model(email: str, images: Images) -> bool:
    try:
        x_train = []
        y_labels = []
        for img in images:
            x_train.append(img)
            y_labels.append(0)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(x_train, np.array(y_labels))

        model_path = f'./trainer_{generate_unique_id(16)}.yml'
        recognizer.save(model_path)

        result = store_model(email, model_path)
        return result
    except:
        return False


def scan_with_model(email: str, image: np.ndarray) -> bool:
    try:
        model = get_model(email)
        if model is None:
            return False
        model_path = f'./trainer_{generate_unique_id(16)}.yml'

        with open(model_path, 'wb') as file:
            file.write(model)

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(model_path)
        _, conf = recognizer.predict(image)

        conf = 100 - conf
        print(conf)
        if conf >= 72:
            return True
        else:
            return False
    except:
        return False
