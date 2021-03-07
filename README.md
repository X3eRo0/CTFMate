# CTFMate
General CTF Helper tool

### Install
```
$ git clone https://github.com/X3eRo0/CTFMate.git ~/CTFMate
$ cd ~/CTFMate
$ pip install -r requirements.txt
$ chmod +x ctfmate.py
$ sudo ln -s ~/CTFMate/ctfmate.py /usr/bin/ctfmate
```

### Usage

```
$ ctfmate --help
usage: ctfmate [-h] [-b BINARY] [-s] [-S SYMBOL] [-o OFFSET] [-pr] [-pi] [-lc LIBC]
               [-ld LINKER] [-H HOST] [-P PORT] [-t]

initiate environment for pwning in CTFs.

optional arguments:
  -h, --help            show this help message and exit
  -b BINARY, --binary BINARY
                        initiate environment for this binary
  -s, --search          search libc
  -S SYMBOL, --symbol SYMBOL
                        libc symbol
  -o OFFSET, --offset OFFSET
                        libc offset
  -pr, --patch-rpath    patch binary's rpath
  -pi, --patch-interpreter
                        patch binary's interpreter
  -lc LIBC, --libc LIBC
                        libc binary for patching
  -ld LINKER, --ld LINKER
                        linker binary for patching
  -H HOST, --host HOST  vulnerable server ip
  -P PORT, --port PORT  vulnerable server port
  -t, --template        generate template exploit.py

```
---
### Libc Searcher Using @niklasb's [libc-database](https://github.com/niklasb/libc-database)
```
$ ctfmate -s -S __libc_start_main -o 9a0
[+] Multiple Libc Found

[1] id - libc6-amd64_2.27-3ubuntu1.2_i386
    0x000219a0 --> __libc_start_main
    0x0006f5d0 --> puts
    0x000425c0 --> system
    0x0017d67a --> str_bin_sh


[2] id - libc6-amd64_2.27-3ubuntu1_i386
    0x000219a0 --> __libc_start_main
    0x0006f590 --> puts
    0x00042580 --> system
    0x0017d49a --> str_bin_sh


[3] id - musl-1.1.22-1-omv4000.i686
    0x0001c9a0 --> __libc_start_main
    0x00053ac0 --> puts
    0x00044410 --> system
    0x00077e04 --> str_bin_sh


Libc[?]/N: 1
[+] Fetched      : [100.0%    1758 KB / 1758 KB] libc6-amd64_2.27-3ubuntu1.2_i386
```

## Features
1. Search and Fetch libc versions using symbol and offset
2. Patch the PWN challenge to use provided libc and linker
3. Custom Exploit Template

## Demo
[![asciicast](https://asciinema.org/a/380929.svg)](https://asciinema.org/a/380929)
