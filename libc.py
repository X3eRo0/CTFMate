from common import *


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

def GetLibcSymDb(symb_url):
    return requests.get(symb_url).text


def GetLibcOffset(libc_sym_db, libc_sym):
    libc_sym_db = libc_sym_db.split('\n')

    for symbol in libc_sym_db:
        symbol = symbol.split(" ")
        if symbol[0] == libc_sym:
            return int(symbol[1], 16)


def CheckLibc(file):
    
    try:
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
    except:
        return False


def GetLibcVersionFromID(libc_id):
    libc_ver = libc_id.split("_")
    lib_arch = libc_ver[0].split("-")[1]
    libc_ver = "_".join([libc_ver[1], lib_arch])
    return libc_ver

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

def GetGLibcPkg(libc_version, output):

    pkgname = libc_dbg_pkg % (libc_version)
    
    if "ubuntu" in libc_version:
        pkgurl  = GetUrl(ubuntu_libc_deb_urls, pkgname)
    elif "deb" in libc_version:
        pkgurl  = GetUrl(debian_libc_deb_urls, pkgname)

    if pkgurl == None:

        pkgurl = str(input("[-] Error 404    : %s Not Found!\n[+] Custom URL/N : " % pkgname))
        if pkgurl == "n" or pkgurl == "N":
            return None

    debpkg  = Download(pkgurl, output, pkgname)
    libcso  = ExtractLibc(output, debpkg)
    return libcso


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
            print("\n[%d] id - %s" % (i, libc['libc_id']))
            print("    0x%.8x --> %s" % (GetLibcOffset(symbol_file, symbol), symbol))
            print("    0x%.8x --> puts" % GetLibcOffset(symbol_file, 'puts'))
            print("    0x%.8x --> system" % GetLibcOffset(symbol_file, 'system'))
            print("    0x%.8x --> str_bin_sh\n" % GetLibcOffset(symbol_file, 'str_bin_sh'))
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
