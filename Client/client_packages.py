"""
Script for Installing Client's Packages
"""
from os import system as command

packages = 'pycryptodome', 'opencv-python', 'opencv-contrib-python', 'PyQt5', 'pyminizip'

for pkg in packages:
    print(f'Installing {pkg}...')
    command(f'pip install {pkg}')
