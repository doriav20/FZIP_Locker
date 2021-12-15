import smtplib
from email.mime.text import MIMEText
import re

USERNAME = 'fziplocker'
ADDRESS = 'fziplocker@gmail.com'
PASSWORD = ''

SUBJECT = "Welcome to FZIP Locker"
BODY = 'Hey {},\n' \
       'We are glad you joined FZIP Locker.\n' \
       'Now you can scan your face and start encrypting your files securely...'


def address_validation(receiver_address: str) -> bool:
    try:
        result = re.search(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', receiver_address)
        return result is not None
    except:
        return False


def create_mail(receiver_address: str) -> str:
    try:
        body = BODY.format(receiver_address[:receiver_address.index('@')])
        msg = MIMEText(body)
        msg['Subject'] = SUBJECT
        msg['From'] = ADDRESS
        msg['To'] = receiver_address
        msg = msg.as_string()
        return msg
    except:
        return None


def send_email(receiver_address: str) -> bool:
    if not address_validation(receiver_address):
        return False
    try:
        msg = create_mail(receiver_address)  # Create SMTP body
        if not msg:
            return False
        # Send through SMTP Gmail server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)  # Connect SMTP Server
        server.ehlo()
        server.login(USERNAME, PASSWORD)
        server.sendmail(ADDRESS, receiver_address, msg)
        server.close()
        return True
    except:
        return False
