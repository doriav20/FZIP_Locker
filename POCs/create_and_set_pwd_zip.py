import zipfile
from os import remove
from os.path import exists, isdir
from glob import glob
import pyminizip


def compress_zipfile(src: [], dest: str):
    zf = zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED)
    for filepath in src:
        if exists(filepath):
            if isdir(filepath):
                dir_files = glob(filepath + "/**", recursive=True)
                for fpath in dir_files:
                    zf.write(fpath, compress_type=zipfile.ZIP_DEFLATED)
            else:
                zf.write(filepath, compress_type=zipfile.ZIP_DEFLATED)
    zf.close()


def compress_pyminizip(src: str, dest: str, pwd: str = None):
    if exists(src):
        pyminizip.compress(src, None, dest, pwd, 0)


def compress(src: [], dest: str, pwd: str = None):
    compress_zipfile(src=src, dest='./comp.zip')
    compress_pyminizip(src='./comp.zip', dest=dest, pwd=pwd)
    remove('./comp.zip')


def decompress(path: str, pwd: str = None):
    if not path.endswith(".zip"):
        return

    dest = path[:-4] + '/'
    pyminizip.uncompress(path, pwd, '.', 0)

    zf = zipfile.ZipFile('./comp.zip', mode='r')
    zf.extractall(dest)
    zf.close()
    remove('./comp.zip')
