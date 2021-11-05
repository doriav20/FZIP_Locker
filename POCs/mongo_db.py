import pymongo.errors
from pymongo import MongoClient
from encryptor import Encryptor
import pickle

cluster = MongoClient('mongodb://localhost:27017')
db = cluster['***db_name***']
collection = db['***collection_name***']


def add_account(email: str, encrpyted_pass: bytes):
    try:
        collection.insert_one({'email': email, 'password': encrpyted_pass, 'files': []})
    except pymongo.errors.DuplicateKeyError:
        print('Duplicate Email Key')


def serialization(obj):
    return pickle.dumps(obj)


def deserialization(obj):
    return pickle.loads(obj)


enc = Encryptor()

email = "***User's Email Here***"
password = enc.encrypt_message("***User's Password Here***")

add_account(email, password)

collection.update_one({'email': email}, {'$push': {'files': '***filename***'}})

# result = collection.find({'email': email})
# result = collection.find()
# for account in result:
#     print(account)
