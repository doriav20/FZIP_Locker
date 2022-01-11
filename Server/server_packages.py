"""
Script for Installing Server's Packages
"""
from os import system as command

packages = 'pymongo', 'pymongo[srv]', 'pycryptodome', 'opencv-python', 'opencv-contrib-python'

for pkg in packages:
    print(f'Installing {pkg}...')
    command(f'pip install {pkg}')
