from Crypto import Random
from Crypto.Cipher import AES
import os


class Encryptor:

    def __init__(self, key: bytes) -> None:
        self.__key = key

    def change_key(self, new_key: bytes):
        self.__key = new_key

    @staticmethod
    def __pad(s: bytes) -> bytes:
        byte_add = Random.get_random_bytes(1)  # Avoiding NULLs Deletion in rstrip(b'\0')
        while byte_add == b'\0':
            byte_add = Random.get_random_bytes(1)
        return s + byte_add + b'\0' * (-1 + AES.block_size - len(s) % AES.block_size)

    def __encrypt(self, bytes_content: bytes) -> bytes:
        message = Encryptor.__pad(bytes_content)
        iv = Random.get_random_bytes(AES.block_size)  # Initialization Vector
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)  # Block Chiper Mode of Operation - Output Feedback (OFB)
        return iv + cipher.encrypt(message)

    def encrypt_message(self, message: str) -> bytes:
        return self.__encrypt(message.encode())

    def encrypt_file(self, path: str) -> bytes:
        with open(path, 'rb') as file:
            file_content = file.read()
        return self.__encrypt(file_content)

    def encrypt_and_save_file(self, path: str, new_extension: str = '') -> str:
        encrypted_content = self.encrypt_file(path)
        os.remove(path)

        if new_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + new_extension
            else:
                path = path + '.' + new_extension

        with open(path, 'wb') as file:
            file.write(encrypted_content)

        return path

    def __decrypt(self, encrypted_bytes_content: bytes) -> bytes:
        iv = encrypted_bytes_content[:AES.block_size]
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)
        plaintext = cipher.decrypt(encrypted_bytes_content[AES.block_size:])
        return plaintext.rstrip(b'\0')[:-1]

    def decrypt_message(self, encrypted_message: bytes) -> str:
        return self.__decrypt(encrypted_message).decode()

    def decrypt_file(self, path: str) -> bytes:
        with open(path, 'rb') as file:
            file_encrypted_content = file.read()

        return self.__decrypt(file_encrypted_content)

    def decrypt_and_save_file(self, path: str, old_extension: str = '') -> str:
        decrypted_content = self.decrypt_file(path)
        os.remove(path)

        if old_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + old_extension
            else:
                path = path + '.' + old_extension

        with open(path, 'wb') as file:
            file.write(decrypted_content)
        return path
