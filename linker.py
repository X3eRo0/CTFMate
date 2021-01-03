from common import *

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

        pkgurl = str(input("[-] Error 404    : %s Not Found!\n[+] Custom URL/N : " % pkgname))
        if pkgurl == "n" or pkgurl == "N":
            return None

    debpkg  = Download(pkgurl, output, pkgname)
    linker  = ExtractLinker(output, debpkg)
    return linker
