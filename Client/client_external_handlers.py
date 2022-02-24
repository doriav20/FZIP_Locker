import pickle
from tkinter import Tk, filedialog
from typing import Tuple

import numpy as np

from encryptor import Encryptor
from my_key import get_common_key
from operation_result import OperationResultType
from client_socket import send_data
from sending_datatypes import SendingDatatype
from ZIP_manager import ZIPManager
import os

KEY = get_common_key()
ENCRYPTOR = Encryptor(KEY)

USER_EMAIL = ''


# Sign in Screen - user sign in: authenticate the user in server side
def ext_sign_in_handler(email: str, password: str) -> OperationResultType:
    encrypted_password = ENCRYPTOR.encrypt_text(password)
    data = {'email': email,
            'encrypted_password': encrypted_password}
    operation_result = send_data(data, SendingDatatype.SignIn)
    if operation_result == OperationResultType.SUCCEEDED:
        global USER_EMAIL
        USER_EMAIL = email
    return operation_result


# Sign Up Screen - after three scans user sign up: add user to DB in server side
def ext_sign_up_handler(email: str, password: str,
                         roi_3: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> OperationResultType:
    encrypted_password = ENCRYPTOR.encrypt_text(password)
    roi_3_serialized = pickle.dumps(roi_3)
    data = {'email': email,
            'encrypted_password': encrypted_password,
            'roi_3': roi_3_serialized}
    operation_result = send_data(data, SendingDatatype.Registration)
    if operation_result == OperationResultType.SUCCEEDED:
        global USER_EMAIL
        USER_EMAIL = email
    return operation_result


# Compress Screen
def ext_logout_handler() -> None:
    global USER_EMAIL
    USER_EMAIL = ''


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
    roi_serialized = pickle.dumps(roi)
    data = {'email': USER_EMAIL,
            'roi': roi_serialized}
    operation_result = send_data(data, SendingDatatype.ScanFaceImage)
    return operation_result


# Compress Screen
def ext_decompress_handler_decrypt_file(encrypted_path: str) -> Tuple[OperationResultType, str]:
    try:
        path, prefix = ENCRYPTOR.decrypt_and_save_file(encrypted_path, 'zip')
        if USER_EMAIL != prefix:
            os.remove(path)
            return OperationResultType.DETAILS_ERROR, ''
        return OperationResultType.SUCCEEDED, path
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_decompress_handler_extract_zip(path: str, password: str) -> OperationResultType:
    operation_result = ZIPManager.decompress(path, password)
    try:
        if os.path.exists(path):
            os.remove(path)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR


# Compress Screen
def ext_compress_handler_select_compress_files() -> Tuple[OperationResultType, Tuple[str, ...]]:
    try:
        Tk().withdraw()
        paths = filedialog.askopenfilenames(title='Select files to compress',
                                            initialdir='')
        if paths:
            return OperationResultType.SUCCEEDED, paths
        else:
            return OperationResultType.DETAILS_ERROR, ('',)
    except:
        return OperationResultType.UNKNOWN_ERROR, ('',)


# Compress Screen
def ext_compress_handler_save_as_lock_file() -> Tuple[OperationResultType, str]:
    try:
        Tk().withdraw()
        path = filedialog.asksaveasfilename(title='Select compressed file to decompress',
                                            initialdir='',
                                            defaultextension='lck',
                                            filetypes=(('Lock files', '*.lck'),))

        if path:
            if not path.endswith('.lck'):
                path = path.replace(path[path.rfind('.') + 1:], 'lck')
            return OperationResultType.SUCCEEDED, path
        else:
            return OperationResultType.DETAILS_ERROR, ''
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_compress_handler_archive_zip(src: Tuple[str, ...], encrypted_path: str, password: str) \
        -> Tuple[OperationResultType, str]:
    dest = encrypted_path[:-3] + 'zip'
    operation_result = ZIPManager.compress(src, dest, password)
    try:
        return operation_result, dest
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_compress_handler_encrypt_file(encrypted_path: str) -> OperationResultType:
    try:
        path = encrypted_path[:-3] + 'zip'
        encrypted_path = ENCRYPTOR.encrypt_and_save_file(path, 'lck', prefix=USER_EMAIL)
        if os.path.exists(path):
            os.remove(path)
        return OperationResultType.SUCCEEDED
    except:
        return OperationResultType.UNKNOWN_ERROR
