import urllib
import urllib.request as request
import os, sys
import tarfile
import tempfile
import unix_ar
import subprocess
import requests
import json
import shutil
import pdb



GLIBC_VERSION_STR = [
    b"GNU C Library (Ubuntu GLIBC ",
    b"GNU C Library (Ubuntu EGLIBC ",
    b"GNU C Library (Debian GLIBC "
]

ubuntu_libc_deb_url = "https://launchpad.net/ubuntu/+archive/primary/+files/"
debian_libc_deb_url = "http://ftp.us.debian.org/debian/pool/main/g/glibc/"
libc_dbg_pkg = "libc6-dbg_%s.deb"

libc_pkg = "libc6_%s.deb"
FILENAME = "libc"


def reporthook(blocknum, blocksize, totalsize):
    global FILENAME
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r[+] Fetching : [%5.1f%% %*d KB / %d KB] %s" % (
            percent, len(str(totalsize)), readsofar/1024, totalsize/1024, FILENAME)
        sys.stderr.write(s)
        if readsofar >= totalsize:
            sys.stderr.write("\r[+] Fetched  : [%5.1f%% %*d KB / %d KB] %s\n" % (100.0, len(str(totalsize)), totalsize/1024, totalsize/1024, FILENAME))
    else:
        sys.stderr.write("read %d\n" % (readsofar,))


def Download(url, directory, filename):
    global FILENAME
    FILENAME = filename
    fullpath = "%s/%s" % (directory, filename)

    try:
        request.urlretrieve(url, fullpath, reporthook)

    except urllib.error.HTTPError:
        url = str(input("[-] %s Not Found!\n[+] Custom URL/N: " % filename))
        if url != "n" and url != "N":
            fullpath = Download(url, directory, filename)
        else:
            print("[-] Exiting")
            exit(-1)

        
    return fullpath


def AbsoluteFilePaths(directory):
   
    for dirpath,_,filenames in os.walk(directory):
       for f in filenames:
           yield os.path.abspath(os.path.join(dirpath, f))


def GetLibcVersion(file):
    if CheckLibc(file):
    
        with open(file, "rb") as f:
            libc = f.read()
            verstrindex = 0
            for verstr in GLIBC_VERSION_STR:
                if verstr in libc:
                    verstrindex = libc.index(verstr) + len(verstr)
            verstr  = libc[verstrindex : verstrindex + 0x100].split(b' ')[0][:-1]

            if libc[0x12] == 0x3e:
                verstr += b"_amd64"
            elif libc[0x12] == 0x03:
                verstr += b"_i386"
            else:
                return None
            
            return verstr.decode('latin1')


def GetLibcVersionFromID(libc_id):
    libc_ver = libc_id.split("_")
    lib_arch = libc_ver[0].split("-")[1]
    libc_ver = "_".join([libc_ver[1], lib_arch])
    return libc_ver


def CheckELF(file):

    with open(file, "rb") as f:
        header = f.read(4)
        if header == b"\x7f\x45\x4c\x46":
            return True

    return False


def CheckLibc(file):
    
    with open(file, "rb") as f:
        content = f.read()
        # check for ELF header
        if not CheckELF(file):
            return False
        # check for libc string
        if b"GNU C Library" not in content:
            return False 
        # check for statically linked binaries
        if content[7] == b'\x02':
            return False
    
        return True


def ExtractLibc(directory, filename):
    ar_file  = unix_ar.open(filename)
    infolist = ar_file.infolist()

    for file in infolist:
        if b"data.tar.gz" == file.name:
            tarball = ar_file.open("data.tar.gz")
            break

        if b"data.tar.xz" == file.name:
            tarball = ar_file.open("data.tar.xz")
            break 

    extract  = tarfile.open(fileobj=tarball)
    members  = extract.getmembers()

    for member in members:
        if "libc-" in member.name:
            filepath = member.name[2:]
            extract.extract(member, directory)
            break

    filepath = os.path.join(directory, filepath)
    return filepath

def ExtractLinker(directory, filename):
    ar_file  = unix_ar.open(filename)
    infolist = ar_file.infolist()

    for file in infolist:
        if b"data.tar.gz" == file.name:
            tarball = ar_file.open("data.tar.gz")
            break

        if b"data.tar.xz" == file.name:
            tarball = ar_file.open("data.tar.xz")
            break


    extract = tarfile.open(fileobj=tarball)
    members = extract.getmembers()
    arch = 0

    if "i386" in filename:
        arch = 32
    elif "amd64" in filename:
        arch = 64
    
    for member in members:
        if "ld-" in member.name: 
            if arch == 32 and "i386" in member.name:
                filepath = member.name[2:]
                extract.extract(member, directory)

            if arch == 64 and "x86_64" in member.name:
                filepath = member.name[2:]
                extract.extract(member, directory)
            break

    filepath = os.path.join(directory, filepath)
    return filepath

def GetLinker(libc_version, output):
    pkgname = libc_pkg % (libc_version)

    if "ubuntu" in libc_version:
        pkgurl  = ubuntu_libc_deb_url + pkgname
    elif "deb" in libc_version:
        pkgurl  = debian_libc_deb_url + pkgname

    debpkg  = Download(pkgurl, output, pkgname)
    linker  = ExtractLinker(output, debpkg)
    return linker


def GetGLibcPkg(libc_version, output):

    pkgname = libc_dbg_pkg % (libc_version)
    
    if "ubuntu" in libc_version:
        pkgurl  = ubuntu_libc_deb_url + pkgname
    elif "deb" in libc_version:
        pkgurl  = debian_libc_deb_url + pkgname
    
    debpkg  = Download(pkgurl, output, pkgname)
    libcso  = ExtractLibc(output, debpkg)
    return libcso


def PatchInterpreter(binary, linker):
    patchelf = subprocess.Popen(["patchelf", "--set-interpreter", linker, binary],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    stdout, stderr = patchelf.communicate()
    returncode = patchelf.returncode
    return returncode

def PatchRPath(binary):

    patchelf = subprocess.Popen(["patchelf", "--set-rpath", os.getcwd(), binary],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    stdout, stderr = patchelf.communicate()
    returncode = patchelf.returncode
    return returncode


def Unstrip(stripped, dbg_libc):
    
    stripped = os.path.abspath(stripped)
    dbg_libc = os.path.abspath(dbg_libc)

    unstrip = subprocess.Popen(["eu-unstrip", stripped, dbg_libc, "-o", stripped],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    stdout, stderr = unstrip.communicate()
    returncode = unstrip.returncode
    return returncode


def GetLibcSymDb(symb_url):
    return requests.get(symb_url).text


def GetLibcOffset(libc_sym_db, libc_sym):
    libc_sym_db = libc_sym_db.split('\n')

    for symbol in libc_sym_db:
        symbol = symbol.split(" ")
        if symbol[0] == libc_sym:
            return int(symbol[1], 16)


def Search(symbol, offset):
    
    data = "{\"symbols\" : {\"%s\": \"%s\"}}" % (symbol, offset)
   
    hdr = {
        "Content-Type" : "application/json"
    }

    url  = "https://libc.rip/api/find"
    req  = requests.post(url, data=data, headers=hdr)
    res  = req.json()
    
    libcs = []

    for libc in res:
        libcs.append({
                "down_url": libc['download_url'],
                "symb_url": libc['symbols_url'],
                "libc_id" : libc['id'],
            }
        )
    
    if len(res) > 1:
        print("[+] Multiple Libc Found")
        i = 1
        for libc in libcs:
            symbol_file = GetLibcSymDb(libc['symb_url'])
            print("[%d] id - %s" % (i, libc['libc_id']))
            print("    puts       -- 0x%x" % GetLibcOffset(symbol_file, 'puts'))
            print("    system     -- 0x%x" % GetLibcOffset(symbol_file, 'system'))
            print("    str_bin_sh -- 0x%x" % GetLibcOffset(symbol_file, 'str_bin_sh'))
            i += 1

        indx = int(input("\nLibc[?]: ")) - 1
        libcver = GetLibcVersionFromID(libcs[indx]['libc_id'])
        temp = tempfile.TemporaryDirectory(dir = '/tmp')
        slib = Download(libcs[indx]['down_url'], os.getcwd(), libcs[indx]['libc_id'])
        filename = os.path.basename(slib)
        shutil.move(slib, os.getcwd())
        temp.cleanup()


    elif len(res) == 0:
        print("[+] No Libc's Found")

    


def main(binary):

    cdfiles = AbsoluteFilePaths(os.getcwd())
    
    for file in cdfiles:
        if CheckLibc(file):
            libc = file
    
    filename = os.path.basename(libc)
    print("[+] Libc     : ./%s" % filename) 
    
    if filename != "libc.so.6":
        os.rename(libc, os.path.join(os.getcwd(), "libc.so.6"))
        filename = "libc.so.6"
        libc = os.path.abspath("./libc.so.6")

    tempdir  = tempfile.TemporaryDirectory(dir = "/tmp")
    libcver  = GetLibcVersion(libc)

    print("[+] Version  : %s" % libcver)

    libcdbg  = GetGLibcPkg(libcver, tempdir.name)
    linker   = GetLinker(libcver, tempdir.name)
    linkern  = os.path.basename(linker)
    
    if not os.path.exists(os.path.join(os.getcwd(), linkern)):
        shutil.move(linker, os.getcwd())
    
    code = Unstrip(libc, libcdbg)
    if code != 0:
        print("[-] eu-unstrip [%.d] -- %s" % (code, filename))
    else:
        print("[+] Patched  : %s" % filename)

    if PatchInterpreter(binary, linkern) != 0:
        print("[-] \"patchelf\" failed to patch interpreter")
    
    elif PatchRPath(binary) != 0:
        print("[-] \"patchelf\" failed to patch rpath")
    
    else:
        print("[+] Patched  : %s" % binary)

    tempdir.cleanup()

if __name__ == "__main__":
    
    main("./ghostdiary")
    # Search("__libc_start_main_ret", "0xe81")
