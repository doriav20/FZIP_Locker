import smtplib
from email.mime.text import MIMEText


def create_mail(sender_address, receiver_address, body, subject):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_address
    msg['To'] = receiver_address
    msg = msg.as_string()
    return msg


def send_email(sender_login_info, receiver_address, subject, body):
    sender_address = sender_login_info[0]
    sender_password = sender_login_info[1]
    msg = create_mail(sender_address, receiver_address, body, subject)  # Create SMTP body

    # Send through SMTP Gmail server
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)  # Connect SMTP Server
    server.ehlo()
    server.login(sender_address, sender_password)
    server.sendmail(sender_address, receiver_address, msg)
    server.close()
