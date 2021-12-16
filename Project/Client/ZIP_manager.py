import os
import zipfile
from os import remove, mkdir, rmdir
from os.path import exists, isdir
import glob
import pyminizip
from typing import List

from Common.details_generator import generate_unique_path


class ZIPManager:
    @staticmethod
    def __compress_zipfile(src: List[str], dest: str) -> None:
        zf = zipfile.ZipFile(dest, mode='w', compression=zipfile.ZIP_DEFLATED)
        for filepath in src:
            if exists(filepath):
                if isdir(filepath):
                    dir_files = glob.glob(filepath + '/**', recursive=True)
                    for fpath in dir_files:
                        zf.write(fpath, compress_type=zipfile.ZIP_DEFLATED)
                else:
                    zf.write(filepath, compress_type=zipfile.ZIP_DEFLATED)
        zf.close()

    @staticmethod
    def __compress_pyminizip(src: str, dest: str, pwd: str = None) -> None:
        if exists(src):
            pyminizip.compress(src, None, dest, pwd, 0)

    @staticmethod
    def compress(src: List[str], dest: str, pwd: str = None) -> None:
        filename = generate_unique_path('in')
        ZIPManager.__compress_zipfile(src=src, dest=filename)
        ZIPManager.__compress_pyminizip(src=filename, dest=dest, pwd=pwd)
        remove(filename)

    @staticmethod
    def __decompress_zipfile(src: str, dest: str) -> None:
        with zipfile.ZipFile(src, mode='r') as zf:
            zf.extractall(dest)

    @staticmethod
    def __decompress_pyminizip(src: str, dest: str, pwd: str) -> None:
        pyminizip.uncompress(src, pwd, dest, 0)

    @staticmethod
    def decompress(path: str, pwd: str = None) -> None:
        if not exists(path):
            return

        if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
            dest = path[:index] + '/'
        else:
            dest = path + '_/'

        dir_name = generate_unique_path()
        mkdir(dir_name)
        ZIPManager.__decompress_pyminizip(path, dir_name, pwd)
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        filename = glob.glob(dir_name + '/**')[0]

        ZIPManager.__decompress_zipfile(filename, dest)

        remove(filename)
        rmdir(dir_name)
