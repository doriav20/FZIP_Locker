import os

from pymongo import MongoClient
from Common.encryptor import Encryptor
import pickle
from datetime import datetime


cluster = MongoClient('mongodb://localhost:27017')
db = cluster['users']
collection = db['users']

simple_key = b'1' * 32  # TODO key logic - CLIENT


def register(email: str, encrypted_password: bytes, roi:np.ndarray) -> bool:
    try:
        password = Encryptor.decrypt_message(simple_key, encrypted_password)

        creation_time = str(datetime.now())
        # Creating key depends on registration time - Importance is that each user has a different key
        new_key = pickle.dumps(creation_time)[7:39]
        new_encrypted_password = Encryptor.encrypt_message(new_key, password)

        collection.insert_one({'email': email, 'password': new_encrypted_password, 'created_time': creation_time})
        return True
    except:  # pymongo.errors.DuplicateKeyError
        return False


def sign_in(email: str, encrypted_password: bytes) -> bool:
    user = collection.find_one({'email': email})
    if user is None:
        return False

    try:
        password = Encryptor.decrypt_message(simple_key, encrypted_password)

        creation_time = user['created_time']
        key = pickle.dumps(creation_time)[7:39]
        true_password = Encryptor.decrypt_message(key, user['password'])

        return true_password == password
    except:
        return False


def store_model(email: str, model_path: str) -> bool:
    user = collection.find_one({'email': email})
    if user is None:
        return False

    try:
        creation_time = user['created_time']
        key = pickle.dumps(creation_time)[7:39]

        encrypted_model = Encryptor.encrypt_file(key, model_path)
        os.remove(model_path)
        collection.update_one(user, {'$set': {'model': encrypted_model}})
        return True
    except:
        return False


def get_model(email: str) -> bytes:
    user = collection.find_one({'email': email})
    if user is None:
        return None
    try:
        creation_time = user['created_time']
        key = pickle.dumps(creation_time)[7:39]

        model = Encryptor.decrypt(key, user['model'])
        return model
    except:
        return None


def user_exists(email: str) -> bool:
    return collection.find_one({'email': email}) is not None
