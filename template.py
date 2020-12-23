#!/usr/bin/env python
# -*- coding: utf-8 -*-

# this exploit was generated via
# 1) pwntools
# 2) ctfinit

import os
import time
from pwn import *

# Set up pwntools for the correct architecture
exe = context.binary = ELF('%s')
context.delete_corefiles = True
context.rename_corefiles = False

host = args.HOST or '%s'
port = int(args.PORT or %s)

def local(argv=[], *a, **kw):
    '''Execute the target binary locally'''
    if args.GDB:
        return gdb.debug([exe.path] + argv, gdbscript=gdbscript, *a, **kw)
    else:
        return process([exe.path] + argv, *a, **kw)

def remote(argv=[], *a, **kw):
    '''Connect to the process on the remote host'''
    io = connect(host, port)
    if args.GDB:
        gdb.attach(io, gdbscript=gdbscript)
    return io

def start(argv=[], *a, **kw):
    '''Start the exploit against the target.'''
    if args.LOCAL:
        return local(argv, *a, **kw)
    else:
        return remote(argv, *a, **kw)

gdbscript = '''
tbreak *0x{exe.entry:x}
continue
'''.format(**locals())

#===========================================================
#                    EXPLOIT GOES HERE
#===========================================================

io = start()

def GetOffsetStdin():
    log_leve = context.log_level
    context.log_level = 'critical'
    if exe.arch != 'amd64':
        print("[-] only amd64 supported")
        exit(-1)

    p = process(exe.path)
    p.sendline(cyclic(512))
    p.wait()
    time.sleep(2)
    core = p.corefile
    fault = core.fault_addr
    ofst = cyclic_find(fault & 0xffffffff)
    p.close()
    context.log_level = log_level
    return ofst


def GetOffsetArgv():
    log_leve = context.log_level
    context.log_level = 'critical'
    if exe.arch != 'amd64':
        print("[-] only amd64 supported")
        exit(-1)

    p = process([exe.path, cyclic(512)])
    p.wait()
    time.sleep(2)
    core = p.corefile
    fault = core.fault_addr
    ofst = cyclic_find(fault & 0xffffffff)
    p.close()
    context.log_level = log_level
    return ofst



io.interactive()
