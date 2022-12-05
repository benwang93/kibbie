# Servo demo

2 demos are contained here:
1. Demo from Waveshare (doesn't work very well and I had to change the python library from smbus to smbus2)
2. Adafruit library demo (works very well!)

Notes:
- Commanding angle changes faster than 100ms seems to cause the communication to be unstable and program crashes
- To run, install `adafruit-circuitpython-servokit` and then run `python3 adafruit_lib_test.py`
