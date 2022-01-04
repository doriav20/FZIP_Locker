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
    return OperationResultType.SUCCEEDED
    # encoded_data = pickle.dumps(data)
    # start_client_socket(encoded_data, datatype)
    # return OperationResultType.SUCCEEDED
