from Crypto import Random
from Crypto.Cipher import AES
import os
import os.path


class Encryptor:
    def __init__(self, _key: bytes = Random.get_random_bytes(32)):
        self.__key = _key

    def pad(self, s: bytes):
        byte_add = Random.get_random_bytes(1)  # Avoiding NULLs Deletion in rstrip(b'\0')
        while byte_add == b'\0':
            byte_add = Random.get_random_bytes(1)
        return s + byte_add + b'\0' * (-1 + AES.block_size - len(s) % AES.block_size)

    def encrypt(self, bytes_message: bytes):
        message = self.pad(bytes_message)
        iv = Random.get_random_bytes(AES.block_size)  # Initialization Vector
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)  # Block Chiper Mode of Operation - Output Feedback (OFB)
        return iv + cipher.encrypt(message)

    def encrypt_message(self, message: str):
        return self.encrypt(message.encode())

    def encrypt_file(self, file_name: str, remove_extension=False):
        file = open(file_name, 'rb')
        plaintext = file.read()
        file.close()
        os.remove(file_name)

        if remove_extension:
            index = file_name.rfind('.')
            if index != -1:
                file_name = file_name[:index]

        enc = self.encrypt(plaintext)

        file = open(file_name + '.lck', 'wb')
        file.write(enc)
        file.close()

    def decrypt(self, ciphertext: bytes):
        iv = ciphertext[:AES.block_size]
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)
        plaintext = cipher.decrypt(ciphertext[AES.block_size:])
        return plaintext.rstrip(b'\0')[:-1]

    def decrypt_message(self, ciphertext: bytes):
        return self.decrypt(ciphertext).decode()

    def decrypt_file(self, file_name: str, extension=''):
        file = open(file_name, 'rb')
        ciphertext = file.read()
        file.close()

        dec = self.decrypt(ciphertext)

        file = open(file_name[:-4] + extension, 'wb')
        file.write(dec)
        file.close()
        os.remove(file_name)
