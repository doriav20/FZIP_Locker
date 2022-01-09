import os
import pymongo.errors
from pymongo import MongoClient
from Common.encryptor import Encryptor
import pickle
from datetime import datetime

from Common.operation_result import OperationResultType

cluster = MongoClient('mongodb://localhost:27017',
                      serverSelectionTimeoutMS=5 * 1000)  # Timeout for each finding / updating
db = cluster['users']
collection = db['users']


def register(email: str, password: str) -> OperationResultType:
    try:
        creation_time = str(datetime.now())
        # Creating key depends on registration time - Importance is that each user has a different key
        new_key = pickle.dumps(creation_time)[7:39]

        encryptor = Encryptor(new_key)
        new_encrypted_password = encryptor.encrypt_text(password)

        collection.insert_one({'email': email,
                               'password': new_encrypted_password,
                               'creation_time': creation_time})
        return OperationResultType.SUCCEEDED
    except pymongo.errors.DuplicateKeyError:  # Email is already in use
        return OperationResultType.DETAILS_ERROR
    except pymongo.errors.ServerSelectionTimeoutError:
        print('ggg')
        return OperationResultType.CONNECTION_ERROR
    except:  # pymongo.errors.DuplicateKeyError
        return OperationResultType.UNKNOWN_ERROR


def sign_in(email: str, password: str) -> OperationResultType:
    try:
        user = collection.find_one({'email': email})
        if user is None:
            return OperationResultType.DETAILS_ERROR  # User does not exist

        creation_time = user['creation_time']
        key = pickle.dumps(creation_time)[7:39]

        encryptor = Encryptor(key)
        true_password, _ = encryptor.decrypt_text(user['password'])

        if true_password == password:
            return OperationResultType.SUCCEEDED
        else:
            return OperationResultType.DETAILS_ERROR
    except pymongo.errors.ServerSelectionTimeoutError:
        return OperationResultType.CONNECTION_ERROR
    except:
        return OperationResultType.UNKNOWN_ERROR


def store_model(email: str, model_path: str) -> OperationResultType:
    try:
        user = collection.find_one({'email': email})

        creation_time = user['creation_time']
        key = pickle.dumps(creation_time)[7:39]

        encryptor = Encryptor(key)
        encrypted_model = encryptor.encrypt_file(model_path)

        os.remove(model_path)

        collection.update_one(user, {'$set': {'model': encrypted_model}})
        return OperationResultType.SUCCEEDED
    except pymongo.errors.ServerSelectionTimeoutError:
        return OperationResultType.CONNECTION_ERROR
    except:
        return OperationResultType.UNKNOWN_ERROR


def get_model(email: str) -> bytes:
    try:
        user = collection.find_one({'email': email})
        if user is None:
            return b''

        creation_time = user['creation_time']
        key = pickle.dumps(creation_time)[7:39]

        encryptor = Encryptor(key)
        model, _ = encryptor.decrypt_text(user['model'], decode=False)
        return model
    except:
        return b''
