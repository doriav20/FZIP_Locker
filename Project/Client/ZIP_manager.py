import os
import zipfile
from shutil import rmtree
import glob
import pyminizip
from typing import Tuple

from Common.details_generator import generate_unique_path
from Common.operation_result import OperationResultType


class ZIPManager:
    @staticmethod
    def __compress_zipfile(src: Tuple[str, ...], dest: str) -> None:
        zf = zipfile.ZipFile(dest, mode='w', compression=zipfile.ZIP_DEFLATED)
        for filepath in src:
            if os.path.exists(filepath):
                if os.path.isdir(filepath):
                    absolute_root_part = filepath.rstrip('\\')
                    absolute_root_part = absolute_root_part[:absolute_root_part.rfind('\\')] + '\\'

                    dir_files = glob.glob(filepath + '\\**', recursive=True)
                    aliases = [fpath[len(absolute_root_part):] for fpath in dir_files]

                    for fpath, alias in zip(dir_files, aliases):
                        zf.write(fpath, arcname=alias, compress_type=zipfile.ZIP_DEFLATED)
                else:
                    alias = filepath
                    if '\\' in alias:
                        alias = (alias.rstrip('\\'))
                        alias = alias[alias.rfind('\\') + 1:]
                    if '/' in alias:
                        alias = (alias.rstrip('/'))
                        alias = alias[alias.rfind('/') + 1:]
                    zf.write(filepath, arcname=alias, compress_type=zipfile.ZIP_DEFLATED)
        zf.close()

    @staticmethod
    def __compress_pyminizip(src: str, dest: str, pwd: str = None) -> None:
        if os.path.exists(src):
            pyminizip.compress(src, None, dest, pwd, 0)

    @staticmethod
    def compress(src: Tuple[str, ...], dest: str, pwd: str = None) -> OperationResultType:
        filename = ''
        try:
            filename = generate_unique_path('in')
            ZIPManager.__compress_zipfile(src=src, dest=filename)
            ZIPManager.__compress_pyminizip(src=filename, dest=dest, pwd=pwd)
            os.remove(filename)

            return OperationResultType.SUCCEEDED
        except:
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass
            return OperationResultType.UNKNOWN_ERROR

    @staticmethod
    def __decompress_zipfile(src: str, dest: str) -> None:
        with zipfile.ZipFile(src, mode='r') as zf:
            zf.extractall(dest)

    @staticmethod
    def __decompress_pyminizip(src: str, dest: str, pwd: str) -> None:
        pyminizip.uncompress(src, pwd, dest, 0)

    @staticmethod
    def decompress(path: str, pwd: str = None) -> OperationResultType:
        dir_name = ''
        try:

            if (index := path.rfind('.')) != -1 and path[index + 1] not in ['/', '\\']:
                dest = path[:index] + '\\'
                if os.path.exists(dest.rstrip('\\')):
                    dest = path[:index] + '__\\'

            else:
                dest = path + '_\\'
                if os.path.exists(dest.rstrip('\\')):
                    dest = path + '__\\'

            dir_name = generate_unique_path()
            os.mkdir(dir_name)

            ZIPManager.__decompress_pyminizip(path, dir_name, pwd)
            os.chdir(os.path.dirname(os.path.abspath(__file__)))

            filename = glob.glob(dir_name + '\\**')[0]
            ZIPManager.__decompress_zipfile(filename, dest)
            rmtree(dir_name)

            return OperationResultType.SUCCEEDED
        except Exception as ex:
            try:
                os.chdir(os.path.dirname(os.path.abspath(__file__)))

                if os.path.exists(dir_name):
                    rmtree(dir_name)
                if str(ex).startswith('error -3 with zipfile'):  # Incorrect Password
                    return OperationResultType.DETAILS_ERROR
            except:
                pass

            return OperationResultType.UNKNOWN_ERROR
