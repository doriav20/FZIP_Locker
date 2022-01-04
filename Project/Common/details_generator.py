import random

SYMBOLS = ['!', '@', '#', '$', '*', '+', '-', '.', '_']
NUMBERS = ['2', '3', '4', '5', '6', '7', '8', '9']
UPPERCASE = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
             'X', 'Y', 'Z']
LOWERCASE = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
             'y', 'z']
chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
         'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

ALL = ['!', '@', '#', '$', '*', '+', '-', '.', '_', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C',
       'D',
       'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
       'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
       'w', 'x', 'y', 'z']


# 0 ; o ; O ; 1 ; i ; I ; l not included

def generate_password(length: int, include_uppercase: bool = True, include_numbers: bool = True,
                      include_symbols: bool = True) -> str:
    _chars = []
    _chars.extend(LOWERCASE)
    if include_uppercase:
        _chars.extend(UPPERCASE)
    if include_numbers:
        _chars.extend(NUMBERS)
    if include_symbols:
        _chars.extend(SYMBOLS)
    password = ''.join(random.choices(population=_chars, k=length))
    return password


def valid_password(passowrd: str) -> bool:
    if not (6 <= len(passowrd) <= 32):
        return False
    for ch in passowrd:
        if ch not in ALL:
            return False
    return True


def generate_unique_id(length: int) -> str:
    unique_id = ''
    length += ((-length) % 4)  # padding
    for i in range(length):
        if i % 4 == 0:
            unique_id += '_'
        unique_id += random.choice(chars)
    return unique_id[1:]


def generate_unique_path(extension: str = '') -> str:
    if extension:
        return generate_unique_id(16) + '.' + extension
    else:
        return generate_unique_id(16)
