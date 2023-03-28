#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pushd $SCRIPT_DIR

# Need to set up X11
# Source: https://serverfault.com/questions/229021/how-to-use-crontab-to-display-something-to-users-on-display-0-0-or-run-a-gui-pr
xauth extract /home/foo/xauth-foo $DISPLAY
export DISPLAY=:0.0

. venv/bin/activate

# Start web server for browsing files (snapshots)
# python3 software/server.py &

# Start main program and block
python3 software/kibbie.py &

popd