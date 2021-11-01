import random

SYMBOLS = ['!', '@', '#', '$', '*', '+', '-', '.', '_']
NUMBERS = ['2', '3', '4', '5', '6', '7', '8', '9']
UPPERCASE = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
             'X', 'Y', 'Z']
LOWERCASE = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
             'y', 'z']


# 0 ; o ; O ; 1 ; i ; I ; l not included
def generate_password(length, include_uppercase=True, include_numbers=True, include_symbols=True):
    chars = []
    chars.extend(LOWERCASE)
    if include_uppercase:
        chars.extend(UPPERCASE)
    if include_numbers:
        chars.extend(NUMBERS)
    if include_symbols:
        chars.extend(SYMBOLS)
    password = "".join([random.choice(chars) for i in range(length)])
    return password
