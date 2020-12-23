import urllib
import urllib.request as request
import os, sys
import tarfile
import tempfile
import subprocess
import requests
import shutil
import argparse

try:
    import unix_ar
except:
    print("[-] unix_ar not installed")
    exit(-1)


GLIBC_VERSION_STR = [
    b"GNU C Library (Ubuntu GLIBC ",
    b"GNU C Library (Ubuntu EGLIBC ",
    b"GNU C Library (Debian GLIBC "
]

ubuntu_libc_deb_urls = [
    "http://security.ubuntu.com/ubuntu/pool/main/g/glibc/",
    "https://launchpad.net/ubuntu/+archive/primary/+files/"
]

debian_libc_deb_urls = [
    "http://ftp.us.debian.org/debian/pool/main/g/glibc/",
]

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

def CheckDependencies():

    try:
        proc = subprocess.Popen(["eu-unstrip", "--help"],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
        stdout, stderr = proc.communicate()
        eu_unstrip = proc.returncode

    except FileNotFoundError:
        eu_unstrip = -1

    try:
        proc = subprocess.Popen(["patchelf", "--help"],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
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
        pkgurl  = GetUrl(ubuntu_libc_deb_urls, pkgname)
    elif "deb" in libc_version:
        pkgurl  = GetUrl(debian_libc_deb_urls, pkgname)

    if pkgurl == None:

        pkgurl = str(input("[-] %s Not Found!\n[+] Custom URL/N: " % filename))
        if pkgurl == "n" or url == "N":
            print("[-] Exiting")
            exit(-1)

    debpkg  = Download(pkgurl, output, pkgname)
    linker  = ExtractLinker(output, debpkg)
    return linker

def GetUrl(urllist, file):

    for url in urllist:
        fullurl = url + file
        r = requests.head(fullurl)
        if r.status_code != 404:
            return fullurl
    return None


def GetGLibcPkg(libc_version, output):

    pkgname = libc_dbg_pkg % (libc_version)
    
    if "ubuntu" in libc_version:
        pkgurl  = GetUrl(ubuntu_libc_deb_urls, pkgname)
    elif "deb" in libc_version:
        pkgurl  = GetUrl(debian_libc_deb_urls, pkgname)

    if pkgurl == None:

        pkgurl = str(input("[-] %s Not Found!\n[+] Custom URL/N: " % filename))
        if pkgurl == "n" or url == "N":
            print("[-] Exiting")
            exit(-1)

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

        indx = input("\nLibc[?]/N: ")
        if indx == "N" or indx == "n":
            return
        indx = int(indx) - 1
        libcver = GetLibcVersionFromID(libcs[indx]['libc_id'])
        temp = tempfile.TemporaryDirectory(dir = '/tmp')
        slib = Download(libcs[indx]['down_url'], os.getcwd(), libcs[indx]['libc_id'])
        filename = os.path.basename(slib)
        if not os.path.exists(os.path.join(os.getcwd(), filename)):
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

    if not os.path.exists(binary):
        print("[-] Error %s does not exist" % binary)
        exit(-1)

    print("[+] Binary   : %s" % binary)
    print("[+] Libc     : %s" % filename) 
    
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
        print("[-] Error    : \"eu-unstrip\" [%.d] -- %s" % (code, filename))
        input()
    else:
        print("[+] Patched  : %s" % filename)

    if PatchInterpreter(binary, linkern) != 0:
        print("[-] Error    : \"patchelf\" failed to patch interpreter")
    
    if PatchRPath(binary) != 0:
        print("[-] Error    : \"patchelf\" failed to patch rpath")
    
    else:
        print("[+] Patched  : %s" % binary)

    tempdir.cleanup()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="initiate environment for pwning in CTFs."
        )

    parser.add_argument('-b', '--binary', dest='binary', help='initiate environment for this binary')
    parser.add_argument('-s', '--search', dest='search', action='store_true', help='search libc')
    parser.add_argument('-S', '--symbol', dest='symbol', help='libc symbol')
    parser.add_argument('-o', '--offset', dest='offset', help='libc offset')

    args = parser.parse_args()

    
    if CheckDependencies() == 0:
        if args.binary:
            main(args.binary)
        elif args.search:
            if args.symbol:
                if args.offset:
                    Search(args.symbol, args.offset)
                else:
                    print("Error: offset was not provided for '%s'" % args.symbol)
            else:
                print("Error: symbol was not provided for searching")
        else:
            parser.print_help()
    else:
        exit(-1)