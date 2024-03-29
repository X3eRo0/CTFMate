from common import *
from libc import *
import zstandard


class Linker:

    version = ""
    tempdir = ""
    ldarch = ""
    fullpath = ""
    dbgpkg = ""
    filename = ""

    def __init__(self, libc_version="", tempdir=None, libcarch=None):
        self.version = libc_version
        self.tempdir = tempdir
        self.ldarch = libcarch

    def ExtractLinker(self):
        ar_file = unix_ar.open(self.dbgpkg)
        infolist = ar_file.infolist()
        tarball = None
        for file in infolist:
            if b"data.tar.gz" == file.name:
                tarball = ar_file.open("data.tar.gz")
                break

            if b"data.tar.xz" == file.name:
                tarball = ar_file.open("data.tar.xz")
                break

            if b"data.tar.zst" == file.name:
                dctx = zstandard.ZstdDecompressor()
                zstd = ar_file.open("data.tar.zst")

                tarball = tempfile.TemporaryFile(suffix=".tar")
                dctx.copy_stream(zstd, tarball)
                tarball.seek(0)

        if tarball is None:
            return -1

        extract = tarfile.open(fileobj=tarball)
        members = extract.getmembers()
        arch = 0

        if "i386" == self.ldarch:
            arch = 32
        elif "amd64" == self.ldarch:
            arch = 64
        filepath = None
        for member in members:
            if "ld-" in member.name:
                if arch == 32 and "i386" in member.name:
                    filepath = member.name[2:]
                    extract.extract(member, self.tempdir.name)

                if arch == 64 and "x86_64" in member.name:
                    filepath = member.name[2:]
                    extract.extract(member, self.tempdir.name)
                break
        if filepath is None:
            return -2
        filepath = os.path.join(self.tempdir.name, filepath)
        return filepath

    def GetLinker(self):
        pkgname = libc_pkg % (self.version)

        if "ubuntu" in self.version:
            pkgurl = GetUrl(ubuntu_libc_deb_urls, pkgname)
        elif "deb" in self.version:
            pkgurl = GetUrl(debian_libc_deb_urls, pkgname)

        if pkgurl == None:

            pkgurl = str(
                input("[-] Error 404    : %s Not Found!\n[+] Custom URL/N : " % pkgname)
            )
            if pkgurl == "n" or pkgurl == "N":
                return None

        self.dbgpkg = Download(pkgurl, self.tempdir.name, pkgname)
        self.fullpath = self.ExtractLinker()
        if isinstance(self.fullpath, int):
            if self.fullpath == -1 or self.fullpath == -2:
                return False
        self.filename = os.path.basename(self.fullpath)
        return True
