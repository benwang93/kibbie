"""
Various shared debug parameters
"""

from .HardwareParameters import *

# Is the kibbie monitor attached?
IS_ARDUINO_MONITOR_ATTACHED = IS_RASPBERRY_PI

# Headless mode toggle
HEADLESS_MODE = True # True to not open doors and prompt user to initialize

# KibbieServoUtils.py parameters
DEV_VIDEO_PROCESSING = True # Set to True to skip servo motor init
DEBUG_SERVO_QUEUE = False # Set to True to print per-channel servo queue information

SKIP_SERVO_WAIT = not IS_RASPBERRY_PI and DEV_VIDEO_PROCESSING

# Turn on debug print for serial
DEBUG_SERIAL_PRINT = False

# Turn on profiling of memory (debug print to console)
PROFILE_MEMORY = True