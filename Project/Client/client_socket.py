import socket
from Common.sending_datatypes import SendingDatatype

MAX_MSG_LENGTH = 1024
CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 1234


def start_client_socket(email: str, data: bytes, datatype: SendingDatatype) -> None:
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((CLIENT_IP, CLIENT_PORT))

        # Sending: length - 8 chars | Data Type - 1 char | Email Address length - 2 chars
        pre_data = (str(len(data)).zfill(8) + str(SendingDatatype.value) + str(len(email)).zfill(2)).encode()
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


if __name__ == '__main__':
    start_client_socket('', b'', None)
