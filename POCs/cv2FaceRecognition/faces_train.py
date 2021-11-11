import pickle
from cv2 import cv2
import os
import numpy as np
from PIL import Image

DIR = os.path.dirname(os.path.abspath(__file__)) + '\\'

face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_alt2.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

y_labels = []
x_train = []
current_id = 0
label_ids = {}

images = [img for img in os.listdir(DIR) if img.lower()[-3:] in ['jpg', 'png']]
for path in images:
    label = path[:-8]  # Format: name (1).jpg / name (1).png
    if label not in label_ids:
        label_ids[label] = current_id
        current_id += 1
    _id = label_ids[label]
    pil_image = Image.open(path).convert('L')
    image_array = np.array(pil_image, 'uint8')
    faces = face_cascade.detectMultiScale(image_array, scaleFactor=1.05, minNeighbors=5)
    for (x, y, w, h) in faces:
        if w < 200 or h < 200:
            continue
        roi = image_array[y:y + h, x:x + w]
        x_train.append(roi)
        y_labels.append(_id)

with open('labels.pickle', 'wb') as f:
    pickle.dump(label_ids, f)

recognizer.train(x_train, np.array(y_labels))
recognizer.save("trainer.yml")
