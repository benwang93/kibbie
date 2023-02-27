# Project Kibbie

Automated kibble dispenser

## Setup

### Raspberry Pi (embedded)
1. Raspberry Pi with Raspian
2. Install required python packages by running `setup_raspberrypi.sh`
3. Set up kibbie's run.sh to run on startup

#### Python package setup

To install OpenCV on Raspberry Pi 3 Model B+, followed these instructions: https://raspberrypi-guide.github.io/programming/install-opencv and installed it in a virtualenv

```
. venv/bin/activate

sudo apt-get install build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libfontconfig1-dev libcairo2-dev libgdk-pixbuf2.0-dev libpango1.0-dev libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran libhdf5-dev libhdf5-serial-dev libhdf5-103 python3-pyqt5 python3-dev -y

pip install opencv-python==4.5.3.56
```

#### Configuring for run on startup

Source: https://stackoverflow.com/questions/12973777/how-to-run-a-shell-script-at-startup

Set up chrontab for kibbie:

```
$ crontab -e
@reboot  /home/<username>/kibbie/run.sh
```

### PC (development)

Run `setup_desktop.sh` to set up virtualenv and install development packages.

To ignore the `HardwareParameters.py` file, run:

```
git update-index --assume-unchanged software/lib/HardwareParameters.py
```

To start tracking again:

```
git update-index --no-assume-unchanged software/lib/HardwareParameters.py
```

Source: https://stackoverflow.com/questions/23673174/how-to-ignore-new-changes-to-a-tracked-file-with-git

### Software

#### FreeCAD

Design done with FreeCAD 0.20.1. Required modules:

- Assembly 3

##### Assembly 3 installation

1. Tools > Addon Manager
2. Search for and install Assembly 3
3. After restarting FreeCAD, load something that uses Assembly 3 (or select it from the menu, maybe create a new assembly?)
4. Will prompt you to install `py-slvs`. The install will appear to fail, but this is due to pip saying it needs to be upgraded. You're OK to dismiss the repeated prompts to install at this point.
5. Click on an assembly in the Model pane on the left, make sure that the assembly's "Solver Type" is set to "SolveSpace" in the left-hand "Property" pane.

# Feeder servo demo

See the `servo_demo` folder. Parts needed:

- `hardware\prints\servo_mount_plate\servo_mount_plate.ctb`
- `hardware\prints\servo_coupler_v1\Servo_coupler_v1.ctb`

Run script `servo_demo\kibbie_dispenser_demo.py`

