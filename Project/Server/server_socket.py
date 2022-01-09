import pickle
import socket
import threading

from Common.operation_result import OperationResultType
from Common.sending_datatypes import SendingDatatype
from Server.db_manager import user_exists

LOCALHOST = "127.0.0.1"
PORT = 1234


def job(client_socket: socket.socket) -> OperationResultType:
    try:
        while True:
            pre_data = client_socket.recv(9).decode()
            if not pre_data:
                break
            length, datatype = int(pre_data[:-1]), SendingDatatype(pre_data[-1])
            obj = client_socket.recv(length)
            if not obj:
                break
            obj = pickle.loads(obj)
            # 0 - Bad | 1 - OK
            if datatype == SendingDatatype.Registration:
                email = obj['Email']
                encrypted_password = obj['Encrypted_Password']
                roi_3 = pickle.loads(obj['roi_3'])
                if user_exists(email):
                    client_socket.send(b'0')
                    client_socket.close()
                    return OperationResultType.UNKNOWN_ERROR
                client_socket.send(b'1')

            elif datatype == SendingDatatype.SignIn:
                email = obj['Email']
                encrypted_password = obj['Encrypted_Password']
                if not user_exists(email):
                    client_socket.send(b'0')
                    client_socket.close()
                    return OperationResultType.UNKNOWN_ERROR
                client_socket.send(b'1')

            elif datatype == SendingDatatype.ScanFaceImage:
                if not user_exists(email):
                    client_socket.send(b'0')
                    client_socket.close()
                    return OperationResultType.UNKNOWN_ERROR
                client_socket.send(b'1')

            else:
                client_socket.send(b'0')
                client_socket.close()
                return OperationResultType.UNKNOWN_ERROR

        client_socket.close()
        return OperationResultType.SUCCEEDED
    except:
        return OperationResultType.UNKNOWN_ERROR


def start_server_socket() -> None:
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((LOCALHOST, PORT))
        server_socket.listen(5)
        while True:
            client_socket, address = server_socket.accept()
            threading.Thread(target=job, args=[client_socket]).start()
    except:
        if server_socket:
            server_socket.close()


if __name__ == '__main__':
    start_server_socket()
