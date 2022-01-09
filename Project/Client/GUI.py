import ctypes
from abc import ABC as AbstractBaseClass, abstractmethod
from types import FunctionType

from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import numpy as np

from enum import Enum

from Client.face_detector import detect_face
from Common.details_generator import generate_password as _generate_password, is_valid_password, is_valid_email

import client_external_handlers as external

import resources
from Common.operation_result import OperationResultType

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
    NO = 8
    YES = 9
    Submit = 10


class Icon(Enum):
    Green_V = 0
    Red_X = 1


GradientBlue = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,stop:0 rgba(10, 112, 164, 255), stop:0.3125 rgba(10, 112, 164, 255), stop:0.795455 rgba(33, 43, 255, 255), stop:1 rgba(33, 43, 255, 255));'
GradientInvertBlue = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(33, 43, 255, 255), stop:0.3125 rgba(33, 43, 255, 255), stop:0.795455 rgba(10, 112, 164, 255), stop:1 rgba(10, 112, 164, 255));'
GradientGreen = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(114, 171, 68, 255),stop:0.3125 rgba(114, 171, 68, 255), stop:0.795455 rgba(3, 97, 73, 255), stop:1 rgba(3, 97, 73, 255));'
GradientRed = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255),stop:0.0113636 rgba(184, 0, 3, 255), stop:1 rgba(255, 207, 140, 255));'
GradientGray = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(137, 137, 137, 255), stop:0.698864 rgba(23, 23, 23, 255));'
GradientTransparentWhite = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(191, 191, 191, 150), stop:1 rgba(255, 255, 255, 150));'
GradientOlivePurple = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(116, 122, 66, 255), stop:1 rgba(170, 170, 255, 255));'
GradientDarkRed = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0.295455 rgba(170, 0, 0, 255), stop:1 rgba(255, 0, 0, 255));'
GradientDarkGreen = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0.295455 rgba(0, 85, 0, 255), stop:1 rgba(0, 154, 0, 255));'
GradientBrightRed = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0.295455 rgba(129, 68, 68, 255), stop:1 rgba(255, 158, 158, 255));'
GradientBrightGreen = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0.295455 rgba(58, 99, 58, 255), stop:1 rgba(144, 154, 144, 255));'
GradientBlueReducedOpacity = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,stop:0 rgba(10, 112, 164, 100), stop:0.3125 rgba(10, 112, 164, 100), stop:0.795455 rgba(33, 43, 255, 100), stop:1 rgba(33, 43, 255, 100));'
GradientInvertBlueReducedOpacity = 'qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(33, 43, 255, 100), stop:0.3125 rgba(33, 43, 255, 100), stop:0.795455 rgba(10, 112, 164, 100), stop:1 rgba(10, 112, 164, 100));'

shared_Register_FaceScanning_image_valid = False  # Shared with Register & Face Scanning Screens
shared_Compress_Password_zip_pwd = ''  # Shared with Compress & Password Screens
shared_Compress_FaceScanning_image_valid = False  # Shared with Compress & Face Scanning Screens


class GUIScreenClass(AbstractBaseClass):
    def __init__(self, Window: QMainWindow, callback_func: FunctionType) -> None:
        self.this_window = Window
        self.callback_func = callback_func

    def open_other_window(self, other_window_type: type, close_current: bool, callback_func=None, **kwargs) -> None:
        self.other_window = QMainWindow()
        if other_window_type == FaceScanningScreenClass:
            roi_preview = kwargs['roi_preview']
            scan_number = kwargs['scan_number']
            other_window_type(self.other_window, callback_func, roi_preview, scan_number)
        elif other_window_type == PasswordScreenClass:
            include_pwd_generator = kwargs['include_pwd_generator']
            other_window_type(self.other_window, callback_func, include_pwd_generator)
        else:
            other_window_type(self.other_window, callback_func)
        self.other_window.show()
        if close_current:
            self.this_window.close()

    @abstractmethod
    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        raise NotImplementedError("change_pressed_button_style is an Abstract Method")
        # return None

    @staticmethod
    def create_font(font_name: str, size: int, bold: bool) -> QFont:
        font = QFont()
        font.setFamily(font_name)

        size = round(size / SCALE_FACTOR)
        font.setPointSize(size)

        font.setBold(bold)
        font.setKerning(True)
        # font.setWeight(75)
        return font


class LoginScreenClass(GUIScreenClass):
    def __init__(self, LoginWindow: QMainWindow, callback_func: FunctionType) -> None:
        super().__init__(LoginWindow, callback_func)
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
        font = LoginScreenClass.create_font('Gadugi', 38, True)
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
        font = LoginScreenClass.create_font('Gadugi', 15, True)
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
        font = LoginScreenClass.create_font('Gadugi', 15, True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.passwordLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.passwordShowButton = QPushButton(self.central_widget)
        self.passwordShowButton.setObjectName('passwordShowButton')
        self.passwordShowButton.setGeometry(QRect(662, 260, 27, 16))
        self.passwordShowButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordShowButton.clicked.connect(self.password_show_handler)
        self.passwordShowButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')

        self.signInButton = QPushButton(self.central_widget)
        self.signInButton.setObjectName('signInButton')
        self.signInButton.setGeometry(QRect(401, 340, 158, 40))
        font = LoginScreenClass.create_font('Gadugi', 18, True)
        self.signInButton.setFont(font)
        self.signInButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.signInButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignIn, EventType.Pressed))
        self.signInButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignIn, EventType.Released))
        self.signInButton.clicked.connect(self.sign_in_handler)
        self.signInButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.signUpButton = QPushButton(self.central_widget)
        self.signUpButton.setObjectName('signUpButton')
        self.signUpButton.setGeometry(QRect(280, 410, 400, 40))
        font = LoginScreenClass.create_font('Gadugi', 18, True)
        self.signUpButton.setFont(font)
        self.signUpButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.signUpButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Pressed))
        self.signUpButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Released))
        self.signUpButton.clicked.connect(self.sign_up_handler)
        self.signUpButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGreen +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.red_x_label = QLabel(self.central_widget)
        self.red_x_label.setObjectName('red_x_label')
        self.red_x_label.setGeometry(QRect(460, 480, 40, 40))
        self.red_x_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/red_x/red_x.png);')
        self.red_x_label.hide()

        self.message_label = QLabel(self.central_widget)
        self.message_label.setObjectName('message_label')
        self.message_label.setGeometry(QRect(0, 440, 960, 40))
        font = RegisterScreenClass.create_font('Gadugi', 18, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        LoginWindow.setCentralWidget(self.central_widget)

        LoginWindow.setWindowTitle(QCoreApplication.translate('LoginWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('LoginWindow', 'FZIP Locker', None))
        self.emailLineEdit.setPlaceholderText(QCoreApplication.translate('LoginWindow', 'Email', None))
        self.passwordLineEdit.setPlaceholderText(QCoreApplication.translate('LoginWindow', 'Password', None))
        self.signInButton.setText(QCoreApplication.translate('LoginWindow', 'Sign in', None))
        self.signUpButton.setText(QCoreApplication.translate('LoginWindow', 'Don\'t have an account? Sign up', None))
        self.message_label.setText(QCoreApplication.translate('LoginWindow', '', None))

        QMetaObject.connectSlotsByName(LoginWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.SignIn:
                self.signInButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.signUpButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.SignIn:
                self.signInButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.signUpButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)
        else:
            self.passwordLineEdit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.passwordLineEdit.echoMode() == QLineEdit.Password

    def sign_in_handler(self) -> None:
        email = self.emailLineEdit.text()
        password = self.passwordLineEdit.text()
        if not is_valid_email(email):
            self.remove_message()
            self.change_message('Email Bad Format')
            self.add_message(Icon.Red_X)
            return
        if not is_valid_password(password):
            self.remove_message()
            self.change_message('Password Have to Include 6-32 Characters')
            self.add_message(Icon.Red_X)
            return
        operation_result = external.ext_sign_in_handler(email, password)
        if operation_result == OperationResultType.SUCCEEDED:
            self.remove_message()
            self.open_other_window(CompressScreenClass, close_current=True)
        elif operation_result == OperationResultType.DETAILS_ERROR:
            self.passwordLineEdit.setText('')
            self.change_message('User Does Not Exist / Wrong Password')
            self.add_message(Icon.Red_X)
        elif operation_result == OperationResultType.CONNECTION_ERROR:
            self.passwordLineEdit.setText('')
            self.remove_message()
            self.change_message('Connection Error')
            self.add_message(Icon.Red_X)
        else:
            self.passwordLineEdit.setText('')
            self.remove_message()
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)

    def sign_up_handler(self) -> None:
        self.open_other_window(RegisterScreenClass, close_current=True)

    def add_message(self, icon_type: Icon) -> None:
        self.buttons_arrangement_with_message()
        if icon_type == Icon.Red_X:
            self.red_x_label.show()
        self.message_label.show()

    def buttons_arrangement_with_message(self):
        self.signInButton.setGeometry(QRect(401, 320, 158, 40))
        self.signUpButton.setGeometry(QRect(280, 390, 400, 40))

    def buttons_arrangement_without_message(self):
        self.signInButton.setGeometry(QRect(401, 340, 158, 40))
        self.signUpButton.setGeometry(QRect(280, 410, 400, 40))

    def change_message(self, new_error_msg: str):
        self.message_label.setText(new_error_msg)

    def remove_message(self) -> None:
        self.buttons_arrangement_without_message()
        self.red_x_label.hide()
        self.message_label.hide()


class RegisterScreenClass(GUIScreenClass):
    def __init__(self, RegisterWindow: QMainWindow, callback_func: FunctionType) -> None:
        super().__init__(RegisterWindow, callback_func)
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
        font = RegisterScreenClass.create_font('Gadugi', 38, True)
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

        self.back_sign_in_button = QPushButton(self.central_widget)
        self.back_sign_in_button.setObjectName('back_sign_in_button')
        self.back_sign_in_button.setGeometry(QRect(10, 10, 37, 24))
        self.back_sign_in_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.back_sign_in_button.clicked.connect(self.back_sign_in_handler)
        self.back_sign_in_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/backs/back_arrow.png);')

        self.emailLineEdit = QLineEdit(self.central_widget)
        self.emailLineEdit.setObjectName('emailLineEdit')
        self.emailLineEdit.setGeometry(QRect(270, 160, 426, 53))
        font = RegisterScreenClass.create_font('Gadugi', 15, True)
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
        font = RegisterScreenClass.create_font('Gadugi', 15, True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.passwordLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.scanButton = QPushButton(self.central_widget)
        self.scanButton.setObjectName('scanButton')
        self.scanButton.setGeometry(QRect(230, 340, 500, 40))
        font = RegisterScreenClass.create_font('Gadugi', 18, True)
        self.scanButton.setFont(font)
        self.scanButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.scanButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Scan, EventType.Pressed))
        self.scanButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Scan, EventType.Released))
        self.scanButton.clicked.connect(self.scan_handler)
        self.scanButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGray +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')
        self.scanButtonClickBlock = False
        self.scan_number = 0

        self.registerButton = QPushButton(self.central_widget)
        self.registerButton.setObjectName('registerButton')
        self.registerButton.setGeometry(QRect(380, 410, 200, 40))
        font = RegisterScreenClass.create_font('Gadugi', 18, True)
        self.registerButton.setFont(font)
        self.registerButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.registerButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Register, EventType.Pressed))
        self.registerButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Register, EventType.Released))
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
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.passwordLengthLabel.setFont(font)
        self.passwordLengthLabel.setStyleSheet('background-color: rgb();')

        self.passwordLengthLineEdit = QLineEdit(self.passwordGeneratorContainer)
        self.passwordLengthLineEdit.setObjectName('passwordLengthLineEdit')
        self.passwordLengthLineEdit.setGeometry(QRect(102, 4, 25, 20))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
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
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.lowerCaseCheckBox.setFont(font)
        self.lowerCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.lowerCaseCheckBox.setChecked(True)

        self.upperCaseCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.upperCaseCheckBox.setObjectName('upperCaseCheckBox')
        self.upperCaseCheckBox.setEnabled(True)
        self.upperCaseCheckBox.setGeometry(QRect(10, 45, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.upperCaseCheckBox.setFont(font)
        self.upperCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.upperCaseCheckBox.setChecked(False)

        self.numbersCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.numbersCheckBox.setObjectName('numbersCheckBox')
        self.numbersCheckBox.setEnabled(True)
        self.numbersCheckBox.setGeometry(QRect(10, 65, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.numbersCheckBox.setFont(font)
        self.numbersCheckBox.setStyleSheet('background-color: rgb();')
        self.numbersCheckBox.setChecked(False)

        self.symbolsCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.symbolsCheckBox.setObjectName('symbolsCheckBox')
        self.symbolsCheckBox.setEnabled(True)
        self.symbolsCheckBox.setGeometry(QRect(10, 85, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.symbolsCheckBox.setFont(font)
        self.symbolsCheckBox.setStyleSheet('background-color: rgb();')
        self.symbolsCheckBox.setChecked(False)

        self.generatePasswordButton = QPushButton(self.passwordGeneratorContainer)
        self.generatePasswordButton.setObjectName('generatePasswordButton')
        self.generatePasswordButton.setGeometry(QRect(35, 105, 110, 20))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.generatePasswordButton.setFont(font)
        self.generatePasswordButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.generatePasswordButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Pressed))
        self.generatePasswordButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Released))
        self.generatePasswordButton.clicked.connect(self.generate_password)
        self.generatePasswordButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientOlivePurple +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.green_v_label = QLabel(self.central_widget)
        self.green_v_label.setObjectName('green_v_label')
        self.green_v_label.setGeometry(QRect(460, 480, 40, 40))
        self.green_v_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/green_v/green_v.png);')
        self.green_v_label.hide()

        self.red_x_label = QLabel(self.central_widget)
        self.red_x_label.setObjectName('red_x_label')
        self.red_x_label.setGeometry(QRect(460, 480, 40, 40))
        self.red_x_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/red_x/red_x.png);')
        self.red_x_label.hide()

        self.message_label = QLabel(self.central_widget)
        self.message_label.setObjectName('message_label')
        self.message_label.setGeometry(QRect(0, 440, 960, 40))
        font = RegisterScreenClass.create_font('Gadugi', 18, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        RegisterWindow.setCentralWidget(self.central_widget)

        RegisterWindow.setWindowTitle(QCoreApplication.translate('RegisterWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('RegisterWindow', 'FZIP Locker', None))
        self.emailLineEdit.setPlaceholderText(QCoreApplication.translate('RegisterWindow', 'Email', None))
        self.passwordLineEdit.setPlaceholderText(QCoreApplication.translate('RegisterWindow', 'Password', None))
        self.scanButton.setText(QCoreApplication.translate(
            'RegisterWindow', 'Scan My Face (3 Times): 3 Remaining', None))
        self.registerButton.setText(QCoreApplication.translate('RegisterWindow', 'Register', None))
        self.passwordLengthLabel.setText(QCoreApplication.translate('RegisterWindow', 'Password Length', None))
        self.lowerCaseCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Lower case included', None))
        self.upperCaseCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Upper case included', None))
        self.numbersCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Numbers included', None))
        self.symbolsCheckBox.setText(QCoreApplication.translate('RegisterWindow', 'Symbols included', None))
        self.generatePasswordButton.setText(QCoreApplication.translate('RegisterWindow', 'Generate Password', None))
        self.message_label.setText(QCoreApplication.translate('RegisterWindow', '', None))

        self.successful_scans = ()

        QMetaObject.connectSlotsByName(RegisterWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Scan:
                self.scanButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            elif button_type == ButtonType.Register:
                self.registerButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.generatePasswordButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.Scan:
                self.scanButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGray +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            elif button_type == ButtonType.Register:
                self.registerButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.generatePasswordButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientOlivePurple +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)
        else:
            self.passwordLineEdit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.passwordLineEdit.echoMode() == QLineEdit.Password

    def password_generator_handler(self) -> None:
        if self.passwordGeneratorContainer.isVisible():
            self.passwordGeneratorContainer.hide()
        else:
            self.passwordGeneratorContainer.show()

    def generate_password(self) -> None:
        if not self.passwordLengthLineEdit.text():
            self.passwordLengthLineEdit.setText('6')

        include_uppercase = self.upperCaseCheckBox.isChecked()
        include_numbers = self.numbersCheckBox.isChecked()
        include_symbols = self.symbolsCheckBox.isChecked()
        length = int(self.passwordLengthLineEdit.text())
        if length < 6:
            length = 6
            self.passwordLengthLineEdit.setText('6')
        elif length > 32:
            length = 32
            self.passwordLengthLineEdit.setText('32')
        self.passwordLineEdit.setText(_generate_password(length, include_uppercase, include_numbers, include_symbols))
        self.passwordGeneratorContainer.hide()
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)

    def back_sign_in_handler(self) -> None:
        self.open_other_window(LoginScreenClass, close_current=True)

    def scan_handler(self) -> None:
        if self.scanButtonClickBlock:
            return
        self.this_window.setEnabled(False)
        self.scan_number += 1
        roi_gray, roi_preview = detect_face()
        if roi_gray is None:
            self.this_window.setEnabled(True)
            self.scan_number -= 1
            return
        roi_gray, roi_preview = roi_gray.copy(), roi_preview.copy()
        self.open_other_window(FaceScanningScreenClass, close_current=False,
                               callback_func=lambda: self.scan_callback_after_scanning(roi_gray),
                               roi_preview=roi_preview, scan_number=self.scan_number)

    def scan_callback_after_scanning(self, roi_gray: np.ndarray):
        self.this_window.setEnabled(True)
        global shared_Register_FaceScanning_image_valid
        if shared_Register_FaceScanning_image_valid:
            shared_Register_FaceScanning_image_valid = False
            self.successful_scans += (roi_gray,)
            if self.scan_number == 3:
                self.scanButtonClickBlock = True
                self.scanButton.setText('Scan My Face (3 Times): 0 Remaining')
                self.remove_message()
                self.change_message('Your Face has been Scanned Successfully')
                self.add_message(Icon.Green_V)
            else:
                self.scanButton.setText(f'Scan My Face (3 Times): {3 - self.scan_number} Remaining')
        else:
            self.scan_number -= 1

    def register_handler(self) -> None:

        if not self.scanButtonClickBlock:
            return
        email = self.emailLineEdit.text()
        password = self.passwordLineEdit.text()
        if not is_valid_email(email):
            self.remove_message()
            self.change_message('Email Bad Format')
            self.add_message(Icon.Red_X)
            return
        if not is_valid_password(password):
            self.remove_message()
            self.change_message('Password Have to Include 6-32 Characters')
            self.add_message(Icon.Red_X)
            return
        result = external.ext_register_handler(email, password, self.successful_scans)
        if result == OperationResultType.SUCCEEDED:
            self.remove_message()
            self.open_other_window(CompressScreenClass, close_current=True)
        elif result == OperationResultType.DETAILS_ERROR:
            self.remove_message()
            self.change_message('This Email is Already in Use by Another Account')
            self.add_message(Icon.Red_X)
        else:
            self.remove_message()
            self.change_message('Connection Error')
            self.add_message(Icon.Red_X)

    def add_message(self, icon_type: Icon) -> None:
        self.buttons_arrangement_with_message()
        if icon_type == Icon.Green_V:
            self.green_v_label.show()
        else:
            self.red_x_label.show()
        self.message_label.show()

    def buttons_arrangement_with_message(self):
        self.scanButton.setGeometry(QRect(230, 320, 500, 40))
        self.registerButton.setGeometry(QRect(380, 390, 200, 40))

    def buttons_arrangement_without_message(self):
        self.scanButton.setGeometry(QRect(230, 340, 500, 40))
        self.registerButton.setGeometry(QRect(380, 410, 200, 40))

    def change_message(self, new_error_msg: str):
        self.message_label.setText(new_error_msg)

    def remove_message(self) -> None:
        self.buttons_arrangement_without_message()
        self.green_v_label.hide()
        self.red_x_label.hide()
        self.message_label.hide()


class CompressScreenClass(GUIScreenClass):
    def __init__(self, CompressWindow: QMainWindow, callback_func: FunctionType) -> None:
        super().__init__(CompressWindow, callback_func)
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

        self.logout_button = QPushButton(self.central_widget)
        self.logout_button.setObjectName('back_sign_in_button')
        self.logout_button.setGeometry(QRect(10, 10, 60, 60))
        self.logout_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.logout_button.clicked.connect(self.logout_handler)
        self.logout_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/backs/logout.png);')

        self.decompressButton = QPushButton(self.central_widget)
        self.decompressButton.setObjectName('decompressButton')
        self.decompressButton.setGeometry(QRect(95, 110, 290, 80))
        font = CompressScreenClass.create_font('Gadugi', 18, True)
        self.decompressButton.setFont(font)
        self.decompressButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.decompressButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Pressed))
        self.decompressButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Released))
        self.decompressButton.clicked.connect(self.decompress_handler)
        self.decompressButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientInvertBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.compressButton = QPushButton(self.central_widget)
        self.compressButton.setObjectName('decompressButton')
        self.compressButton.setGeometry(QRect(575, 110, 290, 80))
        font = CompressScreenClass.create_font('Gadugi', 18, True)
        self.compressButton.setFont(font)
        self.compressButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.compressButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Pressed))
        self.compressButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Released))
        self.compressButton.clicked.connect(self.compress_handler)
        self.compressButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.unlockButton = QPushButton(self.central_widget)
        self.unlockButton.setObjectName('unlockButton')
        self.unlockButton.setGeometry(QRect(142, 220, 196, 210))
        self.unlockButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.unlockButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Pressed))
        self.unlockButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Released))
        self.unlockButton.clicked.connect(self.decompress_handler)
        self.unlockButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/locks/unlock.png);')

        self.lockButton = QPushButton(self.central_widget)
        self.lockButton.setObjectName('lockButton')
        self.lockButton.setGeometry(QRect(652, 220, 136, 210))
        self.lockButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.lockButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Pressed))
        self.lockButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Released))
        self.lockButton.clicked.connect(self.compress_handler)
        self.lockButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/locks/lock.png);')

        self.green_v_label = QLabel(self.central_widget)
        self.green_v_label.setObjectName('green_v_label')
        self.green_v_label.setGeometry(QRect(455, 485, 45, 45))
        self.green_v_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/green_v/green_v.png);')
        self.green_v_label.hide()

        self.red_x_label = QLabel(self.central_widget)
        self.red_x_label.setObjectName('red_x_label')
        self.red_x_label.setGeometry(QRect(455, 485, 45, 45))
        self.red_x_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/red_x/red_x.png);')
        self.red_x_label.hide()

        self.message_label = QLabel(self.central_widget)
        self.message_label.setObjectName('message_label')
        self.message_label.setGeometry(QRect(0, 440, 960, 40))
        font = RegisterScreenClass.create_font('Gadugi', 24, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        CompressWindow.setCentralWidget(self.central_widget)

        CompressWindow.setWindowTitle(QCoreApplication.translate('CompressWindow', 'FZIP Locker', None))
        self.decompressButton.setText(QCoreApplication.translate('CompressWindow', 'Decompress', None))
        self.compressButton.setText(QCoreApplication.translate('CompressWindow', 'Compress', None))
        self.message_label.setText(QCoreApplication.translate('CompressWindow', '', None))

        self.paths = {}

        QMetaObject.connectSlotsByName(CompressWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Decompress:
                self.unlockButton.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/unlock_clicked.png);')
                self.decompressButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertBlueReducedOpacity +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.lockButton.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/lock_clicked.png);')
                self.compressButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlueReducedOpacity +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
        else:
            if button_type == ButtonType.Decompress:
                self.unlockButton.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/unlock.png);')
                self.decompressButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.lockButton.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/lock.png);')
                self.compressButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')

    def logout_handler(self):
        external.ext_logout_handler()
        self.open_other_window(LoginScreenClass, close_current=True)

    def decompress_handler(self) -> None:
        self.this_window.setEnabled(False)
        operation_result, path = external.ext_decompress_handler_select_lock_file()
        self.this_window.setEnabled(True)
        if operation_result == OperationResultType.DETAILS_ERROR:  # Cancel when choosing file
            return
        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return
        self.paths['decompress_lock_file'] = path
        self.remove_message()
        self.this_window.setEnabled(False)
        roi_gray, roi_preview = detect_face()
        if roi_gray is None:
            self.this_window.setEnabled(True)
            return
        roi_gray, roi_preview = roi_gray.copy(), roi_preview.copy()
        self.open_other_window(FaceScanningScreenClass, close_current=False,
                               callback_func=lambda: self.decompress_callback_after_scanning(roi_gray),
                               roi_preview=roi_preview, scan_number=-1)

    def decompress_callback_after_scanning(self, roi_gray: np.ndarray):
        self.this_window.setEnabled(True)
        global shared_Compress_FaceScanning_image_valid
        if not shared_Compress_FaceScanning_image_valid:
            return
        shared_Compress_FaceScanning_image_valid = False

        operation_result = external.ext_decompress_handler_face_authentication(roi_gray)
        if operation_result == OperationResultType.DETAILS_ERROR:
            self.change_message('Face Authentication Failed')
            self.add_message(Icon.Red_X)
            return
        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return

        self.remove_message()
        self.this_window.setEnabled(False)

        self.open_other_window(PasswordScreenClass, close_current=False,
                               callback_func=lambda: self.decompress_callback_after_password(),
                               include_pwd_generator=False)

    def decompress_callback_after_password(self):
        self.this_window.setEnabled(True)
        global shared_Compress_Password_zip_pwd
        if not shared_Compress_Password_zip_pwd:
            return

        operation_result, non_encrypted_path = external.ext_decompress_handler_decrypt_file(
            self.paths['decompress_lock_file'])

        if operation_result == OperationResultType.DETAILS_ERROR:
            self.change_message('The File Does Not Belong to You')
            self.add_message(Icon.Red_X)
            return

        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return
        operation_result = external.ext_decompress_handler_extract_zip(
            non_encrypted_path, shared_Compress_Password_zip_pwd, self.paths['decompress_lock_file'])
        if operation_result == OperationResultType.SUCCEEDED:
            self.remove_message()
            self.change_message('Decompression Completed Successfully')
            self.add_message(Icon.Green_V)

        elif operation_result == OperationResultType.DETAILS_ERROR:
            self.change_message('Incorrect File Password')
            self.add_message(Icon.Red_X)

        else:  # operation_result == OperationResultType.UNKNOWN_ERROR
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)

    def compress_handler(self) -> None:
        self.this_window.setEnabled(False)
        operation_result, paths = external.ext_compress_handler_select_compress_files()
        self.this_window.setEnabled(True)
        if operation_result == OperationResultType.DETAILS_ERROR:  # Cancel when choosing file
            return
        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return
        self.paths['compress_files'] = paths

        self.this_window.setEnabled(False)
        operation_result, path = external.ext_compress_handler_save_as_lock_file()
        self.this_window.setEnabled(True)
        if operation_result == OperationResultType.DETAILS_ERROR:  # Cancel when choosing file
            return
        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return
        self.paths['compress_lock_file'] = path

        self.remove_message()

        self.this_window.setEnabled(False)

        self.open_other_window(PasswordScreenClass, close_current=False,
                               callback_func=lambda: self.compress_callback_after_password(),
                               include_pwd_generator=True)

    def compress_callback_after_password(self):
        self.this_window.setEnabled(True)

        global shared_Compress_Password_zip_pwd
        if not shared_Compress_Password_zip_pwd:
            return
        operation_result, zip_path = external.ext_compress_handler_archive_zip(
            self.paths['compress_files'], self.paths['compress_lock_file'], shared_Compress_Password_zip_pwd)
        if operation_result == OperationResultType.UNKNOWN_ERROR:
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)
            return

        operation_result = external.ext_compress_handler_encrypt_file(self.paths['compress_lock_file'])
        if operation_result == OperationResultType.SUCCEEDED:
            self.remove_message()
            self.change_message('Compression Completed Successfully')
            self.add_message(Icon.Green_V)
        else:  # operation_result == OperationResultType.UNKNOWN_ERROR
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)

    def add_message(self, icon_type: Icon) -> None:
        if icon_type == Icon.Green_V:
            self.green_v_label.show()
        else:
            self.red_x_label.show()
        self.message_label.show()

    def change_message(self, new_error_msg: str):
        self.message_label.setText(new_error_msg)

    def remove_message(self) -> None:
        self.green_v_label.hide()
        self.red_x_label.hide()
        self.message_label.hide()


class FaceScanningScreenClass(GUIScreenClass):
    def __init__(self, FaceScanningWindow: QMainWindow, callback_func: FunctionType,
                 img: np.ndarray, scan_number: int) -> None:
        super().__init__(FaceScanningWindow, callback_func)
        if not FaceScanningWindow.objectName():
            FaceScanningWindow.setObjectName('FaceScanningWindow')
        FaceScanningWindow.resize(960, 540)
        FaceScanningWindow.setMinimumSize(QSize(960, 540))
        FaceScanningWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(FaceScanningWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 0, 960, 81))
        font = FaceScanningScreenClass.create_font('Gadugi', 24, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.img_label = QLabel(self.central_widget)
        self.img_label.setObjectName('img_label')
        img_h, img_w = img.shape[0], img.shape[1]
        self.img_label.setGeometry(QRect(max(0, 480 - img_w // 2), 80, img_w, img_h))
        image = QImage(img, img_w, img_h, img_w * 3, QImage.Format_BGR888)
        pix = QPixmap(image)
        self.img_label.setPixmap(pix)
        self.img_label.setStyleSheet(
            'background-image: url();')

        self.noButton = QPushButton(self.central_widget)
        self.noButton.setObjectName('noButton')
        self.noButton.setGeometry(QRect(145, 430, 190, 60))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.noButton.setFont(font)
        self.noButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.noButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.NO, EventType.Pressed))
        self.noButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.NO, EventType.Released))
        self.noButton.clicked.connect(self.no_handler)
        self.noButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientDarkRed +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.yesButton = QPushButton(self.central_widget)
        self.yesButton.setObjectName('yesButton')
        self.yesButton.setGeometry(QRect(625, 430, 190, 60))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.yesButton.setFont(font)
        self.yesButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.yesButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.YES, EventType.Pressed))
        self.yesButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.YES, EventType.Released))
        self.yesButton.clicked.connect(self.yes_handler)
        self.yesButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientDarkGreen +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        if scan_number == -1:
            title = 'Is This Your Face? - Scan to Compress'
        else:
            title = f'Is This Your Face? - Scan number {scan_number}'

        self.this_window.closeEvent = self.close_event

        self.close_by_X = True

        FaceScanningWindow.setCentralWidget(self.central_widget)

        FaceScanningWindow.setWindowTitle(QCoreApplication.translate('FaceScanningWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate(
            'FaceScanningWindow', title, None))
        self.noButton.setText(QCoreApplication.translate('FaceScanningWindow', 'No', None))
        self.yesButton.setText(QCoreApplication.translate('FaceScanningWindow', 'Yes', None))

        QMetaObject.connectSlotsByName(FaceScanningWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.NO:
                self.noButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBrightRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.yesButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBrightGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
        else:
            if button_type == ButtonType.NO:
                self.noButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientDarkRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.yesButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientDarkGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')

    def no_handler(self) -> None:
        global shared_Register_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
        shared_Register_FaceScanning_image_valid = False
        shared_Compress_FaceScanning_image_valid = False
        self.close_by_X = False
        self.this_window.close()

    def yes_handler(self) -> None:
        global shared_Register_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
        shared_Register_FaceScanning_image_valid = True
        shared_Compress_FaceScanning_image_valid = True
        self.close_by_X = False
        self.this_window.close()

    def close_event(self, event):
        if self.close_by_X:
            global shared_Register_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
            shared_Register_FaceScanning_image_valid = False
            shared_Compress_FaceScanning_image_valid = False
        if self.callback_func:
            self.callback_func()


class PasswordScreenClass(GUIScreenClass):
    def __init__(self, PasswordWindow: QMainWindow, callback_func: FunctionType, include_pwd_generator: bool) -> None:
        super().__init__(PasswordWindow, callback_func)
        if not PasswordWindow.objectName():
            PasswordWindow.setObjectName('PasswordWindow')
        PasswordWindow.resize(480, 270)
        PasswordWindow.setMinimumSize(QSize(480, 270))
        PasswordWindow.setMaximumSize(QSize(480, 270))

        self.central_widget = QWidget(PasswordWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 20, 480, 60))
        font = FaceScanningScreenClass.create_font('Gadugi', 38, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.zip_label_left = QLabel(self.central_widget)
        self.zip_label_left.setObjectName('zip_label_left')
        self.zip_label_left.setGeometry(QRect(-40, 25, 151, 220))
        self.zip_label_left.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_label_right = QLabel(self.central_widget)
        self.zip_label_right.setObjectName('zip_label_right')
        self.zip_label_right.setGeometry(QRect(370, 25, 151, 220))
        self.zip_label_right.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.submitButton = QPushButton(self.central_widget)
        self.submitButton.setObjectName('submitButton')
        self.submitButton.setGeometry(QRect(160, 180, 160, 40))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.submitButton.setFont(font)
        self.submitButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.submitButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Submit, EventType.Pressed))
        self.submitButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Submit, EventType.Released))
        self.submitButton.clicked.connect(self.submit_handler)
        self.submitButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.passwordLineEdit = QLineEdit(self.central_widget)
        self.passwordLineEdit.setObjectName('passwordLineEdit')
        self.passwordLineEdit.setGeometry(QRect(60, 100, 360, 53))
        font = RegisterScreenClass.create_font('Gadugi', 15, True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.passwordLineEdit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.passwordShowButton = QPushButton(self.central_widget)
        self.passwordShowButton.setObjectName('passwordShowButton')
        self.passwordShowButton.setGeometry(QRect(388, 120, 27, 16))
        self.passwordShowButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordShowButton.clicked.connect(self.password_show_handler)
        self.passwordShowButton.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')
        self.passwordGeneratorKey = QPushButton(self.central_widget)
        self.passwordGeneratorKey.setObjectName('passwordGeneratorKey')
        self.passwordGeneratorKey.setGeometry(QRect(362, 118, 21, 20))
        self.passwordGeneratorKey.setCursor(QCursor(Qt.PointingHandCursor))
        self.passwordGeneratorKey.clicked.connect(self.password_generator_handler)
        self.passwordGeneratorKey.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/password_generator_key/password_generator.png);')

        self.passwordGeneratorContainer = QWidget(self.central_widget)
        self.passwordGeneratorContainer.setObjectName('passwordGeneratorContainer')
        self.passwordGeneratorContainer.setGeometry(QRect(296, 140, 180, 130))
        self.passwordGeneratorContainer.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientTransparentWhite +
            'border-radius: 10px')
        self.passwordGeneratorContainer.hide()

        self.passwordLengthLabel = QLabel(self.passwordGeneratorContainer)
        self.passwordLengthLabel.setObjectName('passwordLengthLabel')
        self.passwordLengthLabel.setGeometry(QRect(10, 5, 95, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.passwordLengthLabel.setFont(font)
        self.passwordLengthLabel.setStyleSheet('background-color: rgb();')

        self.passwordLengthLineEdit = QLineEdit(self.passwordGeneratorContainer)
        self.passwordLengthLineEdit.setObjectName('passwordLengthLineEdit')
        self.passwordLengthLineEdit.setGeometry(QRect(102, 4, 25, 20))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
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
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.lowerCaseCheckBox.setFont(font)
        self.lowerCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.lowerCaseCheckBox.setChecked(True)

        self.upperCaseCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.upperCaseCheckBox.setObjectName('upperCaseCheckBox')
        self.upperCaseCheckBox.setEnabled(True)
        self.upperCaseCheckBox.setGeometry(QRect(10, 45, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.upperCaseCheckBox.setFont(font)
        self.upperCaseCheckBox.setStyleSheet('background-color: rgb();')
        self.upperCaseCheckBox.setChecked(False)

        self.numbersCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.numbersCheckBox.setObjectName('numbersCheckBox')
        self.numbersCheckBox.setEnabled(True)
        self.numbersCheckBox.setGeometry(QRect(10, 65, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.numbersCheckBox.setFont(font)
        self.numbersCheckBox.setStyleSheet('background-color: rgb();')
        self.numbersCheckBox.setChecked(False)

        self.symbolsCheckBox = QCheckBox(self.passwordGeneratorContainer)
        self.symbolsCheckBox.setObjectName('symbolsCheckBox')
        self.symbolsCheckBox.setEnabled(True)
        self.symbolsCheckBox.setGeometry(QRect(10, 85, 131, 17))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.symbolsCheckBox.setFont(font)
        self.symbolsCheckBox.setStyleSheet('background-color: rgb();')
        self.symbolsCheckBox.setChecked(False)

        self.generatePasswordButton = QPushButton(self.passwordGeneratorContainer)
        self.generatePasswordButton.setObjectName('generatePasswordButton')
        self.generatePasswordButton.setGeometry(QRect(35, 105, 110, 20))
        font = RegisterScreenClass.create_font('Gadugi', 8, True)
        self.generatePasswordButton.setFont(font)
        self.generatePasswordButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.generatePasswordButton.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Pressed))
        self.generatePasswordButton.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Released))
        self.generatePasswordButton.clicked.connect(self.generate_password)
        self.generatePasswordButton.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientOlivePurple +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        if not include_pwd_generator:
            self.passwordGeneratorKey.hide()

        self.this_window.closeEvent = self.close_event

        self.close_by_X = True

        PasswordWindow.setCentralWidget(self.central_widget)

        PasswordWindow.setWindowTitle(QCoreApplication.translate('PasswordWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('PasswordWindow', 'FZIP Locker', None))
        self.submitButton.setText(QCoreApplication.translate('RegisterWindow', 'Submit', None))
        self.passwordLineEdit.setPlaceholderText(QCoreApplication.translate('PasswordWindow', 'File Password', None))
        self.passwordLengthLabel.setText(QCoreApplication.translate('PasswordWindow', 'Password Length', None))
        self.lowerCaseCheckBox.setText(QCoreApplication.translate('PasswordWindow', 'Lower case included', None))
        self.upperCaseCheckBox.setText(QCoreApplication.translate('PasswordWindow', 'Upper case included', None))
        self.numbersCheckBox.setText(QCoreApplication.translate('PasswordWindow', 'Numbers included', None))
        self.symbolsCheckBox.setText(QCoreApplication.translate('PasswordWindow', 'Symbols included', None))
        self.generatePasswordButton.setText(QCoreApplication.translate('PasswordWindow', 'Generate Password', None))

        QMetaObject.connectSlotsByName(PasswordWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Submit:
                self.submitButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.generatePasswordButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.Submit:
                self.submitButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.generatePasswordButton.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientOlivePurple +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)
        else:
            self.passwordLineEdit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.passwordLineEdit.echoMode() == QLineEdit.Password

    def password_generator_handler(self) -> None:
        if self.passwordGeneratorContainer.isVisible():
            self.passwordGeneratorContainer.hide()
        else:
            self.passwordGeneratorContainer.show()

    def generate_password(self) -> None:
        if not self.passwordLengthLineEdit.text():
            self.passwordLengthLineEdit.setText('6')

        include_uppercase = self.upperCaseCheckBox.isChecked()
        include_numbers = self.numbersCheckBox.isChecked()
        include_symbols = self.symbolsCheckBox.isChecked()
        length = int(self.passwordLengthLineEdit.text())
        if length < 6:
            length = 6
            self.passwordLengthLineEdit.setText('6')
        elif length > 32:
            length = 32
            self.passwordLengthLineEdit.setText('32')
        self.passwordLineEdit.setText(_generate_password(length, include_uppercase, include_numbers, include_symbols))
        self.passwordGeneratorContainer.hide()
        if self.is_password_hidden():
            self.passwordLineEdit.setEchoMode(QLineEdit.Normal)

    def submit_handler(self) -> None:
        password = self.passwordLineEdit.text()
        if not is_valid_password(password):
            return
        global shared_Compress_Password_zip_pwd
        shared_Compress_Password_zip_pwd = self.passwordLineEdit.text()
        self.close_by_X = False
        self.this_window.close()

    def close_event(self, event):
        if self.close_by_X:
            global shared_Compress_Password_zip_pwd
            shared_Compress_Password_zip_pwd = ''
        if self.callback_func:
            self.callback_func()


def run_window(WindowClass: type, image=None) -> None:
    app = QtWidgets.QApplication([])
    MainWindow = QtWidgets.QMainWindow()
    if image is not None:
        WindowClass(MainWindow, None, image)
    else:
        WindowClass(MainWindow, None)
    MainWindow.show()
    app.exec_()
