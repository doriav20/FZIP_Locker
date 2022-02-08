import pickle
import socket
import threading

import server_external_handlers as external

from operation_result import OperationResultType
from sending_datatypes import SendingDatatype

LOCALHOST = '127.0.0.1'
PORT = 1234


def conn_with_client(client_socket: socket.socket) -> None:
    try:
        # while True:
        request = client_socket.recv(3)
        if request == b'TDR':  # TDR - Transfer Data Request
            client_socket.send(b'TDR_ACK')
        else:
            if client_socket:
                client_socket.close()
            return
            # break

        pre_data = client_socket.recv(9).decode()
        if not pre_data:
            if client_socket:
                client_socket.close()
            return
            # break
        length = int(pre_data[:-1])
        datatype = SendingDatatype(int(pre_data[-1]))

        client_socket.send(b'START_TD')

        data_serialized = client_socket.recv(length)
        if not data_serialized:
            if client_socket:
                client_socket.close()
            return
            # break
        data = pickle.loads(data_serialized)
        operation_result = data_handler(data, datatype)

        client_socket.send(str(operation_result.value).encode())

        if client_socket:
            client_socket.close()
    except:
        try:
            if client_socket:
                client_socket.close()
        except:
            pass


def data_handler(data: dict, datatype: SendingDatatype) -> OperationResultType:
    if datatype == SendingDatatype.SignIn:
        email = data.get('email')
        encrypted_password = data.get('encrypted_password')
        if None in [email, encrypted_password]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = external.ext_sign_in_handler(email, encrypted_password)
        print('Sign in:', operation_result)
        return operation_result

    elif datatype == SendingDatatype.Registration:
        email = data.get('email')
        encrypted_password = data.get('encrypted_password')
        roi_3 = data.get('roi_3')
        if None in [email, encrypted_password, roi_3]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = external.ext_sign_up_handler(email, encrypted_password, roi_3)
        print('Sign up:', operation_result)
        return operation_result

    else:  # datatype == SendingDatatype.ScanFaceImage
        email = data.get('email')
        roi = data.get('roi')
        if None in [email, roi]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = external.ext_scan_image_handler(email, roi)
        print('Scan Face:', operation_result)
        return operation_result


def start_server() -> None:
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((LOCALHOST, PORT))
        server_socket.listen(5)
        while True:
            client_socket, address = server_socket.accept()
            threading.Thread(target=conn_with_client, args=[client_socket]).start()
    except:
        if server_socket:
            server_socket.close()


if __name__ == '__main__':
    start_server()
