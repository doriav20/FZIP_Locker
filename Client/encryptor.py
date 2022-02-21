from typing import Union, Tuple

from Crypto import Random
from Crypto.Cipher import AES


class Encryptor:
    __SEPERATOR = b'|'  # Seperator between prefix & content

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

    def __encrypt(self, bytes_content: bytes, prefix: bytes) -> bytes:
        message = Encryptor.__pad(prefix + Encryptor.__SEPERATOR + bytes_content)
        iv = Random.get_random_bytes(AES.block_size)  # Initialization Vector
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)  # Block Chiper Mode of Operation - Output Feedback (OFB)
        return iv + cipher.encrypt(message)

    def encrypt_text(self, text: str, prefix: str = '') -> bytes:
        binary_prefix = prefix.encode()
        return self.__encrypt(text.encode(), binary_prefix)

    def encrypt_file(self, path: str, prefix: str = '') -> bytes:
        with open(path, 'rb') as file:
            file_content = file.read()
        binary_prefix = prefix.encode()
        return self.__encrypt(file_content, binary_prefix)

    def encrypt_and_save_file(self, path: str, new_extension: str = '', prefix: str = '') -> str:
        encrypted_content = self.encrypt_file(path, prefix)

        if new_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + new_extension
            else:
                path = path + '.' + new_extension

        with open(path, 'wb') as file:
            file.write(encrypted_content)

        return path

    def __decrypt(self, encrypted_bytes_content: bytes) -> Tuple[bytes, bytes]:
        iv = encrypted_bytes_content[:AES.block_size]
        cipher = AES.new(self.__key, AES.MODE_OFB, iv)
        plaintext = cipher.decrypt(encrypted_bytes_content[AES.block_size:])
        plaintext = plaintext.rstrip(b'\0')[:-1]
        seperator_index = plaintext.find(Encryptor.__SEPERATOR)
        content, prefix = plaintext[seperator_index + 1:], plaintext[:seperator_index]
        return content, prefix

    def decrypt_text(self, encrypted_text: bytes, decode=True) -> Union[Tuple[str, str], Tuple[bytes, str]]:
        content, prefix = self.__decrypt(encrypted_text)
        if decode:
            return content.decode(), prefix.decode()
        else:
            return content, prefix.decode()

    def decrypt_file(self, path: str) -> Tuple[bytes, bytes]:
        with open(path, 'rb') as file:
            file_encrypted_content = file.read()

        return self.__decrypt(file_encrypted_content)

    def decrypt_and_save_file(self, path: str, old_extension: str = '') -> Tuple[str, str]:
        file_content, prefix = self.decrypt_file(path)

        if old_extension:
            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                path = path[:index] + '.' + old_extension
            else:
                path = path + '.' + old_extension

        with open(path, 'wb') as file:
            file.write(file_content)
        return path, prefix.decode()
