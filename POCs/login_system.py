from password_generator import generate_password
from email_sender import send_email

# email_address = input('Enter your email address: ')
# generate_pass = input('Do you want to generate password? Y/N').lower() == 'y'

email_address = "***User's Email Here***"
generate_pass = False

if generate_pass:
    length = 8
    password = generate_password(length, include_uppercase=False, include_numbers=True, include_symbols=False)
else:
    password = input('Choose password: ')

print(f'Login info:\n\tEmail: {email_address}\n\tPassword: {password}')

SUBJECT = 'We are glad you have joined us - FZIP Locker'
BODY = 'Hey dear, your login details are:\n\tUsername\Email: {0}\n\tPassword: {1}\nHope you will enjoy...\nFZIP Locker'
send_email(
    ["***Mail Domain's Username***", "***Mail Domain's Password***"], email_address, SUBJECT, BODY.format(email_address, password))
