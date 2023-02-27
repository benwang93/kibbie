#!/bin/bash

python3 -m pip install virtualenv
python3 -m virtualenv venv

. venv/bin/activate

pip3 install -r requirements-desktop.txt

# Stop tracking hardware config file
echo "Having git stop tracking hardware config file: software/lib/HardwareParameters.py"
echo "Run 'git update-index --no-assume-unchanged software/lib/HardwareParameters.py' to start tracking"
git update-index --assume-unchanged software/lib/HardwareParameters.py

echo Done!