#!/bin/sh

sudo apt-get install -y elfutils patchelf
git clone https://github.com/X3eRo0/CTFMate.git ~/CTFMate
python -m pip install -r ~/CTFMate/requirements.txt
chmod +x ~/CTFMate/ctfmate.py
sudo ln -s ~/CTFMate/ctfmate.py /usr/bin/ctfmate
