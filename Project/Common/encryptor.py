from Crypto import Random
from Crypto.Cipher import AES
import os


class Encryptor:

    @staticmethod
    def __pad(s: bytes) -> bytes:
        byte_add = Random.get_random_bytes(1)  # Avoiding NULLs Deletion in rstrip(b'\0')
        while byte_add == b'\0':
            byte_add = Random.get_random_bytes(1)
        return s + byte_add + b'\0' * (-1 + AES.block_size - len(s) % AES.block_size)

    @staticmethod
    def __encrypt(key: bytes, bytes_content: bytes) -> bytes:
        message = Encryptor.__pad(bytes_content)
        iv = Random.get_random_bytes(AES.block_size)  # Initialization Vector
        cipher = AES.new(key, AES.MODE_OFB, iv)  # Block Chiper Mode of Operation - Output Feedback (OFB)
        return iv + cipher.encrypt(message)

    @staticmethod
    def encrypt_message(key: bytes, message: str) -> bytes:
        return Encryptor.__encrypt(key, message.encode())

    @staticmethod
    def encrypt_file(key: bytes, path: str) -> bytes:
        with open(path, 'rb') as file:
            file_content = file.read()
        return Encryptor.__encrypt(key, file_content)

    @staticmethod
    def encrypt_and_save_file(key: bytes, path: str, new_extension: str = '') -> None:
        encrypted_content = Encryptor.encrypt_file(key, path)
        os.remove(path)

        if new_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + new_extension
            else:
                path = path + '.' + new_extension

        with open(path, 'wb') as file:
            file.write(encrypted_content)

    @staticmethod
    def __decrypt(key: bytes, encrypted_bytes_content: bytes) -> bytes:
        iv = encrypted_bytes_content[:AES.block_size]
        cipher = AES.new(key, AES.MODE_OFB, iv)
        plaintext = cipher.decrypt(encrypted_bytes_content[AES.block_size:])
        return plaintext.rstrip(b'\0')[:-1]

    @staticmethod
    def decrypt(key: bytes, encrypted_bytes_content: bytes) -> bytes:
        return Encryptor.__decrypt(key, encrypted_bytes_content)

    @staticmethod
    def decrypt_message(key: bytes, encrypted_message: bytes) -> str:
        return Encryptor.__decrypt(key, encrypted_message).decode()

    @staticmethod
    def decrypt_file(key: bytes, path: str) -> bytes:
        with open(path, 'rb') as file:
            file_encrypted_content = file.read()

        return Encryptor.__decrypt(key, file_encrypted_content)

    @staticmethod
    def decrypt_and_save_file(key: bytes, path: str, old_extension: str = '') -> None:
        decrypted_content = Encryptor.decrypt_file(key, path)
        os.remove(path)

        if old_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + old_extension
            else:
                path = path + '.' + old_extension

        with open(path, 'wb') as file:
            file.write(decrypted_content)
