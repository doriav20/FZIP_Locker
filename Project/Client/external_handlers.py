import pickle
from tkinter import Tk, filedialog
from typing import Tuple

import numpy as np

from Common.encryptor import Encryptor
from Common.my_key import get_common_key
from Common.operation_result import OperationResultType
from client_socket import send_data
from Common.sending_datatypes import SendingDatatype
from ZIP_manager import ZIPManager
import os

KEY = get_common_key()
ENCRYPTOR = Encryptor(KEY)

EMAIL = ''
ENCRYPTED_PASSWORD = b''


# Login Screen - user sign in: authenticate the user in server side
def ext_sign_in_handler(email: str, password: str) -> OperationResultType:
    data = {'Email': email,
            'Encrypted_Password': ENCRYPTOR.encrypt_message(password)}
    operation_result = send_data(data, SendingDatatype.SignIn)
    return operation_result


# Register Screen - after three scans user sign up: add user to DB in server side
def ext_register_handler(email: str, password: str,
                         roi_3: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> OperationResultType:
    data = {'Email': email,
            'Encrypted_Password': ENCRYPTOR.encrypt_message(password),
            'roi_3': pickle.dumps(roi_3)}
    operation_result = send_data(data, SendingDatatype.Registration)
    return operation_result


# Compress Screen
def ext_decompress_handler_select_lock_file() -> Tuple[OperationResultType, str]:
    try:
        Tk().withdraw()
        path = filedialog.askopenfilename(title='Select compressed file to decompress',
                                          initialdir='',
                                          filetypes=(('Lock files', '*.lck'),))
        if path:
            return OperationResultType.SUCCEEDED, path
        else:
            return OperationResultType.DETAILS_ERROR, ''
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_decompress_handler_face_authentication(roi: np.ndarray) -> OperationResultType:
    data = {'Email': EMAIL,
            'Encrypted_Password': ENCRYPTED_PASSWORD,
            'roi': pickle.dumps(roi)}
    operation_result = send_data(data, SendingDatatype.ScanFaceImage)
    return operation_result


def ext_decompress_handler_decrypt_file(path: str) -> Tuple[OperationResultType, str]:
    path = ENCRYPTOR.decrypt_and_save_file(path, 'zip')
    return OperationResultType.SUCCEEDED, path


# Compress Screen
def ext_decompress_handler_extract_zip(path: str, password: str) -> OperationResultType:
    operation_result = ZIPManager.decompress(path, password)
    try:
        if operation_result == OperationResultType.SUCCEEDED:
            os.remove(path)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR


# Compress Screen
def ext_compress_handler_select_compress_files() -> Tuple[OperationResultType, Tuple[str, ...]]:
    Tk().withdraw()

    try:
        Tk().withdraw()
        paths = filedialog.askopenfilenames(title='Select files to compress',
                                            initialdir='')
        print(paths)
        if paths:
            return OperationResultType.SUCCEEDED, paths
        else:
            return OperationResultType.DETAILS_ERROR, ('',)
    except:
        return OperationResultType.UNKNOWN_ERROR, ('',)
    files2 = filedialog.asksaveasfilename(title='Save as compressed file',
                                          initialdir='',
                                          defaultextension='.lck',
                                          filetypes=(('Lock files', '*.lck'), ('All files', '*')),
                                          confirmoverwrite=True)
    return OperationResultType.SUCCEEDED
