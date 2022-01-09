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
    Generate_Password = 4
    Decompress = 5
    Compress = 6
    NO = 7
    YES = 8
    Submit = 9


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

shared_SignUp_FaceScanning_image_valid = False  # Shared with SignUp & Face Scanning Screens
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


class SignInScreenClass(GUIScreenClass):
    def __init__(self, SignInWindow: QMainWindow, callback_func: FunctionType) -> None:
        super().__init__(SignInWindow, callback_func)
        if not SignInWindow.objectName():
            SignInWindow.setObjectName('SignInWindow')
        SignInWindow.resize(960, 540)
        SignInWindow.setMinimumSize(QSize(960, 540))
        SignInWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(SignInWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 40, 960, 61))
        font = SignInScreenClass.create_font('Gadugi', 38, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.zip_left_label = QLabel(self.central_widget)
        self.zip_left_label.setObjectName('zip_left_label')
        self.zip_left_label.setGeometry(QRect(-60, 10, 341, 521))
        self.zip_left_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_right_label = QLabel(self.central_widget)
        self.zip_right_label.setObjectName('zip_right_label')
        self.zip_right_label.setGeometry(QRect(660, 10, 341, 521))
        self.zip_right_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.email_line_edit = QLineEdit(self.central_widget)
        self.email_line_edit.setObjectName('email_line_edit')
        self.email_line_edit.setGeometry(QRect(270, 160, 426, 53))
        font = SignInScreenClass.create_font('Gadugi', 15, True)
        self.email_line_edit.setFont(font)
        self.email_line_edit.setEchoMode(QLineEdit.Normal)
        self.email_line_edit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.password_line_edit = QLineEdit(self.central_widget)
        self.password_line_edit.setObjectName('password_line_edit')
        self.password_line_edit.setGeometry(QRect(270, 240, 426, 53))
        font = SignInScreenClass.create_font('Gadugi', 15, True)
        self.password_line_edit.setFont(font)
        self.password_line_edit.setEchoMode(QLineEdit.Password)
        self.password_line_edit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.password_show_button = QPushButton(self.central_widget)
        self.password_show_button.setObjectName('password_show_button')
        self.password_show_button.setGeometry(QRect(662, 260, 27, 16))
        self.password_show_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.password_show_button.clicked.connect(self.password_show_handler)
        self.password_show_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')

        self.sign_in_button = QPushButton(self.central_widget)
        self.sign_in_button.setObjectName('sign_in_button')
        self.sign_in_button.setGeometry(QRect(401, 340, 158, 40))
        font = SignInScreenClass.create_font('Gadugi', 18, True)
        self.sign_in_button.setFont(font)
        self.sign_in_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.sign_in_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignIn, EventType.Pressed))
        self.sign_in_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignIn, EventType.Released))
        self.sign_in_button.clicked.connect(self.sign_in_handler)
        self.sign_in_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.sign_up_button = QPushButton(self.central_widget)
        self.sign_up_button.setObjectName('sign_up_button')
        self.sign_up_button.setGeometry(QRect(280, 410, 400, 40))
        font = SignInScreenClass.create_font('Gadugi', 18, True)
        self.sign_up_button.setFont(font)
        self.sign_up_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.sign_up_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Pressed))
        self.sign_up_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Released))
        self.sign_up_button.clicked.connect(self.sign_up_handler)
        self.sign_up_button.setStyleSheet(
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
        font = SignInScreenClass.create_font('Gadugi', 18, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        SignInWindow.setCentralWidget(self.central_widget)

        SignInWindow.setWindowTitle(QCoreApplication.translate('SignInWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('SignInWindow', 'FZIP Locker', None))
        self.email_line_edit.setPlaceholderText(QCoreApplication.translate('SignInWindow', 'Email', None))
        self.password_line_edit.setPlaceholderText(QCoreApplication.translate('SignInWindow', 'Password', None))
        self.sign_in_button.setText(QCoreApplication.translate('SignInWindow', 'Sign in', None))
        self.sign_up_button.setText(QCoreApplication.translate('SignInWindow', 'Don\'t have an account? Sign up', None))
        self.message_label.setText(QCoreApplication.translate('SignInWindow', '', None))

        QMetaObject.connectSlotsByName(SignInWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.SignIn:
                self.sign_in_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.sign_up_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.SignIn:
                self.sign_in_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.sign_up_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.password_line_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_line_edit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.password_line_edit.echoMode() == QLineEdit.Password

    def sign_in_handler(self) -> None:
        email = self.email_line_edit.text()
        password = self.password_line_edit.text()
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
            self.password_line_edit.setText('')
            self.change_message('User Does Not Exist / Wrong Password')
            self.add_message(Icon.Red_X)
        elif operation_result == OperationResultType.CONNECTION_ERROR:
            self.password_line_edit.setText('')
            self.remove_message()
            self.change_message('Connection Error')
            self.add_message(Icon.Red_X)
        else:
            self.password_line_edit.setText('')
            self.remove_message()
            self.change_message('Unknown Error')
            self.add_message(Icon.Red_X)

    def sign_up_handler(self) -> None:
        self.open_other_window(SignUpScreenClass, close_current=True)

    def add_message(self, icon_type: Icon) -> None:
        self.buttons_arrangement_with_message()
        if icon_type == Icon.Red_X:
            self.red_x_label.show()
        self.message_label.show()

    def buttons_arrangement_with_message(self):
        self.sign_in_button.setGeometry(QRect(401, 320, 158, 40))
        self.sign_up_button.setGeometry(QRect(280, 390, 400, 40))

    def buttons_arrangement_without_message(self):
        self.sign_in_button.setGeometry(QRect(401, 340, 158, 40))
        self.sign_up_button.setGeometry(QRect(280, 410, 400, 40))

    def change_message(self, new_error_msg: str):
        self.message_label.setText(new_error_msg)

    def remove_message(self) -> None:
        self.buttons_arrangement_without_message()
        self.red_x_label.hide()
        self.message_label.hide()


class SignUpScreenClass(GUIScreenClass):
    def __init__(self, SignUpWindow: QMainWindow, callback_func: FunctionType) -> None:
        super().__init__(SignUpWindow, callback_func)
        if not SignUpWindow.objectName():
            SignUpWindow.setObjectName('SignUpWindow')
        SignUpWindow.resize(960, 540)
        SignUpWindow.setMinimumSize(QSize(960, 540))
        SignUpWindow.setMaximumSize(QSize(960, 540))

        self.central_widget = QWidget(SignUpWindow)
        self.central_widget.setObjectName('central_widget')
        self.central_widget.setStyleSheet(
            'background-image: url(:/bg_image/gray_background.jpg);'
            'background-position: center;')

        self.title_label = QLabel(self.central_widget)
        self.title_label.setObjectName('title_label')
        self.title_label.setGeometry(QRect(0, 40, 960, 61))
        font = SignUpScreenClass.create_font('Gadugi', 38, True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')

        self.zip_left_label = QLabel(self.central_widget)
        self.zip_left_label.setObjectName('zip_left_label')
        self.zip_left_label.setGeometry(QRect(-60, 10, 341, 521))
        self.zip_left_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_right_label = QLabel(self.central_widget)
        self.zip_right_label.setObjectName('zip_right_label')
        self.zip_right_label.setGeometry(QRect(660, 10, 341, 521))
        self.zip_right_label.setStyleSheet(
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

        self.email_line_edit = QLineEdit(self.central_widget)
        self.email_line_edit.setObjectName('email_line_edit')
        self.email_line_edit.setGeometry(QRect(270, 160, 426, 53))
        font = SignUpScreenClass.create_font('Gadugi', 15, True)
        self.email_line_edit.setFont(font)
        self.email_line_edit.setEchoMode(QLineEdit.Normal)
        self.email_line_edit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.password_line_edit = QLineEdit(self.central_widget)
        self.password_line_edit.setObjectName('password_line_edit')
        self.password_line_edit.setGeometry(QRect(270, 240, 426, 53))
        font = SignUpScreenClass.create_font('Gadugi', 15, True)
        self.password_line_edit.setFont(font)
        self.password_line_edit.setEchoMode(QLineEdit.Password)
        self.password_line_edit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.scan_button = QPushButton(self.central_widget)
        self.scan_button.setObjectName('scan_button')
        self.scan_button.setGeometry(QRect(230, 340, 500, 40))
        font = SignUpScreenClass.create_font('Gadugi', 18, True)
        self.scan_button.setFont(font)
        self.scan_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.scan_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Scan, EventType.Pressed))
        self.scan_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Scan, EventType.Released))
        self.scan_button.clicked.connect(self.scan_handler)
        self.scan_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGray +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')
        self.scan_buttonClickBlock = False
        self.scan_number = 0

        self.sign_up_button = QPushButton(self.central_widget)
        self.sign_up_button.setObjectName('sign_up_button')
        self.sign_up_button.setGeometry(QRect(380, 410, 200, 40))
        font = SignUpScreenClass.create_font('Gadugi', 18, True)
        self.sign_up_button.setFont(font)
        self.sign_up_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.sign_up_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Pressed))
        self.sign_up_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.SignUp, EventType.Released))
        self.sign_up_button.clicked.connect(self.sign_up_handler)
        self.sign_up_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientGreen +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        self.password_show_button = QPushButton(self.central_widget)
        self.password_show_button.setObjectName('password_show_button')
        self.password_show_button.setGeometry(QRect(662, 260, 27, 16))
        self.password_show_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.password_show_button.clicked.connect(self.password_show_handler)
        self.password_show_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')

        self.password_generator_key = QPushButton(self.central_widget)
        self.password_generator_key.setObjectName('password_generator_key')
        self.password_generator_key.setGeometry(QRect(636, 258, 21, 20))
        self.password_generator_key.setCursor(QCursor(Qt.PointingHandCursor))
        self.password_generator_key.clicked.connect(self.password_generator_handler)
        self.password_generator_key.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/password_generator_key/password_generator.png);')

        self.password_generator_container = QWidget(self.central_widget)
        self.password_generator_container.setObjectName('password_generator_container')
        self.password_generator_container.setGeometry(QRect(570, 280, 180, 130))
        self.password_generator_container.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientTransparentWhite +
            'border-radius: 10px')
        self.password_generator_container.hide()

        self.password_length_label = QLabel(self.password_generator_container)
        self.password_length_label.setObjectName('password_length_label')
        self.password_length_label.setGeometry(QRect(10, 5, 95, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.password_length_label.setFont(font)
        self.password_length_label.setStyleSheet('background-color: rgb();')

        self.password_length_line_edit = QLineEdit(self.password_generator_container)
        self.password_length_line_edit.setObjectName('password_length_line_edit')
        self.password_length_line_edit.setGeometry(QRect(102, 4, 25, 20))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.password_length_line_edit.setFont(font)
        self.password_length_line_edit.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.password_length_line_edit.setStyleSheet(
            'border-style: solid;'
            'border-width: 2px;'
            'border-color: rgb(0, 0, 0);')
        validator = QIntValidator(1, 99)
        self.password_length_line_edit.setValidator(validator)

        self.lower_case_check_box = QCheckBox(self.password_generator_container)
        self.lower_case_check_box.setObjectName('lower_case_check_box')
        self.lower_case_check_box.setEnabled(False)
        self.lower_case_check_box.setGeometry(QRect(10, 25, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.lower_case_check_box.setFont(font)
        self.lower_case_check_box.setStyleSheet('background-color: rgb();')
        self.lower_case_check_box.setChecked(True)

        self.upper_case_check_box = QCheckBox(self.password_generator_container)
        self.upper_case_check_box.setObjectName('upper_case_check_box')
        self.upper_case_check_box.setEnabled(True)
        self.upper_case_check_box.setGeometry(QRect(10, 45, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.upper_case_check_box.setFont(font)
        self.upper_case_check_box.setStyleSheet('background-color: rgb();')
        self.upper_case_check_box.setChecked(False)

        self.numbers_check_box = QCheckBox(self.password_generator_container)
        self.numbers_check_box.setObjectName('numbers_check_box')
        self.numbers_check_box.setEnabled(True)
        self.numbers_check_box.setGeometry(QRect(10, 65, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.numbers_check_box.setFont(font)
        self.numbers_check_box.setStyleSheet('background-color: rgb();')
        self.numbers_check_box.setChecked(False)

        self.symbols_check_box = QCheckBox(self.password_generator_container)
        self.symbols_check_box.setObjectName('symbols_check_box')
        self.symbols_check_box.setEnabled(True)
        self.symbols_check_box.setGeometry(QRect(10, 85, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.symbols_check_box.setFont(font)
        self.symbols_check_box.setStyleSheet('background-color: rgb();')
        self.symbols_check_box.setChecked(False)

        self.generate_password_button = QPushButton(self.password_generator_container)
        self.generate_password_button.setObjectName('generate_password_button')
        self.generate_password_button.setGeometry(QRect(35, 105, 110, 20))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.generate_password_button.setFont(font)
        self.generate_password_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.generate_password_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Pressed))
        self.generate_password_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Released))
        self.generate_password_button.clicked.connect(self.generate_password)
        self.generate_password_button.setStyleSheet(
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
        font = SignUpScreenClass.create_font('Gadugi', 18, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        SignUpWindow.setCentralWidget(self.central_widget)

        SignUpWindow.setWindowTitle(QCoreApplication.translate('SignUpWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('SignUpWindow', 'FZIP Locker', None))
        self.email_line_edit.setPlaceholderText(QCoreApplication.translate('SignUpWindow', 'Email', None))
        self.password_line_edit.setPlaceholderText(QCoreApplication.translate('SignUpWindow', 'Password', None))
        self.scan_button.setText(QCoreApplication.translate(
            'SignUpWindow', 'Scan My Face (3 Times): 3 Remaining', None))
        self.sign_up_button.setText(QCoreApplication.translate('SignUpWindow', 'Sign up', None))
        self.password_length_label.setText(QCoreApplication.translate('SignUpWindow', 'Password Length', None))
        self.lower_case_check_box.setText(QCoreApplication.translate('SignUpWindow', 'Lower case included', None))
        self.upper_case_check_box.setText(QCoreApplication.translate('SignUpWindow', 'Upper case included', None))
        self.numbers_check_box.setText(QCoreApplication.translate('SignUpWindow', 'Numbers included', None))
        self.symbols_check_box.setText(QCoreApplication.translate('SignUpWindow', 'Symbols included', None))
        self.generate_password_button.setText(QCoreApplication.translate('SignUpWindow', 'Generate Password', None))
        self.message_label.setText(QCoreApplication.translate('SignUpWindow', '', None))

        self.successful_scans = ()

        QMetaObject.connectSlotsByName(SignUpWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Scan:
                self.scan_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            elif button_type == ButtonType.SignUp:
                self.sign_up_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.generate_password_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.Scan:
                self.scan_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGray +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            elif button_type == ButtonType.SignUp:
                self.sign_up_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')
            else:
                self.generate_password_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientOlivePurple +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.password_line_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_line_edit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.password_line_edit.echoMode() == QLineEdit.Password

    def password_generator_handler(self) -> None:
        if self.password_generator_container.isVisible():
            self.password_generator_container.hide()
        else:
            self.password_generator_container.show()

    def generate_password(self) -> None:
        if not self.password_length_line_edit.text():
            self.password_length_line_edit.setText('6')

        include_uppercase = self.upper_case_check_box.isChecked()
        include_numbers = self.numbers_check_box.isChecked()
        include_symbols = self.symbols_check_box.isChecked()
        length = int(self.password_length_line_edit.text())
        if length < 6:
            length = 6
            self.password_length_line_edit.setText('6')
        elif length > 32:
            length = 32
            self.password_length_line_edit.setText('32')
        self.password_line_edit.setText(_generate_password(length, include_uppercase, include_numbers, include_symbols))
        self.password_generator_container.hide()
        if self.is_password_hidden():
            self.password_line_edit.setEchoMode(QLineEdit.Normal)

    def back_sign_in_handler(self) -> None:
        self.open_other_window(SignInScreenClass, close_current=True)

    def scan_handler(self) -> None:
        if self.scan_buttonClickBlock:
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
        global shared_SignUp_FaceScanning_image_valid
        if shared_SignUp_FaceScanning_image_valid:
            shared_SignUp_FaceScanning_image_valid = False
            self.successful_scans += (roi_gray,)
            if self.scan_number == 3:
                self.scan_buttonClickBlock = True
                self.scan_button.setText('Scan My Face (3 Times): 0 Remaining')
                self.remove_message()
                self.change_message('Your Face has been Scanned Successfully')
                self.add_message(Icon.Green_V)
            else:
                self.scan_button.setText(f'Scan My Face (3 Times): {3 - self.scan_number} Remaining')
        else:
            self.scan_number -= 1

    def sign_up_handler(self) -> None:

        if not self.scan_buttonClickBlock:
            return
        email = self.email_line_edit.text()
        password = self.password_line_edit.text()
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
        result = external.ext_sign_up_handler(email, password, self.successful_scans)
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
        self.scan_button.setGeometry(QRect(230, 320, 500, 40))
        self.sign_up_button.setGeometry(QRect(380, 390, 200, 40))

    def buttons_arrangement_without_message(self):
        self.scan_button.setGeometry(QRect(230, 340, 500, 40))
        self.sign_up_button.setGeometry(QRect(380, 410, 200, 40))

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

        self.decompress_button = QPushButton(self.central_widget)
        self.decompress_button.setObjectName('decompress_button')
        self.decompress_button.setGeometry(QRect(95, 110, 290, 80))
        font = CompressScreenClass.create_font('Gadugi', 18, True)
        self.decompress_button.setFont(font)
        self.decompress_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.decompress_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Pressed))
        self.decompress_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Released))
        self.decompress_button.clicked.connect(self.decompress_handler)
        self.decompress_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientInvertBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.compress_button = QPushButton(self.central_widget)
        self.compress_button.setObjectName('compress_button')
        self.compress_button.setGeometry(QRect(575, 110, 290, 80))
        font = CompressScreenClass.create_font('Gadugi', 18, True)
        self.compress_button.setFont(font)
        self.compress_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.compress_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Pressed))
        self.compress_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Released))
        self.compress_button.clicked.connect(self.compress_handler)
        self.compress_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.unlock_button = QPushButton(self.central_widget)
        self.unlock_button.setObjectName('unlock_button')
        self.unlock_button.setGeometry(QRect(142, 220, 196, 210))
        self.unlock_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.unlock_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Pressed))
        self.unlock_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Decompress, EventType.Released))
        self.unlock_button.clicked.connect(self.decompress_handler)
        self.unlock_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/locks/unlock.png);')

        self.lock_button = QPushButton(self.central_widget)
        self.lock_button.setObjectName('lock_button')
        self.lock_button.setGeometry(QRect(652, 220, 136, 210))
        self.lock_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.lock_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Pressed))
        self.lock_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Compress, EventType.Released))
        self.lock_button.clicked.connect(self.compress_handler)
        self.lock_button.setStyleSheet(
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
        font = SignUpScreenClass.create_font('Gadugi', 24, True)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(
            'background-image: url();'
            'color: rgb(255, 255, 255);')
        self.message_label.hide()

        CompressWindow.setCentralWidget(self.central_widget)

        CompressWindow.setWindowTitle(QCoreApplication.translate('CompressWindow', 'FZIP Locker', None))
        self.decompress_button.setText(QCoreApplication.translate('CompressWindow', 'Decompress', None))
        self.compress_button.setText(QCoreApplication.translate('CompressWindow', 'Compress', None))
        self.message_label.setText(QCoreApplication.translate('CompressWindow', '', None))

        self.paths = {}

        QMetaObject.connectSlotsByName(CompressWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Decompress:
                self.unlock_button.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/unlock_clicked.png);')
                self.decompress_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertBlueReducedOpacity +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.lock_button.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/lock_clicked.png);')
                self.compress_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlueReducedOpacity +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
        else:
            if button_type == ButtonType.Decompress:
                self.unlock_button.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/unlock.png);')
                self.decompress_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientInvertBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.lock_button.setStyleSheet(
                    'background-image: url();'
                    'border-image: url(:/locks/lock.png);')
                self.compress_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')

    def logout_handler(self):
        external.ext_logout_handler()
        self.open_other_window(SignInScreenClass, close_current=True)

    def decompress_handler(self) -> None:
        self.remove_message()
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
        self.remove_message()
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

        self.no_button = QPushButton(self.central_widget)
        self.no_button.setObjectName('no_button')
        self.no_button.setGeometry(QRect(145, 430, 190, 60))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.no_button.setFont(font)
        self.no_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.no_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.NO, EventType.Pressed))
        self.no_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.NO, EventType.Released))
        self.no_button.clicked.connect(self.no_handler)
        self.no_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientDarkRed +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.yes_button = QPushButton(self.central_widget)
        self.yes_button.setObjectName('yes_button')
        self.yes_button.setGeometry(QRect(625, 430, 190, 60))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.yes_button.setFont(font)
        self.yes_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.yes_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.YES, EventType.Pressed))
        self.yes_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.YES, EventType.Released))
        self.yes_button.clicked.connect(self.yes_handler)
        self.yes_button.setStyleSheet(
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
        self.no_button.setText(QCoreApplication.translate('FaceScanningWindow', 'No', None))
        self.yes_button.setText(QCoreApplication.translate('FaceScanningWindow', 'Yes', None))

        QMetaObject.connectSlotsByName(FaceScanningWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.NO:
                self.no_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBrightRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.yes_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBrightGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
        else:
            if button_type == ButtonType.NO:
                self.no_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientDarkRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.yes_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientDarkGreen +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')

    def no_handler(self) -> None:
        global shared_SignUp_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
        shared_SignUp_FaceScanning_image_valid = False
        shared_Compress_FaceScanning_image_valid = False
        self.close_by_X = False
        self.this_window.close()

    def yes_handler(self) -> None:
        global shared_SignUp_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
        shared_SignUp_FaceScanning_image_valid = True
        shared_Compress_FaceScanning_image_valid = True
        self.close_by_X = False
        self.this_window.close()

    def close_event(self, event):
        if self.close_by_X:
            global shared_SignUp_FaceScanning_image_valid, shared_Compress_FaceScanning_image_valid
            shared_SignUp_FaceScanning_image_valid = False
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

        self.zip_left_label = QLabel(self.central_widget)
        self.zip_left_label.setObjectName('zip_left_label')
        self.zip_left_label.setGeometry(QRect(-40, 25, 151, 220))
        self.zip_left_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.zip_right_label = QLabel(self.central_widget)
        self.zip_right_label.setObjectName('zip_right_label')
        self.zip_right_label.setGeometry(QRect(370, 25, 151, 220))
        self.zip_right_label.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/zip_image/zip_image.png);')

        self.submit_button = QPushButton(self.central_widget)
        self.submit_button.setObjectName('submit_button')
        self.submit_button.setGeometry(QRect(160, 180, 160, 40))
        font = FaceScanningScreenClass.create_font('Gadugi', 18, True)
        self.submit_button.setFont(font)
        self.submit_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Submit, EventType.Pressed))
        self.submit_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Submit, EventType.Released))
        self.submit_button.clicked.connect(self.submit_handler)
        self.submit_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientBlue +
            'color: rgb(255, 255, 255);'
            'border-radius:20px;')

        self.password_line_edit = QLineEdit(self.central_widget)
        self.password_line_edit.setObjectName('password_line_edit')
        self.password_line_edit.setGeometry(QRect(60, 100, 360, 53))
        font = SignUpScreenClass.create_font('Gadugi', 15, True)
        self.password_line_edit.setFont(font)
        self.password_line_edit.setEchoMode(QLineEdit.Password)
        self.password_line_edit.setStyleSheet(
            'background-image: url();'
            'background-color: rgba(0, 0, 0, 0);'
            'border: 1px solid black;'
            'color: rgb(255, 255, 255);')

        self.password_show_button = QPushButton(self.central_widget)
        self.password_show_button.setObjectName('password_show_button')
        self.password_show_button.setGeometry(QRect(388, 120, 27, 16))
        self.password_show_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.password_show_button.clicked.connect(self.password_show_handler)
        self.password_show_button.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/eye/eye.png);')
        self.password_generator_key = QPushButton(self.central_widget)
        self.password_generator_key.setObjectName('password_generator_key')
        self.password_generator_key.setGeometry(QRect(362, 118, 21, 20))
        self.password_generator_key.setCursor(QCursor(Qt.PointingHandCursor))
        self.password_generator_key.clicked.connect(self.password_generator_handler)
        self.password_generator_key.setStyleSheet(
            'background-image: url();'
            'border-image: url(:/password_generator_key/password_generator.png);')

        self.password_generator_container = QWidget(self.central_widget)
        self.password_generator_container.setObjectName('password_generator_container')
        self.password_generator_container.setGeometry(QRect(296, 140, 180, 130))
        self.password_generator_container.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientTransparentWhite +
            'border-radius: 10px')
        self.password_generator_container.hide()

        self.password_length_label = QLabel(self.password_generator_container)
        self.password_length_label.setObjectName('password_length_label')
        self.password_length_label.setGeometry(QRect(10, 5, 95, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.password_length_label.setFont(font)
        self.password_length_label.setStyleSheet('background-color: rgb();')

        self.password_length_line_edit = QLineEdit(self.password_generator_container)
        self.password_length_line_edit.setObjectName('password_length_line_edit')
        self.password_length_line_edit.setGeometry(QRect(102, 4, 25, 20))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.password_length_line_edit.setFont(font)
        self.password_length_line_edit.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.password_length_line_edit.setStyleSheet(
            'border-style: solid;'
            'border-width: 2px;'
            'border-color: rgb(0, 0, 0);')
        validator = QIntValidator(1, 99)
        self.password_length_line_edit.setValidator(validator)

        self.lower_case_check_box = QCheckBox(self.password_generator_container)
        self.lower_case_check_box.setObjectName('lower_case_check_box')
        self.lower_case_check_box.setEnabled(False)
        self.lower_case_check_box.setGeometry(QRect(10, 25, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.lower_case_check_box.setFont(font)
        self.lower_case_check_box.setStyleSheet('background-color: rgb();')
        self.lower_case_check_box.setChecked(True)

        self.upper_case_check_box = QCheckBox(self.password_generator_container)
        self.upper_case_check_box.setObjectName('upper_case_check_box')
        self.upper_case_check_box.setEnabled(True)
        self.upper_case_check_box.setGeometry(QRect(10, 45, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.upper_case_check_box.setFont(font)
        self.upper_case_check_box.setStyleSheet('background-color: rgb();')
        self.upper_case_check_box.setChecked(False)

        self.numbers_check_box = QCheckBox(self.password_generator_container)
        self.numbers_check_box.setObjectName('numbers_check_box')
        self.numbers_check_box.setEnabled(True)
        self.numbers_check_box.setGeometry(QRect(10, 65, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.numbers_check_box.setFont(font)
        self.numbers_check_box.setStyleSheet('background-color: rgb();')
        self.numbers_check_box.setChecked(False)

        self.symbols_check_box = QCheckBox(self.password_generator_container)
        self.symbols_check_box.setObjectName('symbols_check_box')
        self.symbols_check_box.setEnabled(True)
        self.symbols_check_box.setGeometry(QRect(10, 85, 131, 17))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.symbols_check_box.setFont(font)
        self.symbols_check_box.setStyleSheet('background-color: rgb();')
        self.symbols_check_box.setChecked(False)

        self.generate_password_button = QPushButton(self.password_generator_container)
        self.generate_password_button.setObjectName('generate_password_button')
        self.generate_password_button.setGeometry(QRect(35, 105, 110, 20))
        font = SignUpScreenClass.create_font('Gadugi', 8, True)
        self.generate_password_button.setFont(font)
        self.generate_password_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.generate_password_button.pressed.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Pressed))
        self.generate_password_button.released.connect(
            lambda: self.change_pressed_button_style(ButtonType.Generate_Password, EventType.Released))
        self.generate_password_button.clicked.connect(self.generate_password)
        self.generate_password_button.setStyleSheet(
            'background-image: url();'
            'background-color: ' + GradientOlivePurple +
            'color: rgb(255, 255, 255);'
            'border-radius:10px;')

        if not include_pwd_generator:
            self.password_generator_key.hide()

        self.this_window.closeEvent = self.close_event

        self.close_by_X = True

        PasswordWindow.setCentralWidget(self.central_widget)

        PasswordWindow.setWindowTitle(QCoreApplication.translate('PasswordWindow', 'FZIP Locker', None))
        self.title_label.setText(QCoreApplication.translate('PasswordWindow', 'FZIP Locker', None))
        self.submit_button.setText(QCoreApplication.translate('PasswordWindow', 'Submit', None))
        self.password_line_edit.setPlaceholderText(QCoreApplication.translate('PasswordWindow', 'File Password', None))
        self.password_length_label.setText(QCoreApplication.translate('PasswordWindow', 'Password Length', None))
        self.lower_case_check_box.setText(QCoreApplication.translate('PasswordWindow', 'Lower case included', None))
        self.upper_case_check_box.setText(QCoreApplication.translate('PasswordWindow', 'Upper case included', None))
        self.numbers_check_box.setText(QCoreApplication.translate('PasswordWindow', 'Numbers included', None))
        self.symbols_check_box.setText(QCoreApplication.translate('PasswordWindow', 'Symbols included', None))
        self.generate_password_button.setText(QCoreApplication.translate('PasswordWindow', 'Generate Password', None))

        QMetaObject.connectSlotsByName(PasswordWindow)

    def change_pressed_button_style(self, button_type: ButtonType, event_type: EventType) -> None:
        if event_type == EventType.Pressed:
            if button_type == ButtonType.Submit:
                self.submit_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.generate_password_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientRed +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

        else:
            if button_type == ButtonType.Submit:
                self.submit_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientBlue +
                    'color: rgb(255, 255, 255);'
                    'border-radius:20px;')
            else:
                self.generate_password_button.setStyleSheet(
                    'background-image: url();'
                    'background-color: ' + GradientOlivePurple +
                    'color: rgb(255, 255, 255);'
                    'border-radius:10px;')

    def password_show_handler(self) -> None:
        if self.is_password_hidden():
            self.password_line_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_line_edit.setEchoMode(QLineEdit.Password)

    def is_password_hidden(self) -> bool:
        return self.password_line_edit.echoMode() == QLineEdit.Password

    def password_generator_handler(self) -> None:
        if self.password_generator_container.isVisible():
            self.password_generator_container.hide()
        else:
            self.password_generator_container.show()

    def generate_password(self) -> None:
        if not self.password_length_line_edit.text():
            self.password_length_line_edit.setText('6')

        include_uppercase = self.upper_case_check_box.isChecked()
        include_numbers = self.numbers_check_box.isChecked()
        include_symbols = self.symbols_check_box.isChecked()
        length = int(self.password_length_line_edit.text())
        if length < 6:
            length = 6
            self.password_length_line_edit.setText('6')
        elif length > 32:
            length = 32
            self.password_length_line_edit.setText('32')
        self.password_line_edit.setText(_generate_password(length, include_uppercase, include_numbers, include_symbols))
        self.password_generator_container.hide()
        if self.is_password_hidden():
            self.password_line_edit.setEchoMode(QLineEdit.Normal)

    def submit_handler(self) -> None:
        password = self.password_line_edit.text()
        if not is_valid_password(password):
            return
        global shared_Compress_Password_zip_pwd
        shared_Compress_Password_zip_pwd = self.password_line_edit.text()
        self.close_by_X = False
        self.this_window.close()

    def close_event(self, event):
        if self.close_by_X:
            global shared_Compress_Password_zip_pwd
            shared_Compress_Password_zip_pwd = ''
        if self.callback_func:
            self.callback_func()


def start_program() -> None:
    app = QtWidgets.QApplication([])
    sign_in_window = QtWidgets.QMainWindow()
    SignInScreenClass(sign_in_window, None)
    sign_in_window.show()
    app.exec_()


if __name__ == '__main__':
    start_program()
