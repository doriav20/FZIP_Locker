import socket
import pickle
import numpy as np
from PIL import Image

LOCALHOST = "127.0.0.1"
PORT = 1234

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((LOCALHOST, PORT))

done = False

pil_image = Image.open('./picture.jpg')
image_array = np.array(pil_image, 'uint8')
obj = pickle.dumps(image_array)

length = str(len(obj)).zfill(8)
clientSocket.send(length.encode())
clientSocket.send(obj)

clientSocket.close()
