#!/usr/bin/python3

from libc import *
from linker import *
from common import *

def SIGINT_Handler(sig, frame):
    print("[-] Exiting (CTRL-C)")
    sys.exit(0)

def AbsoluteFilePaths(directory):
   
    for dirpath,_,filenames in os.walk(directory):
       for f in filenames:
           yield os.path.abspath(os.path.join(dirpath, f))


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


def GenerateTemplate(binary, host, port):
   
    if host == None:
        host = "127.0.0.1"

    if port == None:
        port = "1337"

    template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'template.py')
    with open(template_path, 'r') as t:
        template = t.read()

    template = template % (binary, host, port)
    template_path = os.path.join(os.getcwd(), 'exploit.py')
    with open(template_path, 'w') as t:
        t.write(template)
        print("[+] Exploit      : 'exploit.py' Template Generated")
        return
    print("[-] Error writing to 'exploit.py'")
    return

def main(binary, libc, linker, host, port):

    cdfiles = AbsoluteFilePaths(os.getcwd())
    if libc == None:
        for file in cdfiles:
            if CheckLibc(file):
                libc = file
    
   
    if libc != None:
        filename = os.path.basename(libc)

        if not os.path.exists(binary):
            print("[-] Error %s does not exist" % binary)
            exit(-1)


        print("[+] Binary       : %s" % binary)
        print("[+] Libc         : %s" % filename) 
        
        if filename != "libc.so.6":
            os.rename(libc, os.path.join(os.getcwd(), "libc.so.6"))
            filename = "libc.so.6"
            libc = os.path.abspath("./libc.so.6")

        tempdir  = tempfile.TemporaryDirectory(dir = "/tmp")
        libcver  = GetLibcVersion(libc)

        print("[+] Version      : %s" % libcver)

        libcdbg  = GetGLibcPkg(libcver, tempdir.name)
        if libcdbg != None:
            code = Unstrip(libc, libcdbg)
            if code != 0:
                print("[-] Error        : \"eu-unstrip\" [%.d] -- %s" % (code, filename))
            else:
                print("[+] Patched      : %s" % filename)
    

        if linker == None:
            linker   = GetLinker(libcver, tempdir.name)
            if linker != None:
                linkern  = os.path.basename(linker)
        else:
            linkern  = linker 
            linker   = os.path.abspath(linker)
        
        if linker != None:
            if not os.path.exists(os.path.join(os.getcwd(), linkern)):
                shutil.move(linker, os.getcwd())
        
            if PatchInterpreter(binary, linkern) != 0:
                print("[-] Error        : \"patchelf\" failed to patch interpreter")
        
        if PatchRPath(binary) != 0:
            print("[-] Error        : \"patchelf\" failed to patch rpath")
        
        else:
            print("[+] Patched      : %s" % binary)
        
        tempdir.cleanup()
    
    GenerateTemplate(binary, host, port)

if __name__ == "__main__":

    
    signal.signal(signal.SIGINT, SIGINT_Handler)
    

    parser = argparse.ArgumentParser(
        description="initiate environment for pwning in CTFs."
        )

    parser.add_argument('-b', '--binary', dest='binary', help='initiate environment for this binary')
    parser.add_argument('-s', '--search', dest='search', action='store_true', help='search libc')
    parser.add_argument('-S', '--symbol', dest='symbol', help='libc symbol')
    parser.add_argument('-o', '--offset', dest='offset', help='libc offset')
    parser.add_argument('-pr', '--patch-rpath', action='store_true', dest='patch_rpath', help="patch binary's rpath")
    parser.add_argument('-pi', '--patch-interpreter', action='store_true', dest='patch_interpreter', help="patch binary's interpreter")
    parser.add_argument('-lc', '--libc', dest='libc', help='libc binary for patching')
    parser.add_argument('-ld', '--ld', dest='linker', help='linker binary for patching')
    parser.add_argument('-H', '--host', dest='host', help='vulnerable server ip')
    parser.add_argument('-P', '--port', dest='port', help='vulnerable server port')
    parser.add_argument('-t', '--template', action='store_true', dest='template', help='generate template exploit.py')
    args = parser.parse_args()
    
    
    if CheckDependencies() == 0:
        if args.binary and not args.patch_rpath and not args.patch_interpreter and not args.template:
            main(args.binary, args.libc, args.linker, args.host, args.port)
    
        elif args.search:
            if args.symbol:
                if args.offset:
                    Search(args.symbol, args.offset)
                else:
                    print("Error: offset was not provided for '%s'" % args.symbol)
            else:
                print("Error: symbol was not provided for searching")
    
        elif args.patch_rpath:
            if args.binary:
                if PatchRPath(args.binary) != 0:
                    print("[-] Error     : \"patchelf\" failed to patch rpath")
                else:
                    print("[+] Patched   : %s" % args.binary)
            else:
                parser.print_usage()
        
        elif args.patch_interpreter:
            if args.binary:
                if args.linker:
                    if PatchInterpreter(args.binary, args.linker) != 0:
                        print("[-] Error     : \"patchelf\" failed to patch interpreter")

                    else:
                        print("[+] Patched   : %s" % args.binary)
                else:
                    parser.print_usage()
            else:
                parser.print_usage()

        elif args.template:
            if args.binary:
                GenerateTemplate(args.binary, args.host, args.port)
            else:
                parser.print_usage()

        else:
            parser.print_usage()
    else:
        exit(-1)
