import socket

from operation_result import OperationResultType
from sending_datatypes import SendingDatatype
import pickle

HOST_IP = '127.0.0.1'
PORT = 1234


def conn_with_server(data: bytes, datatype: SendingDatatype) -> OperationResultType:
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST_IP, PORT))

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
    data_serialized = pickle.dumps(data)
    operation_result = conn_with_server(data_serialized, datatype)
    return operation_result
