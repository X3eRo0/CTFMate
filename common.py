import urllib
import urllib.request as request
import os, sys
import tarfile
import tempfile
import subprocess
import requests
import shutil
import argparse
import signal
import zstandard
from bs4 import BeautifulSoup


libc_dbg_pkg = "libc6-dbg_%s.deb"
libc_pkg = "libc6_%s.deb"

ubuntu_libc_deb_urls = [
    "http://security.ubuntu.com/ubuntu/pool/main/g/glibc/",
    "https://launchpad.net/ubuntu/+archive/primary/+files/",
]

debian_libc_deb_urls = [
    "http://ftp.us.debian.org/debian/pool/main/g/glibc/",
]

GLIBC_VERSION_STR = [
    b"GNU C Library (Ubuntu GLIBC ",
    b"GNU C Library (Ubuntu EGLIBC ",
    b"GNU C Library (Debian GLIBC ",
]

try:
    import unix_ar
except:
    sys.stdout.write("\r[-] unix_ar not installed")
    exit(-1)


def reporthook(blocknum, blocksize, totalsize):
    global FILENAME
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r[+] Fetching     : [%5.1f%% %*d KB / %d KB] %s" % (
            percent,
            len(str(totalsize)),
            readsofar / 1024,
            totalsize / 1024,
            FILENAME,
        )
        sys.stderr.write(s)
        if readsofar >= totalsize:
            sys.stderr.write(
                "\r[+] Fetched      : [%5.1f%% %*d KB / %d KB] %s\n"
                % (
                    100.0,
                    len(str(totalsize)),
                    totalsize / 1024,
                    totalsize / 1024,
                    FILENAME,
                )
            )
    else:
        sys.stderr.write("read %d\n" % (readsofar,))


def Download(url, directory, filename):
    global FILENAME
    FILENAME = filename
    fullpath = "%s/%s" % (directory, filename)

    try:
        request.urlretrieve(url, fullpath, reporthook)

    except urllib.error.HTTPError as e:

        print("[-] Error    : %s Not Found" % filename)
        exit(-1)

    return fullpath


def GetUrl(urllist, file):

    for url in urllist:
        fullurl = url + file
        r = requests.head(fullurl)
        if r.status_code != 404:
            return fullurl
    return None


def CheckELF(file):

    with open(file, "rb") as f:
        header = f.read(4)
        if header == b"\x7f\x45\x4c\x46":
            return True

    return False


def CheckDependencies():

    try:
        proc = subprocess.Popen(
            ["eu-unstrip", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()
        eu_unstrip = proc.returncode

    except FileNotFoundError:
        eu_unstrip = -1

    try:
        proc = subprocess.Popen(
            ["patchelf", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()
        patchelf = proc.returncode

    except FileNotFoundError:
        patchelf = -1

    if eu_unstrip + patchelf != 0:
        print("[-] Missing Dependencies:")
        if eu_unstrip != 0:
            print(" -= eu_unstrip")
        if patchelf != 0:
            print(" -= patchelf")

    return eu_unstrip + patchelf
