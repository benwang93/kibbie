# Project Kibbie

Automated kibble dispenser

## Setup

### Raspberry Pi (embedded)

Hardware requirements:

- Raspberry Pi 3 B+
- 64 GB MicroSD card with Raspbian (see https://www.raspberrypi.com/software/ for installation instructions)

Instructions:

1. On Raspberry Pi with Raspian, clone this repo to `/home/<username>/`
2. Increase swap size from 100MB to something big (2048MB?). See https://peppe8o.com/set-raspberry-pi-swap-memory/
3. Install required python packages by running `setup_raspberrypi.sh`
4. Enable I2C on Pi via the Pi configuration tool. For more information, see https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c
5. Set up kibbie's run.sh to run on startup

Additionally, set up SSH and VNC on the Pi.

#### Python package setup

To install OpenCV on Raspberry Pi 3 Model B+, followed these instructions: https://raspberrypi-guide.github.io/programming/install-opencv and installed it in a virtualenv. Note that these are part of the `setup_raspberrypi.sh` script.

```
. venv/bin/activate

sudo apt-get install build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libfontconfig1-dev libcairo2-dev libgdk-pixbuf2.0-dev libpango1.0-dev libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran libhdf5-dev libhdf5-serial-dev libhdf5-103 python3-pyqt5 python3-dev -y

pip install opencv-python==4.5.3.56
```

#### Configuring swap memory

Copied from https://peppe8o.com/set-raspberry-pi-swap-memory/ (and tweaked the memory requirement to 2 GB)

Disable swap:

```
sudo dphys-swapfile swapoff
```

Change swap size in dphys-swapfile. Open this file for editing:

```
sudo nano /etc/dphys-swapfile
```

Identify CONF_SWAPSIZE parameter and change according to your needs. For example, I will change it to:

```
CONF_SWAPSIZE=2048
```

Exit and save. Enable swap and restart dphys service:

```
sudo dphys-swapfile swapon
sudo systemctl restart dphys-swapfile.service
```

Check that swap has changed value:

```
pi@raspberrypi:~ $ free
               total        used        free      shared  buff/cache   available
 Mem:         374964       36648      223092        2708      115224      282916
 Swap:        511996           0      511996
```

This will persist also after Raspberry PI reboot.

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
git update-index --assume-unchanged software\lib\HardwareParameters.py
```

To start tracking again:

```
git update-index --no-assume-unchanged software\lib\HardwareParameters.py
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

## Other info

- [MakerFocus PWM Servo Motor Driver IIC Module 16 Channel PWM Outputs 12 Bit Resolution I2C Compatible with Raspberry Pi 4 3B+ 3B Zero/Zero W/Zero WH and Jetson Nano on Amazon](https://www.amazon.com/gp/product/B07H9ZTWNC)
- [Adafruit I2C configuration guide](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c)
- [Adafruit Servo Hat instructions](https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/attach-and-test-the-hat)

