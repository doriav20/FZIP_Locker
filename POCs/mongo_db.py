import pymongo.errors
from pymongo import MongoClient
from encryptor import Encryptor

cluster = MongoClient('mongodb://localhost:27017')
db = cluster['***db_name***']
collection = db['***collection_name***']


def add_account(email: str, encrpyted_pass: bytes):
    try:
        collection.insert_one({'email': email, 'password': encrpyted_pass})
    except pymongo.errors.DuplicateKeyError:
        print("Duplicate Email Key")


enc = Encryptor()

email = "***User's Email Here***"
password = enc.encrypt_message("***User's Password Here***")

add_account(email, password)

# result = collection.find({'email': email})
# result = collection.find()
# for account in result:
#     print(account)
