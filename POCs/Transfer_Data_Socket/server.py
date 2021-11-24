import socket
import pickle
from matplotlib import pyplot as plt

LOCALHOST = "127.0.0.1"
PORT = 1234

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

serverSocket.bind((LOCALHOST, PORT))
serverSocket.listen(1)
clientSocket = None

while not clientSocket:
    clientSocket, address = serverSocket.accept()
length = int(clientSocket.recv(8).decode())
obj = clientSocket.recv(length)
if clientSocket:
    clientSocket.close()
    clientSocket = None

serverSocket.close()

image_array = pickle.loads(obj)
plt.imshow(image_array)
plt.show()
