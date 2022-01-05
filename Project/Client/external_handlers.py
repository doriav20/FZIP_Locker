import pickle
from tkinter import Tk, filedialog
from typing import Tuple

import numpy as np

from Common.details_generator import generate_unique_path
from Common.encryptor import Encryptor
from Common.my_key import get_common_key
from Common.operation_result import OperationResultType
from client_socket import send_data
from Common.sending_datatypes import SendingDatatype
from ZIP_manager import ZIPManager
import os
import shutil

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


# Compress Screen
def ext_decompress_handler_decrypt_file(encrypted_path: str) -> Tuple[OperationResultType, str]:
    try:
        path = ENCRYPTOR.decrypt_and_save_file(encrypted_path, 'zip')
        # if os.path.exists(encrypted_path):
        #     os.remove(encrypted_path)
        return OperationResultType.SUCCEEDED, path
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_decompress_handler_extract_zip(path: str, password: str, encrypted_path: str) -> OperationResultType:
    operation_result = ZIPManager.decompress(path, password)
    try:
        if os.path.exists(path):
            os.remove(path)
        # if operation_result == OperationResultType.SUCCEEDED:
        #     if os.path.exists(encrypted_path):
        #         os.remove(encrypted_path)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR


# Compress Screen
def ext_compress_handler_select_compress_files() -> Tuple[OperationResultType, Tuple[str, ...]]:
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
        # if operation_result == OperationResultType.SUCCEEDED:
        #     for path in src:
        #         if os.path.exists(path):
        #             if os.path.isdir(path):
        #                 shutil.rmtree(path)
        #             else:
        #                 os.remove(path)
        return operation_result, dest
    except:
        return OperationResultType.UNKNOWN_ERROR, ''


# Compress Screen
def ext_compress_handler_encrypt_file(encrypted_path: str) -> OperationResultType:
    try:
        path = encrypted_path[:-3] + 'zip'
        encrypted_path = ENCRYPTOR.encrypt_and_save_file(path, 'lck')
        if os.path.exists(path):
            os.remove(path)
        return OperationResultType.SUCCEEDED
    except:
        return OperationResultType.UNKNOWN_ERROR
