import smtplib
from email.message import EmailMessage

USERNAME = 'faceziplocker'
ADDRESS = 'faceziplocker@gmail.com'
PASSWORD = ''

SUBJECT = "Welcome to FZIP Locker"
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <style>
        table {
            max-width: 420px;
            width: 100%;
            border: 0;
            border-spacing: 0;
            border-collapse: collapse;
            margin: 0 auto;
            text-align: center;
            direction: ltr;
            color: rgb(0, 0, 0);
            background-color: rgb(245, 245, 220);
        }

        h1 {
            margin-top: 0;
            font-family: Bahnschrift SemiBold, Gadugi, sans-serif;
            font-size: xxx-large;
            font-style: normal;
            background-color: rgba(95, 158, 160, 0.5);
        }

        em {
            margin-top: 10px;
            display: inline-block;
            font-family: Bahnschrift SemiBold, Gadugi, sans-serif;
            font-size: x-large;
            font-style: normal;
            background-color: rgba(0, 255, 255, 0.2);
        }

        img {
            margin-top: 15px;
            width: 60%;
        }
    </style>
</head>
<body>
<table>
    <tr>
        <td>
            <h1>
                Hey {username}
            </h1>
            <em>
                We are glad you joined FZIP Locker
                <br>
                Now you can scan your face and start encrypting your files securely...
            </em>
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Wikimedia-logo.png" alt="Logo" title="Logo">
        </td>
    </tr>
</table>
</body>
</html>
'''


def create_mail(receiver_address: str) -> str:
    try:
        msg = EmailMessage()
        msg['Subject'] = SUBJECT
        msg['From'] = ADDRESS
        msg['To'] = receiver_address
        username = receiver_address[:receiver_address.index('@')]
        msg.set_content(HTML.replace('{username}', username), subtype='html')
        msg = msg.as_string()
        return msg
    except:
        return None


def send_email(receiver_address: str) -> bool:
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
