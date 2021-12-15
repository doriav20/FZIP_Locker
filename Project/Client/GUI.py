import random
import ctypes

from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from enum import Enum

from Common.details_generator import generate_password as _generate_password

import resources

SCALE_FACTOR = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100


class EventType(Enum):
    Pressed = 1
    Released = 2


class ButtonType(Enum):
    SignIn = 1
    SignUp = 2
    Scan = 3
    Register = 4
    Generate_Password = 5
    Decompress = 6
    Compress = 7


GradientBlue = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,stop:0 rgba(10, 112, 164, 255), stop:0.3125 rgba(10, 112, 164, 255), stop:0.795455 rgba(33, 43, 255, 255), stop:1 rgba(33, 43, 255, 255));'
GradientInvertBlue = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(33, 43, 255, 255), stop:0.3125 rgba(33, 43, 255, 255), stop:0.795455 rgba(10, 112, 164, 255), stop:1 rgba(10, 112, 164, 255));'
GradientGreen = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(114, 171, 68, 255),stop:0.3125 rgba(114, 171, 68, 255), stop:0.795455 rgba(3, 97, 73, 255), stop:1 rgba(3, 97, 73, 255));'
GradientRed = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255),stop:0.0113636 rgba(184, 0, 3, 255), stop:1 rgba(255, 207, 140, 255));'
GradientInvertRed = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 207, 140, 255),stop:1 rgba(184, 0, 3, 255));'
GradientGray = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(137, 137, 137, 255), stop:0.698864 rgba(23, 23, 23, 255));'
GradientTransparentWhite = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(191, 191, 191, 150), stop:1 rgba(255, 255, 255, 150));'
GradientOlivePurple = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(116, 122, 66, 255), stop:1 rgba(170, 170, 255, 255));'


class LoginScreenClass:
    def __init__(self, LoginWindow):
        if not LoginWindow.objectName():
            LoginWindow.setObjectName('LoginWindow')
        LoginWindow.resize(960, 540)
        LoginWindow.setMinimumSize(QSize(960, 540))
        LoginWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(LoginWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 40, 960, 61))
        font = create_font('Gadugi', 38, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.zip_label_left = QLabel(self.central_widget)
        self.zip_label_left.setObjectName('zip_label_left')
        self.zip_label_left.setGeometry(QRect(-60, 10, 341, 521))
        self.zip_label_left.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_label_right = QLabel(self.central_widget)
        self.zip_label_right.setObjectName('zip_label_right')
        self.zip_label_right.setGeometry(QRect(660, 10, 341, 521))
        self.zip_label_right.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.emailLineEdit = QLineEdit(self.central_widget)
        self.emailLineEdit.setObjectName('emailLineEdit')
        self.emailLineEdit.setGeometry(QRect(270, 160, 426, 53))
        font = create_font('Gadugi', 15, True)
        self.emailLineEdit.setFont(font)
        self.emailLineEdit.setEchoMode(QLineEdit.Normal)
        self.emailLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.passwordLineEdit = QLineEdit(self.central_widget)
        self.passwordLineEdit.setObjectName('passwordLineEdit')
        self.passwordLineEdit.setGeometry(QRect(270, 240, 426, 53))
        font = create_font('Gadugi', 15, True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.passwordLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.signInButton = QPushButton(self.central_widget)
        self.signInButton.setObjectName('signInButton')
        self.signInButton.setGeometry(QRect(401, 340, 158, 40))
        font = create_font('Gadugi', 18, True)
        self.signInButton.setFont(font)
        self.signInButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.signInButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.signInButton, ButtonType.SignIn, EventType.Pressed))
        self.signInButton.released.connect(
            lambda: self.change_pressed_button_style(self.signInButton, ButtonType.SignIn, EventType.Released))
        self.signInButton.clicked.connect(self.sign_in_handler)
        self.signInButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.signUpButton = QPushButton(self.central_widget)
        self.signUpButton.setObjectName('signUpButton')
        self.signUpButton.setGeometry(QRect(280, 410, 400, 40))
        font = create_font('Gadugi', 18, True)
        self.signUpButton.setFont(font)
        self.signUpButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.signUpButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.signUpButton, ButtonType.SignUp, EventType.Pressed))
        self.signUpButton.released.connect(
            lambda: self.change_pressed_button_style(self.signUpButton, ButtonType.SignUp, EventType.Released))
        self.signUpButton.clicked.connect(self.sign_up_handler)
        self.signUpButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGreen +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.passwordShowButton = QPushButton(self.central_widget)
        self.passwordShowButton.setObjectName('passwordShowButton')
        self.passwordShowButton.setGeometry(QRect(662, 260, 27, 16))
        self.passwordShowButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordShowButton.clicked.connect(self.password_show_handler)
        self.passwordShowButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')

        self.red_x = QLabel(self.central_widget)
        self.red_x.setObjectName('red_x')
        self.red_x.setGeometry(QRect(245, 445, 41, 41))
        self.red_x.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/red_x/red_x.png);')
        self.red_x.hide()

        self.error_text = QLabel(self.central_widget)
        self.error_text.setObjectName('error_text')
        self.error_text.setGeometry(QRect(277, 445, 451, 41))
        font = create_font('Gadugi', 20, True)
        self.error_text.setFont(font)
        self.error_text.setAlignment(Qt.AlignCenter)
        self.error_text.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.error_text.hide()

        LoginWindow.setCentralWidget(self.central_widget)

        LoginWindow.setWindowTitle(QCoreApplication.translate('LoginWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('LoginWindow', 'FZIP Locker', None))
        self.emailLineEdit.setPlaceholderText(QCoreApplication.translate('LoginWindow', 'Email', None))
        self.passwordLineEdit.setPlaceholderText(QCoreApplication.translate('LoginWindow', 'Password', None))
        self.signInButton.setText(QCoreApplication.translate('LoginWindow', 'Sign in', None))
        self.signUpButton.setText(QCoreApplication.translate('LoginWindow', 'Don\'t have an account? Sign up', None))
        self.passwordShowButton.setText('')
        self.red_x.setText('')
        self.error_text.setText(QCoreApplication.translate('LoginWindow', 'Your login details was incorrect', None))

        QMetaObject.connectSlotsByName(LoginWindow)

    def change_pressed_button_style(self, button, button_type, event_type):
        if event_type == EventType.Pressed:
            button.setStyleSheet(
                'background-image: url();'
                'background-color: ' + GradientRed +
                'color: rgb(255, 255, 255);'
                'border-radius:10px;')
        else:
            if button_type == ButtonType.SignIn:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self):
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)
        else:
            self.passwordLineEdit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self):
        return self.passwordLineEdit.echoMode() == QLineEdit.Password

    def sign_in_handler(self):
        # TODO Remove fictive handler
        if self.is_error_message_displayed():
            self.remove_error_message()
        else:
            self.add_error_message()

    def sign_up_handler(self):
        # TODO Remove fictive handler
        self.sign_in_handler()

    def add_error_message(self):
        if self.is_error_message_displayed():
            return
        self.signInButton.setGeometry(QRect(401, 320, 158, 40))
        self.signUpButton.setGeometry(QRect(280, 380, 400, 40))
        self.red_x.show()
        self.error_text.show()

    def remove_error_message(self):
        if not self.is_error_message_displayed():
            return
        self.signInButton.setGeometry(QRect(401, 340, 158, 40))
        self.signUpButton.setGeometry(QRect(280, 410, 400, 40))
        self.red_x.hide()
        self.error_text.hide()

    def is_error_message_displayed(self):
        return self.red_x.isVisible()


class RegisterScreenClass:
    def __init__(self, RegisterWindow):
        if not RegisterWindow.objectName():
            RegisterWindow.setObjectName('RegisterWindow')
        RegisterWindow.resize(960, 540)
        RegisterWindow.setMinimumSize(QSize(960, 540))
        RegisterWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(RegisterWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 40, 960, 61))
        font = create_font('Gadugi', 38, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.zip_label_left = QLabel(self.central_widget)
        self.zip_label_left.setObjectName('zip_label_left')
        self.zip_label_left.setGeometry(QRect(-60, 10, 341, 521))
        self.zip_label_left.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_label_right = QLabel(self.central_widget)
        self.zip_label_right.setObjectName('zip_label_right')
        self.zip_label_right.setGeometry(QRect(660, 10, 341, 521))
        self.zip_label_right.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.emailLineEdit = QLineEdit(self.central_widget)
        self.emailLineEdit.setObjectName('emailLineEdit')
        self.emailLineEdit.setGeometry(QRect(270, 160, 426, 53))
        font = create_font('Gadugi', 15, True)
        self.emailLineEdit.setFont(font)
        self.emailLineEdit.setEchoMode(QLineEdit.Normal)
        self.emailLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.passwordLineEdit = QLineEdit(self.central_widget)
        self.passwordLineEdit.setObjectName('passwordLineEdit')
        self.passwordLineEdit.setGeometry(QRect(270, 240, 426, 53))
        font = create_font('Gadugi', 15, True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.passwordLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.scanButton = QPushButton(self.central_widget)
        self.scanButton.setObjectName('scanButton')
        self.scanButton.setGeometry(QRect(380, 340, 200, 40))
        font = create_font('Gadugi', 18, True)
        self.scanButton.setFont(font)
        self.scanButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.scanButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.scanButton, ButtonType.Scan, EventType.Pressed))
        self.scanButton.released.connect(
            lambda: self.change_pressed_button_style(self.scanButton, ButtonType.Scan, EventType.Released))
        self.scanButton.clicked.connect(self.scan_handler)
        self.scanButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGray +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.registerButton = QPushButton(self.central_widget)
        self.registerButton.setObjectName('registerButton')
        self.registerButton.setGeometry(QRect(380, 410, 200, 40))
        font = create_font('Gadugi', 18, True)
        self.registerButton.setFont(font)
        self.registerButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.registerButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.registerButton, ButtonType.Register, EventType.Pressed))
        self.registerButton.released.connect(
            lambda: self.change_pressed_button_style(self.registerButton, ButtonType.Register, EventType.Released))
        self.registerButton.clicked.connect(self.register_handler)
        self.registerButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGreen +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.passwordShowButton = QPushButton(self.central_widget)
        self.passwordShowButton.setObjectName('passwordShowButton')
        self.passwordShowButton.setGeometry(QRect(662, 260, 27, 16))
        self.passwordShowButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordShowButton.clicked.connect(self.password_show_handler)
        self.passwordShowButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')

        self.passwordGeneratorKey = QPushButton(self.central_widget)
        self.passwordGeneratorKey.setObjectName('passwordGeneratorKey')
        self.passwordGeneratorKey.setGeometry(QRect(636, 258, 21, 20))
        self.passwordGeneratorKey.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordGeneratorKey.clicked.connect(self.password_generator_handler)
        self.passwordGeneratorKey.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/password_generator_key/password_generator.png);')

        self.passwordGeneratorContainer = QWidget(self.central_widget)
        self.passwordGeneratorContainer.setObjectName('passwordGeneratorContainer')
        self.passwordGeneratorContainer.setGeometry(QRect(570, 280, 180, 130))
        self.passwordGeneratorContainer.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientTransparentWhite +
            'border-radius: 10px')
        self.passwordGeneratorContainer.hide()

        self.passwordLengthLabel = QLabel(self.passwordGeneratorContainer)
        self.passwordLengthLabel.setObjectName('passwordLengthLabel')
        self.passwordLengthLabel.setGeometry(QRect(10, 5, 95, 17))
        font = create_font('Gadugi', 8, True)
        self.passwordLengthLabel.setFont(font)
        self.passwordLengthLabel.setStyleSheet('background-color: rgb();')

        self.passwordLengthLineEdit = QLineEdit(self.passwordGeneratorContainer)
        self.passwordLengthLineEdit.setObjectName('passwordLengthLineEdit')
        self.passwordLengthLineEdit.setGeometry(QRect(102, 4, 25, 20))
        font = create_font('Gadugi', 8, True)
        self.passwordLengthLineEdit.setFont(font)
        self.passwordLengthLineEdit.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.passwordLengthLineEdit.setStyleSheet(
            'border-style: solid;'
            'border-width: 2px;'
            'border-color: rgb(0, 0, 0);')
        validator = QIntValidator(1, 99)
        self.passwordLengthLineEdit.setValidator(validator)

        self.lowerCaseCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.lowerCaseCheckBox.setObjectName('lowerCaseCheckBox')
        self.lowerCaseCheckBox.setEnabled(False)
        self.lowerCaseCheckBox.setGeometry(QRect(10, 25, 131, 17))
        font = create_font('Gadugi', 8, True)
        self.lowerCaseCheckBox.setFont(font)
        self.lowerCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.lowerCaseCheckBox.setChecked(True)

        self.upperCaseCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.upperCaseCheckBox.setObjectName('upperCaseCheckBox')
        self.upperCaseCheckBox.setEnabled(True)
        self.upperCaseCheckBox.setGeometry(QRect(10, 45, 131, 17))
        font = create_font('Gadugi', 8, True)
        self.upperCaseCheckBox.setFont(font)
        self.upperCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.upperCaseCheckBox.setChecked(False)

        self.numbersCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.numbersCheckBox.setObjectName('numbersCheckBox')
        self.numbersCheckBox.setEnabled(True)
        self.numbersCheckBox.setGeometry(QRect(10, 65, 131, 17))
        font = create_font('Gadugi', 8, True)
        self.numbersCheckBox.setFont(font)
        self.numbersCheckBox.setStyleSheet('background-color: rgb();')
        self.numbersCheckBox.setChecked(False)

        self.symbolsCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.symbolsCheckBox.setObjectName('symbolsCheckBox')
        self.symbolsCheckBox.setEnabled(True)
        self.symbolsCheckBox.setGeometry(QRect(10, 85, 131, 17))
        font = create_font('Gadugi', 8, True)
        self.symbolsCheckBox.setFont(font)
        self.symbolsCheckBox.setStyleSheet('background-color: rgb();')
        self.symbolsCheckBox.setChecked(False)

        self.generatePasswordButton = QPushButton(self.passwordGeneratorContainer)
        self.generatePasswordButton.setObjectName('generatePasswordButton')
        self.generatePasswordButton.setGeometry(QRect(35, 105, 110, 20))
        font = create_font('Gadugi', 8, True)
        self.generatePasswordButton.setFont(font)
        self.generatePasswordButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.generatePasswordButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.generatePasswordButton, ButtonType.Generate_Password,
                                                     EventType.Pressed))
        self.generatePasswordButton.released.connect(
            lambda: self.change_pressed_button_style(self.generatePasswordButton, ButtonType.Generate_Password,
                                                     EventType.Released))
        self.generatePasswordButton.clicked.connect(self.generate_password)
        self.generatePasswordButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientOlivePurple +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.green_v = QLabel(self.central_widget)
        self.green_v.setObjectName('green_v')
        self.green_v.setGeometry(QRect(195, 403, 45, 45))
        self.green_v.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/green_v/green_v.png);')
        self.green_v.hide()

        self.scan_success_text = QLabel(self.central_widget)
        self.scan_success_text.setObjectName('scan_success_text')
        self.scan_success_text.setGeometry(QRect(230, 400, 551, 41))
        font = create_font('Gadugi', 20, True)
        self.scan_success_text.setFont(font)
        self.scan_success_text.setAlignment(Qt.AlignCenter)
        self.scan_success_text.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.scan_success_text.hide()

        self.red_x = QLabel(self.central_widget)
        self.red_x.setObjectName('red_x')
        self.red_x.setGeometry(QRect(140, 398, 45, 45))
        self.red_x.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/red_x/red_x.png);')
        self.red_x.hide()

        self.scan_error_text = QLabel(self.central_widget)
        self.scan_error_text.setObjectName('scan_error_text')
        self.scan_error_text.setGeometry(QRect(180, 400, 631, 41))
        font = create_font('Gadugi', 17, True)
        self.scan_error_text.setFont(font)
        self.scan_error_text.setAlignment(Qt.AlignCenter)
        self.scan_error_text.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.scan_error_text.hide()

        self.register_error_text = QLabel(self.central_widget)
        self.register_error_text.setObjectName('register_error_text')
        self.register_error_text.setGeometry(QRect(182, 460, 631, 41))
        font = create_font('Gadugi', 18, True)
        self.register_error_text.setFont(font)
        self.register_error_text.setAlignment(Qt.AlignCenter)
        self.register_error_text.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.register_error_text.hide()

        RegisterWindow.setCentralWidget(self.central_widget)

        RegisterWindow.setWindowTitle(QCoreApplication.translate('RegisterWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('RegisterWindow', 'FZIP Locker', None))
        self.emailLineEdit.setPlaceholderText(QCoreApplication.translate('RegisterWindow', 'Email', None))
        self.passwordLineEdit.setPlaceholderText(QCoreApplication.translate('RegisterWindow', 'Password', None))
        self.scanButton.setText(QCoreApplication.translate('RegisterWindow', 'Scan My Face', None))
        self.registerButton.setText(QCoreApplication.translate('RegisterWindow', 'Register', None))
        self.passwordLengthLabel.setText(QCoreApplication.translate('RegisterWindow', 'Password Length', None))
        self.lowerCaseCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Lower case included', None))
        self.upperCaseCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Upper case included', None))
        self.numbersCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Numbers included', None))
        self.symbolsCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Symbols included', None))
        self.generatePasswordButton.setText(QCoreApplication.translate('RegisterWindow', 'Generate Password', None))
        self.scan_success_text.setText(QCoreApplication.translate(
            'RegisterWindow', 'Your Face has been Scanned Successfully', None))
        self.scan_error_text.setText(QCoreApplication.translate(
            'RegisterWindow', 'Your Face has not been Scanned Successfully, Try Again!', None))
        self.register_error_text.setText(QCoreApplication.translate(
            'RegisterWindow', 'This email is already in use by another account', None))

        QMetaObject.connectSlotsByName(RegisterWindow)

    def change_pressed_button_style(self, button, button_type, event_type):
        if event_type == EventType.Pressed:
            button.setStyleSheet(
                'background-image: url();'
                'background-color: ' + GradientRed +
                'color: rgb(255, 255, 255);'
                'border-radius:10px;')
        else:
            if button_type == ButtonType.Scan:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGray +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            elif button_type == ButtonType.Register:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientOlivePurple +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self):
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)
        else:
            self.passwordLineEdit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self):
        return self.passwordLineEdit.echoMode() == QLineEdit.Password

    def password_generator_handler(self):
        if self.passwordGeneratorContainer.isVisible():
            self.passwordGeneratorContainer.hide()
        else:
            self.passwordGeneratorContainer.show()

    def generate_password(self):
        if not self.passwordLengthLineEdit.text():
            self.passwordLengthLineEdit.setText('6')

        include_uppercase = self.upperCaseCheckBox.isChecked()
        include_numbers = self.numbersCheckBox.isChecked()
        include_symbols = self.symbolsCheckBox.isChecked()
        length = int(self.passwordLengthLineEdit.text())
        if length < 6:
            length = 6
        elif length > 32:
            length = 32
        self.passwordLengthLineEdit.setText(str(length))
        self.passwordLineEdit.setText(_generate_password(length, include_uppercase, include_numbers, include_symbols))
        self.passwordGeneratorContainer.hide()
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)

    def scan_handler(self):
        # TODO Remove fictive handler
        n = random.choice([0, 1, 2, 3])
        if n == 0:
            self.clear_messages()
        elif n == 1:
            self.add_scan_confirm()
        elif n == 2:
            self.add_scan_error()
        else:
            self.add_register_error()

    def register_handler(self):
        # TODO Remove fictive handler
        self.scan_handler()

    def clear_messages(self):
        changed = True
        if self.is_scan_confirm_displayed():
            self.green_v.hide()
            self.scan_success_text.hide()
        elif self.is_scan_error_displayed():
            self.red_x.hide()
            self.scan_error_text.hide()
        elif self.is_register_error_displayed():
            self.red_x.hide()
            self.register_error_text.hide()
        else:
            changed = False
        if changed:
            self.scanButton.setGeometry(QRect(380, 340, 200, 40))
            self.registerButton.setGeometry(QRect(380, 410, 200, 40))

    def add_scan_confirm(self):
        self.clear_messages()
        self.scanButton.setGeometry(QRect(380, 340, 200, 40))
        self.registerButton.setGeometry(QRect(380, 460, 200, 40))
        self.green_v.show()
        self.scan_success_text.show()

    def add_scan_error(self):
        self.clear_messages()
        self.scanButton.setGeometry(QRect(380, 340, 200, 40))
        self.registerButton.setGeometry(QRect(380, 460, 200, 40))
        self.red_x.setGeometry(QRect(140, 398, 45, 45))
        self.red_x.show()
        self.scan_error_text.show()

    def add_register_error(self):
        self.clear_messages()
        self.scanButton.setGeometry(QRect(380, 340, 200, 40))
        self.registerButton.setGeometry(QRect(380, 400, 200, 40))
        self.red_x.setGeometry(QRect(179, 459, 43, 43))
        self.red_x.show()
        self.register_error_text.show()

    def is_scan_confirm_displayed(self):
        return self.scan_success_text.isVisible()

    def is_scan_error_displayed(self):
        return self.scan_error_text.isVisible()

    def is_register_error_displayed(self):
        return self.register_error_text.isVisible()


class CompressScreenClass:
    def __init__(self, CompressWindow):
        if not CompressWindow.objectName():
            CompressWindow.setObjectName('CompressWindow')
        CompressWindow.resize(960, 540)
        CompressWindow.setMinimumSize(QSize(960, 540))
        CompressWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(CompressWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_white_background.jpg);'
            'background-position: center;')

        self.decompressButton = QPushButton(self.central_widget)
        self.decompressButton.setObjectName('decompressButton')
        self.decompressButton.setGeometry(QRect(95, 140, 290, 80))
        font = create_font('Gadugi', 18, True)
        self.decompressButton.setFont(font)
        self.decompressButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.decompressButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.decompressButton, ButtonType.Decompress, EventType.Pressed))
        self.decompressButton.released.connect(
            lambda: self.change_pressed_button_style(self.decompressButton, ButtonType.Decompress, EventType.Released))
        self.decompressButton.clicked.connect(self.decompress_handler)
        self.decompressButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientInvertBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.compressButton = QPushButton(self.central_widget)
        self.compressButton.setObjectName('decompressButton')
        self.compressButton.setGeometry(QRect(575, 140, 290, 80))
        font = create_font('Gadugi', 18, True)
        self.compressButton.setFont(font)
        self.compressButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.compressButton.pressed.connect(
            lambda: self.change_pressed_button_style(self.compressButton, ButtonType.Compress, EventType.Pressed))
        self.compressButton.released.connect(
            lambda: self.change_pressed_button_style(self.compressButton, ButtonType.Compress, EventType.Released))
        self.compressButton.clicked.connect(self.compress_handler)
        self.compressButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.unlockLabel = QLabel(self.central_widget)
        self.unlockLabel.setObjectName('unlock')
        self.unlockLabel.setGeometry(QRect(142, 250, 196, 210))
        self.unlockLabel.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/locks/unlock.png);')
        self.lockLabel = QLabel(self.central_widget)
        self.lockLabel.setObjectName('lock')
        self.lockLabel.setGeometry(QRect(652, 250, 136, 210))
        self.lockLabel.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/locks/lock.png);')

        CompressWindow.setCentralWidget(self.central_widget)

        CompressWindow.setWindowTitle(QCoreApplication.translate('CompressWindow', 'FZIP Locker', None))
        self.decompressButton.setText(QCoreApplication.translate('CompressWindow', 'Decompress', None))
        self.compressButton.setText(QCoreApplication.translate('CompressWindow', 'Compress', None))

        QMetaObject.connectSlotsByName(CompressWindow)

    def change_pressed_button_style(self, button, button_type, event_type):
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Decompress:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
        else:
            if button_type == ButtonType.Decompress:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def decompress_handler(self):
        pass

    def compress_handler(self):
        pass


def create_font(font_name, size, bold):
    font = QFont()
    font.setFamily(font_name)

    size /= SCALE_FACTOR
    size = round(size)
    font.setPointSize(size)

    font.setBold(bold)
    font.setKerning(True)
    # font.setWeight(75)
    return font


def run_window(window):
    app = QtWidgets.QApplication([])
    MainWindow = QtWidgets.QMainWindow()
    ui = window(MainWindow)
    MainWindow.show()
    app.exec_()


if __name__ == '__main__':
    # pass
    # run_window(LoginScreenClass)
    run_window(RegisterScreenClass)
    # run_window(CompressScreenClass)
