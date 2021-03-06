import pickle

from encryptor import Encryptor
from my_key import get_common_key
from operation_result import OperationResultType
import db_manager
import face_scanner
from email_sender import send_email

KEY = get_common_key()
COMMON_ENCRYPTOR = Encryptor(KEY)


def ext_sign_in_handler(email: str, encrypted_password) -> OperationResultType:
    try:
        password, _ = COMMON_ENCRYPTOR.decrypt_text(encrypted_password)
        operation_result = db_manager.sign_in(email, password)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR


def ext_sign_up_handler(email: str, encrypted_password: bytes, roi_3_serialized: bytes) -> OperationResultType:
    try:
        password, _ = COMMON_ENCRYPTOR.decrypt_text(encrypted_password)
        operation_result = db_manager.sign_up(email, password)
        if operation_result != OperationResultType.SUCCEEDED:
            return operation_result

        roi_3 = pickle.loads(roi_3_serialized)
        operation_result, model_path = face_scanner.create_model(roi_3)
        if operation_result != OperationResultType.SUCCEEDED:
            return operation_result
        operation_result = db_manager.store_model(email, model_path)
        send_email(email)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR


def ext_scan_image_handler(email: str, roi_serialized: bytes) -> OperationResultType:
    try:
        roi = pickle.loads(roi_serialized)
        operation_result = face_scanner.scan_with_model(email, roi)
        return operation_result
    except:
        return OperationResultType.UNKNOWN_ERROR
