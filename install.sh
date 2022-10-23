#!/bin/sh

git clone https://github.com/X3eRo0/CTFMate.git
cd ~/CTFMate
python -m pip install -r ./requirements.txt
chmod +x ctfmate.py
sudo ln -s $PWD/ctfmate.py /usr/bin/ctfmate
