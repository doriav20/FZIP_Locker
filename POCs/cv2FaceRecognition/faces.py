import pickle
from cv2 import cv2

face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_alt2.xml')

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer.yml')

with open('labels.pickle', 'rb') as f:
    label_ids = pickle.load(f)
    label_ids = {v: k for k, v in label_ids.items()}

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5)
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y + h, x:x + w]  # (ycord_start, ycord_end)

        _id, conf = recognizer.predict(roi_gray)
        real_conf = 100 - conf
        print(real_conf)
        if real_conf >= 60:
            font = cv2.FONT_HERSHEY_SIMPLEX
            name = label_ids[_id]
            color = (255, 255, 255)
            stroke = 2
            cv2.putText(frame, name, (x, y-10), font, 1, color, stroke, cv2.LINE_AA)

        color = (255, 0, 0)  # BGR 0-255
        stroke = 2

        end_cord_x = x + w
        end_cord_y = y + h

        cv2.rectangle(frame, (x, y), (end_cord_x, end_cord_y), color, stroke)

    cv2.imshow('frame', frame)
    if cv2.waitKey(20) & 0XFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
