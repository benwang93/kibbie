#!/bin/bash
. venv/bin/activate

# Start web server for browsing files (snapshots)
python3 software/server.py &

# Start main program and block
python3 software/kibbie.py