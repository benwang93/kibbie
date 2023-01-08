"""
Feeder demo

Setup:
- Connect Pi servo hat to DC power (9V, 4A)
- Command servo to the neutral position via this program
- Use `servo_angle_commander.py` to calibrate if needed
  - Attach dispenser servo to feeder assembly such that servo neutral is when 2 paddles are perfectly vertical
  - Attach door servo to feeder assembly such that servo at 40 degrees is door fully open
- Send "d" command to dispense food, "h" for help.

""" 

from adafruit_servokit import ServoKit
import time

# Servo channel definitions
NUM_CHANNELS = 16
NUM_CHANNELS_USED = 2
CHANNEL_DOOR = 0
CHANNEL_DISPENSER = 1

# Dispenser angle definitions
ANGLE_NEUTRAL = 90
NUM_PADDLES = 5
ANGLE_DISPENSE_1 = ANGLE_NEUTRAL - 360 / NUM_PADDLES
ANGLE_DISPENSE_2 = ANGLE_NEUTRAL + 360 / NUM_PADDLES

# Door angle definitions
ANGLE_DOOR_OPEN = 40                                    # Calibrated offset angle for fully retracted (open) door
ANGLE_DOOR_RANGE = 162-40                               # Range of door - should be same regardless of servo calibration
ANGLE_DOOR_CLOSED = ANGLE_DOOR_OPEN + ANGLE_DOOR_RANGE  # Calculated angle of closed door

# Counters
current_angles = []   # Current servo angle
dispense_count = 0  # Total number of dispenses

def go_to_angle(channel, target_angle):
    global current_angles

    kit.servo[channel].angle = target_angle+1
    time.sleep(1)
    kit.servo[channel].angle = target_angle-1
    time.sleep(1)
    kit.servo[channel].angle = target_angle

    current_angles[channel] = target_angle

def print_help():
    print(
        "\n" + \
        "==============\n" + \
        "Kibbie console\n" + \
        "==============\n" + \
        "\n" +\
        "Commands:\n" +\
        "\n" +
        "  d    dispense\n" +\
        "  h    print this help\n" +\
        "  c    close door\n" +\
        "  o    open door\n" +\
        "  n    go to neutral\n" +\
        "  1    go to dispense 1 position\n" +\
        "  2    go to dispense 2 position\n" +\
        "  p    print status (angle and food dispensed)\n" +\
        "  q    quit\n"
    )

def print_status():
    global current_angles, dispense_count
    print("Kibbie status:")
    for channel in range(NUM_CHANNELS_USED):
        print(f"  Current angle[{channel}]: {current_angles[channel]}")
    print(f"  Total dispenses: {dispense_count}")

def dispense_food():
    global current_angles, dispense_count
    if current_angles[CHANNEL_DISPENSER] == ANGLE_DISPENSE_1:
        go_to_angle(CHANNEL_DISPENSER, ANGLE_DISPENSE_2)
    else:
        go_to_angle(CHANNEL_DISPENSER, ANGLE_DISPENSE_1)
    
    # Track number of dispenses
    dispense_count += 1

    print("Food dispensed!\n")

# Initial setup
kit = ServoKit(channels=NUM_CHANNELS)

for channel_num in range(NUM_CHANNELS_USED):
    kit.servo[channel_num].actuation_range = 180
    kit.servo[channel_num].set_pulse_width_range(500, 2500)

    # Track per-servo angles
    current_angles.append(0)

# Start with door closed
go_to_angle(CHANNEL_DOOR, ANGLE_DOOR_OPEN)

# We need authority in both directions, so 90 degrees is neutral
print("Setting angle to neutral (90 degrees)")

# In order to reduce motor chatter, we need to always overshoot the angle, wait a bit, then go to the desired angle
go_to_angle(CHANNEL_DISPENSER, ANGLE_NEUTRAL)

# Wait for food to be loaded
print("90 degrees achieved! Please pour food in")
_ = input("Hit enter to continue")

# Now we need to load food into the feeder. Do this by turning in either direction enough to load the paddles, but not enough to dispense
print("Loading side 1...")
go_to_angle(CHANNEL_DISPENSER, ANGLE_DISPENSE_1)

time.sleep(1.5)

# Now dispense food once
print("Loading complete!")
print_help()

while True:
    print("\n-----------------------------------\n")
    command = input("Please enter a command: ")

    if command == "d":
        dispense_food()
    elif command == "h":
        print_help()
    elif command == "c":
        go_to_angle(CHANNEL_DOOR, ANGLE_DOOR_CLOSED)
        print("Door closed!")
    elif command == "o":
        go_to_angle(CHANNEL_DOOR, ANGLE_DOOR_OPEN)
        print("Door opened!")
    elif command == "n":
        go_to_angle(CHANNEL_DISPENSER, ANGLE_NEUTRAL)
        print("Dispenser moved to neutral!")
    elif command == "1":
        go_to_angle(CHANNEL_DISPENSER, ANGLE_DISPENSE_1)
        print("Dispenser moved to dispense position 1!")
    elif command == "2":
        go_to_angle(CHANNEL_DISPENSER, ANGLE_DISPENSE_2)
        print("Dispenser moved to dispense position 2!")
    elif command == "p":
        print_status()
    elif command == "q":
        break
    else:
        print(f"Unrecognized command '{command}'\n")

print(f"Kibbie shutting down after {dispense_count} dispenses!")