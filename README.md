# Project Kibbie

Automated kibble dispenser

## Setup

1. Raspberry Pi with Raspian
2. Install required python packages

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

