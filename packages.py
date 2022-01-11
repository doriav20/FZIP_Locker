"""
Script for Installing Project's Packages
"""
from os import system as command

packages = 'opencv-python',\
           'opencv-contrib-python',\
           'PyQt5',\
           'pyqt5-tools',\
           'pycryptodome',\
           'pyminizip',\
           'pymongo',\
           'pymongo[srv]'

for pkg in packages:
    print(f'Installing {pkg}...')
    command(f'pip install {pkg}')
