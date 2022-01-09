import socket

from Common.operation_result import OperationResultType
from Common.sending_datatypes import SendingDatatype
import pickle

MAX_MSG_LENGTH = 1024
CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 1234


def start_client_socket(data: bytes, datatype: SendingDatatype) -> None:
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((CLIENT_IP, CLIENT_PORT))

        # Sending: length - 8 chars | Data Type - 1 char
        pre_data = (str(len(data)).zfill(8) + str(datatype.value)).encode()
        client_socket.send(pre_data)

        # 0 - Bad | 1 - OK
        communication_status = client_socket.recv(1)
        if communication_status == b'1':
            client_socket.send(data)
            client_socket.close()
        else:
            client_socket.close()
    except:
        if client_socket:
            client_socket.close()


def send_data(data: dict, datatype: SendingDatatype) -> OperationResultType:
    from Server import server_external_handlers
    if datatype == SendingDatatype.SignIn:
        email = data.get('email')
        encrypted_password = data.get('encrypted_password')
        if None in [email, encrypted_password]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = server_external_handlers.ext_sign_in_handler(email, encrypted_password)
        print('Sign in:', operation_result)
        return operation_result

    elif datatype == SendingDatatype.Registration:
        email = data.get('email')
        encrypted_password = data.get('encrypted_password')
        roi_3 = data.get('roi_3')
        if None in [email, encrypted_password, roi_3]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = server_external_handlers.ext_register_handler(email, encrypted_password, roi_3)
        print('Sign up:', operation_result)
        return operation_result

    elif datatype == SendingDatatype.ScanFaceImage:
        email = data.get('email')
        roi = data.get('roi')
        if None in [email, roi]:  # One of parameters was not provided
            return OperationResultType.UNKNOWN_ERROR
        operation_result = server_external_handlers.ext_scan_image_handler(email, roi)
        print('Scan Face:', operation_result)
        return operation_result

    else:
        return OperationResultType.UNKNOWN_ERROR
