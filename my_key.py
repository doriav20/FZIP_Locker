import pickle
import os


# Get common key from file called key.key
def get_common_key() -> bytes:
    path = os.path.dirname(os.path.abspath(__file__)) + r'\key.key'
    key = pickle.load(open(path, mode='rb'))
    return key
