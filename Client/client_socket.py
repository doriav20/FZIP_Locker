import socket

from operation_result import OperationResultType
from sending_datatypes import SendingDatatype
import pickle

MAX_MSG_LENGTH = 1024
CLIENT_IP = '127.0.0.1'
PORT = 1234


def conn_with_server(data: bytes, datatype: SendingDatatype) -> OperationResultType:
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((CLIENT_IP, PORT))

        client_socket.send(b'TDR')  # TDR - Transfer Data Request
        response = client_socket.recv(7)
        if response != b'TDR_ACK':
            if client_socket:
                client_socket.close()
            return OperationResultType.CONNECTION_ERROR

        # Sending: length - 8 chars | Data Type - 1 char
        pre_data = (str(len(data)).zfill(8) + str(datatype.value)).encode()
        client_socket.send(pre_data)
        response = client_socket.recv(8)

        if response != b'START_TD':
            if client_socket:
                client_socket.close()
            return OperationResultType.CONNECTION_ERROR

        client_socket.send(data)
        response = client_socket.recv(1)

        operation_result = OperationResultType(int(response))
        return operation_result
    except:
        try:
            if client_socket:
                client_socket.close()
        except:
            pass
        return OperationResultType.CONNECTION_ERROR


def send_data(data: dict, datatype: SendingDatatype) -> OperationResultType:
    # from Server import server_external_handlers
    # if datatype == SendingDatatype.SignIn:
    #     email = data.get('email')
    #     encrypted_password = data.get('encrypted_password')
    #     if None in [email, encrypted_password]:  # One of parameters was not provided
    #         return OperationResultType.UNKNOWN_ERROR
    #     operation_result = server_external_handlers.ext_sign_in_handler(email, encrypted_password)
    #     print('Sign in:', operation_result)
    #     return operation_result
    #
    # elif datatype == SendingDatatype.Registration:
    #     email = data.get('email')
    #     encrypted_password = data.get('encrypted_password')
    #     roi_3 = data.get('roi_3')
    #     if None in [email, encrypted_password, roi_3]:  # One of parameters was not provided
    #         return OperationResultType.UNKNOWN_ERROR
    #     operation_result = server_external_handlers.ext_sign_up_handler(email, encrypted_password, roi_3)
    #     print('Sign up:', operation_result)
    #     return operation_result
    #
    # elif datatype == SendingDatatype.ScanFaceImage:
    #     email = data.get('email')
    #     roi = data.get('roi')
    #     if None in [email, roi]:  # One of parameters was not provided
    #         return OperationResultType.UNKNOWN_ERROR
    #     operation_result = server_external_handlers.ext_scan_image_handler(email, roi)
    #     print('Scan Face:', operation_result)
    #     return operation_result
    data_serialized = pickle.dumps(data)
    operation_result = conn_with_server(data_serialized, datatype)
    return operation_result
