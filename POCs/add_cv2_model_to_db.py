from encryptor import Encryptor
from pymongo import MongoClient
import Crypto.Random

cluster = MongoClient('mongodb://localhost:27017')
db = cluster['***db_name***']
collection = db['***collection_name***']

ENCRYPTION_KEY = Crypto.Random.get_random_bytes(32)


def store_model_db(model_path):
    with open(model_path, 'rb') as model_file:
        model_content = model_file.read()
    enc = Encryptor(ENCRYPTION_KEY)
    encrypted_model = enc.encrypt(model_content)
    collection.insert_one({'model': encrypted_model})


def save_model():
    model_binary_content = collection.find_one()
    enc = Encryptor(ENCRYPTION_KEY)
    decrypted_model = enc.decrypt(model_binary_content['model'])
    with open('./model.yml', 'wb') as model_file:
        model_file.write(decrypted_model)


if __name__ == '__main__':
    collection.delete_many({})
    store_model_db('***model_path***')
    save_model()
