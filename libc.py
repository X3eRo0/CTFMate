from common import *
from linker import *

helpfull_symbols = [
    "__libc_start_main",
    "system",
    "open",
    "read",
    "write",
    "str_bin_sh",
    "_IO_2_1_stdin_"
]

class Symbols:
    symbols = {}
    symfile = []
    sympath = ""
    
    def __init__(self, symfile = [], sympath = ""):
        self.symfile = symfile
        self.sympath = sympath

    def read(self):
        
        # read the libc symbol file ".symbols"
        
        self.symfile = open(self.sympath, "rb").readlines()

    def parse(self):
        
        # parse the symbols
        
        self.symfile = list(set(self.symfile.split('\n')))
        
        for symbol in self.symfile:
            symbol = symbol.strip().split()
            if len(symbol) == 0:
                continue
            
            offset = int(symbol[1], 16)
            symbol = symbol[0]
            self.symbols[symbol] = offset

        return True

    def getsymbol(self, offset):
        
        # fetch the symbol corresponding to the 
        # given offset

        for i, j in enumerate(self.symbols):
            if offset == self.symbols[j]:
                return j

        return 0

    def getoffset(self, symbol):

        # fetch the offset corresponding to the
        # given symbol

        return self.symbols[symbol]

    def add(self, symbol, offset):

        # add a symbol to the symbol table

        self.symbols[symbol] = offset
        return



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
    libc_id  = libc_id.replace("libc6_", "") 
    libc_ver = libc_id.split("_")
    lib_arch = libc_ver[0].split("-")[1]
    libc_ver = "_".join([libc_ver[1], lib_arch])
    return libc_ver

class Libc:
    version   = ""
    down_url  = ""
    symb_url  = ""
    filename  = ""
    directory = ""
    tempdir   = ""
    fullpath  = ""
    libcarch  = ""
    symbols   = Symbols()
    libcdata  = b""
    buildid   = ""
    debugfile = ""
    dbgdebpkg = ""
    linker    = None 

    def __init__(self, filename=""):
        self.filename = filename
        self.GetLibcVersion()

    def GetLibcVersion(self):
    
        # Get the Libc Version from the libc
        # file

        if CheckLibc(self.filename):
            
            self.fullpath  = os.path.abspath(self.filename)
            self.directory = os.path.dirname(self.fullpath)
            self.filename  = os.path.basename(self.fullpath)
            self.tempdir   = tempfile.TemporaryDirectory(dir="/tmp")

            with open(self.filename, "rb") as f:
                self.libcdata = f.read()
                verstrindex = 0
                for verstr in GLIBC_VERSION_STR:
                    if verstr in self.libcdata:
                        verstrindex = self.libcdata.index(verstr) + len(verstr)
                verstr  = self.libcdata[verstrindex : verstrindex + 0x100].split(b' ')[0][:-1]
    
                if self.libcdata[0x12] == 0x3e:
                    self.libcarch = "amd64"
                    verstr += b"_amd64"
                elif self.libcdata[0x12] == 0x03:
                    self.libcarch = "i386"
                    verstr += b"_i386"
                else:
                    return None
                
                self.version = verstr.decode('latin1')
                self.linker  = Linker(self.version, self.tempdir, self.libcarch)
                return True
        else:
            return False


    def GetLibcSymDb(self, symbol_url=None):
        if symbol_url == None:
            syms = requests.get(self.symb_url).text
        else:
            syms = requests.get(symbol_url).text
        self.symbols.symfile = syms
        return True


    def GetLibcOffset(self, symbol):
        return self.symbols[symbol]



    def ExtractLibc(self):
        ar_file  = unix_ar.open(self.dbgdebpkg)
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
                extract.extract(member, self.tempdir.name)
                break
    
        self.debugfile = os.path.join(self.tempdir.name, filepath)
        return True




    def GetGLibcPkg(self):
    
        pkgname = libc_dbg_pkg % (self.version)
        
        if "ubuntu" in self.version:
            pkgurl  = GetUrl(ubuntu_libc_deb_urls, pkgname)
        elif "deb"  in self.version:
            pkgurl  = GetUrl(debian_libc_deb_urls, pkgname)
    
        if pkgurl == None:
    
            pkgurl = str(input("[-] Error 404    : %s Not Found!\n[+] Custom URL/N : " % pkgname))
            if pkgurl == "n" or pkgurl == "N":
                return None
    
        self.dbgdebpkg = Download(pkgurl, self.tempdir.name, pkgname)
        self.ExtractLibc()
        return True 

    def Unstrip(self):
        
        stripped = self.fullpath
        dbg_libc = self.debugfile
    
        unstrip = subprocess.Popen(["eu-unstrip", stripped, dbg_libc, "-o", stripped],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
        stdout, stderr = unstrip.communicate()
        returncode = unstrip.returncode
        return returncode


    def Search_rip(self, symbol):
        
        data = "{\"symbols\" : "
    
        for i in symbol.symbols.keys():
            data += "{\"%s\": \"%x\"}," % (i, symbol.getoffset(i))
        
        data = data[:-1]
        data += "}"
        hdr = {
            "Content-Type" : "application/json"
        }
    
        url  = "https://libc.rip/api/find"
        req  = requests.post(url, data=data, headers=hdr)
        res  = req.json()
            
        libcs = []
        if res['status'] != 500: 
            for libc in res:
                libcs.append({
                        "down_url": libc['download_url'],
                        "symb_url": libc['symbols_url'],
                        "libc_id" : libc['id'],
                    }
                )
        
        return self.ChooseLibc(libcs, list(symbol.symbols.keys()), "libc.rip")


    def Search_blu(self, symbol):
    
        blukat_url = "https://libc.blukat.me/?q="
        download_url = "https://libc.blukat.me/d/"
        for i in symbol.symbols.keys():
            blukat_url += i
            blukat_url += ":"
            blukat_url += "%x" % symbol.symbols[i]
    
        res = requests.get(blukat_url)
        if res.status_code != 200:
            return False
        prh = BeautifulSoup(res.text, 'html.parser')
        tag = prh.find_all(attrs={"class":"lib-item"})
        libcs = []
        
        for i in tag:
            libc_id = i.string.strip()
            libcs.append({
                "libc_id"  : libc_id,
                "down_url" : download_url + libc_id + ".so",
                "symb_url" : download_url + libc_id + ".symbols"
            })

        return self.ChooseLibc(libcs, list(symbol.symbols.keys()), "libc.blukat.me") 


    def ChooseLibc(self, libcs, symbols, website):
        if len(libcs) > 1:
            print("[+] %.2d Libc's Found [%s]" % (len(libcs), website))
            i = 1
            
            for libc in libcs:
                self.GetLibcSymDb(libc['symb_url'])
                self.symbols.parse()
                
                print("\n  [%d] id - %s" % (i, libc['libc_id']))
                
                for sym in helpfull_symbols:
                    print("    0x%.8x --> %s" % (self.symbols.getoffset(sym), sym))
                i += 1
        
            indx = input("\nLibc[?]/N: ")
            if indx == "N" or indx == "n":
                return
            indx = int(indx) - 1
            libcver = GetLibcVersionFromID(libcs[indx]['libc_id'])
            
            self.down_url = libcs[indx]['down_url']
            self.symb_url = libcs[indx]['symb_url']
            self.fullpath = Download(self.down_url, os.getcwd(), libcs[indx]['libc_id'])
            self.filename = os.path.basename(self.fullpath)

            if not os.path.exists(os.path.join(os.getcwd(), self.filename)):
                shutil.move(self.fullpath, os.getcwd())
        
            return True

        elif len(libcs) == 0:
            print("[+] No Libc's Found [%s]" % website)
            return False


def Search():
    # get the symbol, offset combination
    # and search in libc.rip or libc.blukat.me
    libc = Libc()
    print("Enter the symbol you want to search and the")
    print("corresponding offset of that symbol in this")
    print("format: Press N after entering all symbols)")
    print("  > _IO_2_1_stdin_:5c0")
    symbols = Symbols()
    sym_off = "CTF{835171179aa9ffb305821fb9cb3c82b9}"
    
    while (sym_off != "N" or sym_off != "n"):
        sym_off = str(input("(sym:off/N) : ")).strip().split(":")
        if len(sym_off) == 1:
            if sym_off[0] == "N" or sym_off[0] == "n":
                break
            else:
                continue
        
        try:
            symbol  = sym_off[0]
            offset  = int(sym_off[1], 16)
            symbols.add(symbol, offset)
        except:
            continue

    if  libc.Search_rip(symbols):
        return
    else:
        libc.Search_blu(symbols)
        return
