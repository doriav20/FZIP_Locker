import os
import zipfile
from os import remove, mkdir, rmdir
from os.path import exists, isdir
import glob

import pyminizip
from Common.details_generator import generate_unique_filename


class ZIPManager:
    @staticmethod
    def __compress_zipfile(src: [], dest: str) -> None:
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
    def compress(src: [], dest: str, pwd: str = None) -> None:
        filename = generate_unique_filename('tmp')
        ZIPManager.__compress_zipfile(src=src, dest=filename)
        ZIPManager.__compress_pyminizip(src=filename, dest=dest, pwd=pwd)
        remove(filename)

    @staticmethod
    def decompress(path: str, pwd: str = None) -> None:
        if not exists(path):
            return

        if (idx := path.find('.')) != -1:
            dest = path[:idx] + '/'
        else:
            return

        dir_name = generate_unique_filename()
        mkdir(dir_name)
        pyminizip.uncompress(path, pwd, dir_name, 0)
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        filename = glob.glob(dir_name + '/**')[0]

        zf = zipfile.ZipFile(filename, mode='r')
        zf.extractall(dest)
        zf.close()

        remove(filename)
        rmdir(dir_name)

