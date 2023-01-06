#!/bin/bash

python3 -m pip install virtualenv
python3 -m virtualenv venv

. venv/bin/activate

pip3 install -r requirements-desktop.txt

echo Done!